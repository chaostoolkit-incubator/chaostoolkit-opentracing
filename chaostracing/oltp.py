import json
import os
import platform
import secrets
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator

from chaoslib.run import EventHandlerRegistry, RunEventHandler
from chaoslib.types import Activity, Configuration, Experiment, Journal, Run, Secrets
from logzero import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

try:
    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

    HAS_BOTOCORE = True
except ImportError:
    logger.debug("Failed to import BotocoreInstrumentor", exc_info=True)
    HAS_BOTOCORE = False
try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    HAS_HTTPX = True
except ImportError:
    logger.debug("Failed to import HTTPXClientInstrumentor", exc_info=True)
    HAS_HTTPX = False
try:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    HAS_REQUESTS = True
except ImportError:
    logger.debug("Failed to import RequestsInstrumentor", exc_info=True)
    HAS_REQUESTS = False
try:
    from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor

    HAS_URLLIB3 = True
except ImportError:
    logger.debug("Failed to import URLLib3Instrumentor", exc_info=True)
    HAS_URLLIB3 = False
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource, get_aggregated_resources
from opentelemetry.sdk.trace import Span, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_span_in_context

try:
    from google.cloud.trace_v2 import TraceServiceClient
    from google.cloud.trace_v2.services.trace_service.transports import (
        TraceServiceGrpcTransport,
    )
    from google.oauth2.service_account import Credentials
    from opentelemetry.exporter.cloud_trace import _OPTIONS as GCP_TRACE_OPTIONS
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.propagators.cloud_trace_propagator import (
        CloudTraceFormatPropagator,
    )
    from opentelemetry.resourcedetector.gcp_resource_detector import (
        GoogleCloudResourceDetector,
    )

    HAS_GCP_EXPORTER = True
except ImportError:
    HAS_GCP_EXPORTER = False

try:
    from opentelemetry.propagators.aws import AwsXRayPropagator
    from opentelemetry.sdk.extension.aws.resource.ec2 import AwsEc2ResourceDetector
    from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator

    HAS_AWS_EXPORTER = True
except ImportError:
    HAS_AWS_EXPORTER = False


try:
    from azure.core.settings import settings
    from azure.core.tracing.ext.opentelemetry_span import OpenTelemetrySpan
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

    HAS_AZURE_EXPORTER = True
except ImportError:
    HAS_AZURE_EXPORTER = False


__all__ = [
    "configure_control",
]

REGISTRY_HANDLER = None


def configure_control(
    experiment: Experiment,
    event_registry: EventHandlerRegistry,
    trace_request: bool = False,
    trace_httpx: bool = False,
    trace_botocore: bool = False,
    trace_urllib3: bool = False,
    configuration: Configuration = None,
    secrets: Secrets = None,
    **kwargs: Any,
) -> None:
    configure_traces(configuration)
    configure_instrumentations(
        trace_request, trace_httpx, trace_botocore, trace_urllib3
    )

    global REGISTRY_HANDLER
    REGISTRY_HANDLER = OLTPRunEventHandler()
    event_registry.register(REGISTRY_HANDLER)

    REGISTRY_HANDLER.started(experiment, None)


class OLTPRunEventHandler(RunEventHandler):
    def __init__(self) -> None:
        self.root_stack = None
        self.root_span = None

        self.before_ssh_span = None
        self.before_ssh_stack = None

        self.after_ssh_stack = None
        self.after_ssh_span = None

        self.method_stack = None
        self.method_span = None

        self.rollbacks_stack = None
        self.rollbacks_span = None

        self.continuous_stack = None
        self.continuous_span = None

        self.activity_stacks = {}
        self.activity_spans = {}

        self.current_span = None

    def started(self, experiment: Experiment, journal: Journal) -> None:
        logger.debug("Starting capturing OLTP traces")
        stack = ExitStack()
        span = stack.enter_context(new_span("experiment"))
        span.set_attribute("chaostoolkit.experiment.title", experiment.get("title"))
        span.set_attribute("chaostoolkit.platform.full", platform.platform())

        self.root_stack = stack
        self.root_span = span
        self.current_span = span

    def finish(self, journal: Journal) -> None:
        logger.debug("Stopping capturing OLTP traces")

        span = self.root_span
        self.root_span = None

        span.set_attribute("chaostoolkit.experiment.status", journal.get("status"))
        span.set_attribute("chaostoolkit.experiment.deviated", journal.get("deviated"))

        self.root_stack.close()

        logger.debug("Finished capturing OLTP traces")

    def interrupted(self, experiment: Experiment, journal: Journal) -> None:
        self.root_span.set_attribute("chaostoolkit.experiment.interrupted", True)

    def signal_exit(self) -> None:
        self.root_span.set_attribute("chaostoolkit.experiment.exit_signal", True)

    def start_continuous_hypothesis(self, frequency: int) -> None:
        stack = ExitStack()
        span = stack.enter_context(new_span("hypothesis", self.root_span))
        span.set_attribute("chaostoolkit.hypothesis.phase", "continuous")

        self.continuous_stack = stack
        self.continuous_span = span

    def continuous_hypothesis_iteration(self, iteration_index: int, state: Any) -> None:
        first_probe = state.get("probes")[0]
        start_time = first_probe["start"]
        end_time = first_probe["end"]

        start_ts = int(
            datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%f")
            .replace(tzinfo=timezone.utc)
            .timestamp()
            * 1e9
        )
        end_ts = int(
            datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%f")
            .replace(tzinfo=timezone.utc)
            .timestamp()
            * 1e9
        )

        with new_span(
            "hypothesis", self.continuous_span, start_time=start_ts, end_on_exit=False
        ) as span:
            span.set_attribute("chaostoolkit.hypothesis.phase", "continuous")
            span.set_attribute("chaostoolkit.hypothesis.iteration", iteration_index)
            span.set_attribute(
                "chaostoolkit.hypothesis.met", state.get("steady_state_met")
            )

            for probe in state.get("probes"):
                child_start_ts = int(
                    datetime.strptime(probe["start"], "%Y-%m-%dT%H:%M:%S.%f")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                    * 1e9
                )
                child_end_ts = int(
                    datetime.strptime(probe["end"], "%Y-%m-%dT%H:%M:%S.%f")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                    * 1e9
                )
                with new_span(
                    "activity", span, start_time=child_start_ts, end_on_exit=False
                ) as child:
                    activity = probe["activity"]
                    child.set_attribute("chaostoolkit.activity.name", activity["name"])
                    child.set_attribute(
                        "chaostoolkit.activity.background",
                        activity.get("background", False),
                    )
                    child.set_attribute(
                        "chaostoolkit.activity.output", json.dumps(probe.get("output"))
                    )
                    child.set_attribute(
                        "chaostoolkit.activity.status", probe.get("status")
                    )
                    x = probe.get("exception")
                    if x:
                        child.set_attribute("chaostoolkit.activity.error", x)
                    child.end(end_time=child_end_ts)

            span.end(end_time=end_ts)

    def continuous_hypothesis_completed(
        self, experiment: Experiment, journal: Journal, exception: Exception = None
    ) -> None:
        self.continuous_span = None

        self.continuous_stack.close()

    def start_hypothesis_before(self, experiment: Experiment) -> None:
        stack = ExitStack()
        span = stack.enter_context(new_span("hypothesis", self.root_span))
        span.set_attribute("chaostoolkit.hypothesis.phase", "before")

        self.before_ssh_stack = stack
        self.before_ssh_span = span
        self.current_span = span

    def hypothesis_before_completed(
        self, experiment: Experiment, state: Dict[str, Any], journal: Journal
    ) -> None:
        span = self.before_ssh_span
        self.before_ssh_span = None
        self.current_span = self.root_span

        span.set_attribute("chaostoolkit.hypothesis.met", state.get("steady_state_met"))

        self.before_ssh_stack.close()

    def start_hypothesis_after(self, experiment: Experiment) -> None:
        stack = ExitStack()
        span = stack.enter_context(new_span("hypothesis", self.root_span))
        span.set_attribute("chaostoolkit.hypothesis.phase", "after")

        self.after_ssh_stack = stack
        self.after_ssh_span = span
        self.current_span = span

    def hypothesis_after_completed(
        self, experiment: Experiment, state: Dict[str, Any], journal: Journal
    ) -> None:
        span = self.after_ssh_span
        self.after_ssh_span = None
        self.current_span = self.root_span

        span.set_attribute("chaostoolkit.hypothesis.met", state.get("steady_state_met"))

        self.after_ssh_stack.close()

    def start_method(self, experiment: Experiment) -> None:
        stack = ExitStack()
        span = stack.enter_context(new_span("method", self.root_span))

        self.method_stack = stack
        self.method_span = span
        self.current_span = span

    def method_completed(self, experiment: Experiment, state: Any) -> None:
        self.method_span = None
        self.current_span = self.root_span

        self.method_stack.close()

    def start_rollbacks(self, experiment: Experiment) -> None:
        stack = ExitStack()
        span = stack.enter_context(new_span("rollbacks", self.root_span))

        self.rollbacks_stack = stack
        self.rollbacks_span = span
        self.current_span = span

    def rollbacks_completed(self, experiment: Experiment, journal: Journal) -> None:
        self.rollbacks_span = None
        self.current_span = self.root_span

        self.rollbacks_stack.close()

    def start_activity(self, activity: Activity) -> None:
        parent = self.current_span
        if self.continuous_span is not None:
            if "tolerance" in activity:
                return

        stack = ExitStack()
        span = stack.enter_context(new_span("activity", parent))
        span.set_attribute("chaostoolkit.activity.name", activity.get("name"))
        span.set_attribute(
            "chaostoolkit.activity.background", activity.get("background", False)
        )

        stack_id = secrets.token_hex(6)
        activity["_id"] = stack_id

        self.activity_stacks[stack_id] = stack
        self.activity_spans[stack_id] = span

    def activity_completed(self, activity: Activity, state: Run) -> None:
        stack_id = activity.pop("_id", None)
        if not stack_id:
            return

        span = self.activity_spans.pop(stack_id)
        span.set_attribute(
            "chaostoolkit.activity.output", json.dumps(state.get("output"))
        )
        span.set_attribute("chaostoolkit.activity.status", state.get("status"))
        x = state.get("exception")
        if x:
            span.set_attribute("chaostoolkit.activity.error", x)

        stack = self.activity_stacks.pop(stack_id)
        stack.close()


###############################################################################
# Private functions
###############################################################################
def configure_traces(configuration: Configuration) -> None:
    resource = Resource.create(
        {"service.name": os.getenv("OTEL_SERVICE_NAME", "chaostoolkit")}
    )

    vendor = configuration.get("otel_vendor", os.getenv("OTEL_VENDOR"))
    if vendor == "gcp":
        if not HAS_GCP_EXPORTER:
            raise RuntimeError(
                "missing Google Cloud Platform Open Telemetry dependencies. "
                "See: https://google-cloud-opentelemetry.readthedocs.io/"
            )

        tsc = None

        configuration = configuration or {}
        service_account = configuration.get(
            "otel_gcp_service_account", os.getenv("CHAOSTOOLKIT_OTEL_GCP_SA")
        )
        project_id = configuration.get(
            "otel_gcp_project_id", os.getenv("CHAOSTOOLKIT_OTEL_GCP_PROJECT_ID")
        )
        if service_account and os.path.isfile(service_account):
            credentials = Credentials.from_service_account_file(service_account)
            project_id = credentials.project_id
            tsc = TraceServiceClient(
                credentials=credentials,
                transport=TraceServiceGrpcTransport(
                    channel=TraceServiceGrpcTransport.create_channel(
                        options=GCP_TRACE_OPTIONS
                    )
                ),
            )

        resources = get_aggregated_resources(
            [GoogleCloudResourceDetector(raise_on_error=False)],
            initial_resource=resource,
        )
        provider = TracerProvider(resource=resources)
        exporter = CloudTraceSpanExporter(project_id=project_id, client=tsc)
        set_global_textmap(CloudTraceFormatPropagator())
    elif vendor == "aws":
        if not HAS_AWS_EXPORTER:
            raise RuntimeError(
                "missing AWS Open Telemetry dependencies. "
                "See: https://aws-otel.github.io/docs/getting-started/python-sdk"
            )

        resources = get_aggregated_resources(
            [AwsEc2ResourceDetector()],
            initial_resource=resource,
        )
        provider = TracerProvider(
            resources=resources, id_generator=AwsXRayIdGenerator()
        )
        set_global_textmap(AwsXRayPropagator())
    elif vendor == "azure":
        if not HAS_AZURE_EXPORTER:
            raise RuntimeError(
                "missing Azure Open Telemetry dependencies. "
                "See: https://learn.microsoft.com/en-us/python/api/overview/azure/core-tracing-opentelemetry-readme"  # noqa
            )

        settings.tracing_implementation = OpenTelemetrySpan
        exporter = AzureMonitorTraceExporter()
    else:
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter()

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    trace.get_tracer(__name__)

    logger.info("Chaos Toolkit Open Telemetry tracer created")


def configure_instrumentations(
    trace_request: bool = False,
    trace_httpx: bool = False,
    trace_botocore: bool = False,
    trace_urllib3: bool = False,
) -> None:
    provider = trace.get_tracer_provider()

    if trace_request:
        if not HAS_REQUESTS:
            logger.debug("Cannot trace requests has its missing some dependency")
        else:
            RequestsInstrumentor().instrument(tracer_provider=provider)

    if trace_httpx:
        if not HAS_HTTPX:
            logger.debug("Cannot trace httpx has its missing some dependency")
        else:
            HTTPXClientInstrumentor().instrument(tracer_provider=provider)

    if trace_botocore:
        if not HAS_BOTOCORE:
            logger.debug("Cannot trace botocore has its missing some dependency")
        else:
            BotocoreInstrumentor().instrument(tracer_provider=provider)

    if trace_urllib3:
        if not HAS_URLLIB3:
            logger.debug("Cannot trace urllib3 has its missing some dependency")
        else:
            URLLib3Instrumentor().instrument(tracer_provider=provider)


@contextmanager
def new_span(
    name: str, parent: Span = None, end_on_exit: bool = True, **kwargs
) -> Iterator[Span]:
    tracer = trace.get_tracer(__name__)
    ctx = set_span_in_context(parent)

    with tracer.start_as_current_span(
        name,
        context=ctx,
        record_exception=True,
        set_status_on_exception=True,
        end_on_exit=end_on_exit,
        **kwargs,
    ) as span:
        yield span  # type: ignore
