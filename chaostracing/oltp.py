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
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource, get_aggregated_resources
from opentelemetry.sdk.trace import Span, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_span_in_context

try:
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

__all__ = [
    "configure_control",
    "before_activity_control",
    "after_activity_control",
]

REGISTRY_HANDLER = None


def configure_control(
    experiment: Experiment,
    event_registry: EventHandlerRegistry,
    trace_request: bool = False,
    trace_httpx: bool = False,
    trace_botocore: bool = False,
    configuration: Configuration = None,
    secrets: Secrets = None,
    **kwargs: Any,
) -> None:
    configure_traces(configuration)
    configure_instrumentations(trace_request, trace_httpx, trace_botocore)

    global REGISTRY_HANDLER
    REGISTRY_HANDLER = OLTPRunEventHandler()
    event_registry.register(REGISTRY_HANDLER)

    REGISTRY_HANDLER.started(experiment, None)


def before_activity_control(
    context: Activity,
    configuration: Configuration = None,
    secrets: Secrets = None,
    **kwargs: Any,
) -> None:
    REGISTRY_HANDLER.start_activity(context)


def after_activity_control(
    context: Activity,
    state: Run,
    configuration: Configuration = None,
    secrets: Secrets = None,
    **kwargs: Any,
) -> None:
    REGISTRY_HANDLER.activity_completed(context, state)


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
        stack = ExitStack()
        span = stack.enter_context(new_span("experiment"))
        span.set_attribute("chaostoolkit.experiment.title", experiment.get("title"))
        span.set_attribute("chaostoolkit.platform.full", platform.platform())

        self.root_stack = stack
        self.root_span = span
        self.current_span = span

    def finish(self, journal: Journal) -> None:
        span = self.root_span
        self.root_span = None

        span.set_attribute("chaostoolkit.experiment.status", journal.get("status"))
        span.set_attribute("chaostoolkit.experiment.deviated", journal.get("deviated"))

        self.root_stack.close()

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
    resource = Resource.create({"service.name": "chaostoolkit"})

    vendor = configuration.get("otel_vendor", os.getenv("OTEL_VENDOR"))
    if vendor is None:
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter()
    elif vendor == "gcp":
        if not HAS_GCP_EXPORTER:
            raise RuntimeError(
                "missing Google Cloud Platform Open Telemetry dependencies. "
                "See: https://google-cloud-opentelemetry.readthedocs.io/"
            )

        resources = get_aggregated_resources(
            [GoogleCloudResourceDetector(raise_on_error=False)],
            initial_resource=resource,
        )
        provider = TracerProvider(resource=resources)
        exporter = CloudTraceSpanExporter()
        set_global_textmap(CloudTraceFormatPropagator())

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    trace.get_tracer(__name__)

    logger.info("Chaos Toolkit Open Telemetry tracer created")


def configure_instrumentations(
    trace_request: bool = False, trace_httpx: bool = False, trace_botocore: bool = False
) -> None:
    provider = trace.get_tracer_provider()

    if trace_request:
        RequestsInstrumentor().instrument(tracer_provider=provider)

    if trace_httpx:
        HTTPXClientInstrumentor().instrument(tracer_provider=provider)

    if trace_botocore:
        BotocoreInstrumentor().instrument(tracer_provider=provider)


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
