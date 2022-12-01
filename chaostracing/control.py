# -*- coding: utf-8 -*-
import json
import os
import time
from typing import Any, Dict, List, NoReturn, Optional

import opentracing
from chaoslib.types import (
    Activity,
    Configuration,
    Experiment,
    Hypothesis,
    Journal,
    Run,
    Secrets,
)
from logzero import logger
from opentracing import Span, Tracer

__all__ = [
    "configure_control",
    "cleanup_control",
    "before_experiment_control",
    "after_experiment_control",
    "before_hypothesis_control",
    "after_hypothesis_control",
    "before_method_control",
    "after_method_control",
    "before_activity_control",
    "before_rollback_control",
    "after_rollback_control",
    "after_activity_control",
]


def configure_control(
    configuration: Configuration = None, secrets: Secrets = None, **kwargs
) -> Optional[Tracer]:
    """
    Configure the tracer once for the life of the experiment's execution.
    """
    logger.debug("Configuring opentracing control...")
    tracer = None
    configuration = configuration or {}
    provider = kwargs.get(
        "provider", configuration.get("tracing_provider", "noop")
    ).lower()
    logger.debug("Creating a {} tracer".format(provider))

    if provider == "noop":
        tracer = create_noop_tracer(configuration, secrets)
    elif provider == "jaeger":
        tracer = create_jaeger_tracer(configuration, secrets, **kwargs)
    elif provider == "opentelemetry":
        tracer = create_opentelemetry_tracer(configuration, secrets, **kwargs)
    else:
        logger.debug("Unsupported tracer provider: {}".format("provider"))

    if tracer is not None:
        opentracing.set_global_tracer(tracer)

    logger.debug("OpenTracing tracer {} created".format(tracer))
    return tracer


def cleanup_control() -> NoReturn:
    """
    Cleanup the tracer's resources after the experiment has completed
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    if scope is not None:
        time.sleep(0.3)
        scope.close()
        time.sleep(0.5)

    if tracer is not None and hasattr(tracer, "close"):
        time.sleep(0.3)
        tracer.close()
        time.sleep(0.5)


def before_experiment_control(context: Experiment, **kwargs):
    """
    Create a tracing span when the experiment's execution begins.
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    parent = scope.span if scope else None

    name = context.get("title")
    scope = tracer.start_active_span(name, child_of=parent, finish_on_close=True)
    scope.span.set_tag("type", "experiment")
    tags = context.get("tags")
    if tags:
        scope.span.set_tag("target", ", ".join(tags))

    contributions = context.get("contributions")
    if contributions:
        for contribution in contributions:
            scope.span.set_tag(contribution, contributions[contribution])

    if kwargs:
        _log_kv(kwargs, tracer, scope.span)


def after_experiment_control(context: Experiment, state: Journal, **kwargs):
    """
    Finishes the span created when the experiment's execution began
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    span = scope.span
    try:
        if not span:
            return

        status = state.get("status")
        span.set_tag("status", status)
    finally:
        scope.close()


def before_hypothesis_control(context: Hypothesis, **kwargs):
    """
    Create a span, child of the experiment's span, before the steady-state
    hypothesis probes are applied
    """
    tracer = opentracing.global_tracer()
    name = context.get("title")
    scope = tracer.scope_manager.active
    scope = tracer.start_active_span(name, child_of=scope.span, finish_on_close=True)
    scope.span.set_tag("type", "hypothesis")
    if kwargs:
        _log_kv(kwargs, tracer, scope.span)


def after_hypothesis_control(context: Hypothesis, state: Dict[str, Any], **kwargs):
    """
    Finishes the span created when the steady-state hypothesis began
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    span = scope.span
    try:
        if not span:
            return

        deviated = not state.get("steady_state_met")
        span.set_tag("deviated", deviated)
        if deviated and "probes" in state:
            deviated_probe = state["probes"][-1]
            span.set_tag("error", True)
            _log_kv(
                {
                    "probe": deviated_probe["activity"]["name"],
                    "expected": deviated_probe["activity"]["tolerance"],
                    "computed": deviated_probe["output"],
                },
                tracer,
                span,
            )
    finally:
        scope.close()


def before_method_control(context: Experiment, **kwargs):
    """
    Create a span, child of the experiment's span, before the method activities
    are applied
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    scope = tracer.start_active_span(
        "Method", child_of=scope.span, finish_on_close=True
    )
    scope.span.set_tag("type", "method")
    if kwargs:
        _log_kv(kwargs, tracer, scope.span)


def after_method_control(context: Experiment, state: List[Run], **kwargs):
    """
    Finishes the span created when the method began
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    if scope:
        scope.close()


def before_rollback_control(context: Experiment, **kwargs):
    """
    Create a span, child of the experiment's span, before the rollback
    activities are applied
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    scope = tracer.start_active_span(
        "Rollbacks", child_of=scope.span, finish_on_close=True
    )
    scope.span.set_tag("type", "rollback")
    if kwargs:
        _log_kv(kwargs, tracer, scope.span)


def after_rollback_control(context: Experiment, state: List[Run], **kwargs):
    """
    Finishes the span created when the rollback began
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    if scope:
        scope.close()


def before_activity_control(context: Activity, **kwargs):
    """
    Create a span, child of the method or rollback's span, before the
    activitiy is applied
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    name = context.get("name")
    scope = tracer.start_active_span(name, child_of=scope.span, finish_on_close=True)
    scope.span.set_tag("type", "activity")
    scope.span.set_tag("activity", context.get("type"))

    # special treatment for HTTP activities
    # we inject the metadata of the HTTP request
    provider = context["provider"]
    _log_kv(provider, tracer, scope.span)
    if provider["type"] == "http":
        headers = provider.get("headers", {})
        scope.span.set_tag("http.method", provider.get("method", "GET").upper())
        scope.span.set_tag("http.url", provider["url"])
        scope.span.set_tag("span.kind", "client")
        scope.span.tracer.inject(scope.span, "http_headers", headers)
        provider["headers"] = headers

    if kwargs:
        _log_kv(kwargs, tracer, scope.span)


def after_activity_control(context: Activity, state: Run, **kwargs):
    """
    Finishes the span created when the activity began
    """
    tracer = opentracing.global_tracer()
    scope = tracer.scope_manager.active
    try:
        span = scope.span
        # special treatment for HTTP activities
        # we inject the status code of the HTTP response
        provider = context["provider"]
        if provider["type"] == "http":
            output = state.get("output")
            if isinstance(output, dict):
                status = output.get("status")
                if status is not None:
                    span.set_tag("http.status_code", status)

        status = state.get("status")
        span.set_tag("status", status)
        if status == "failed":
            span.set_tag("error", True)
            _log_kv({"event": "error", "stack": state["exception"]}, tracer, span)

        tolerance_met = state.get("tolerance_met")
        if tolerance_met is not None:
            span.set_tag("deviated", 1 if tolerance_met else 0)
            span.set_tag("error", True if tolerance_met else False)

    finally:
        if scope:
            scope.close()


###############################################################################
# Internals
###############################################################################
def create_noop_tracer(configuration: Configuration = None, secrets: Secrets = None):
    """
    Create a dummy tracer that will respond to the OpenTracing API but will
    do nothing
    """
    logger.debug("The noop tracer will not send any data out")
    return opentracing.tracer


def create_jaeger_tracer(
    configuration: Configuration = None, secrets: Secrets = None, **kwargs
):
    """
    Create a Jaeger tracer
    """
    from jaeger_client import Config
    from jaeger_client.config import DEFAULT_REPORTING_PORT
    from jaeger_client.constants import BAGGAGE_HEADER_PREFIX, TRACE_ID_HEADER

    host = kwargs.get("host", configuration.get("tracing_host", "localhost"))
    port = kwargs.get("port", configuration.get("tracing_port", DEFAULT_REPORTING_PORT))
    tracer_config = Config(
        config={
            "sampler": {
                "type": "const",
                "param": 1,
            },
            "logging": True,
            "propagation": kwargs.get(
                "propagation", configuration.get("tracing_propagation", None)
            ),
            "trace_id_header": kwargs.get(
                "id_name", configuration.get("tracing_id_name", TRACE_ID_HEADER)
            ),
            "baggage_header_prefix": kwargs.get(
                "baggage_prefix",
                configuration.get("baggage_prefix", BAGGAGE_HEADER_PREFIX),
            ),
            "local_agent": {"reporting_host": host, "reporting_port": port},
        },
        service_name="chaostoolkit",
        validate=True,
    )
    addr = "{}:{}".format(host, port)
    logger.debug("Configured Jaeger Tracer to send to '{}'".format(addr))
    return tracer_config.initialize_tracer()


def create_opentelemetry_tracer(
    configuration: Configuration = None, secrets: Secrets = None, **kwargs
):
    """
    Create an OpenTelemetry tracer based of an opentracing tracer.

    Currently supported exporter are: "oltp-grpc", "oltp-http",
    "jaeger-thrift" and "jaeger-grpc".
    """
    from opentelemetry import trace
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.shim.opentracing_shim import create_tracer

    resource = None
    exporter = kwargs.get(
        "exporter", configuration.get("tracing_opentelemetry_exporter")
    )
    if exporter not in ["oltp-grpc", "oltp-http", "jaeger-thrift", "jaeger-grpc"]:
        logger.debug("Unsupported opentelemetry shim exporter: {}".format("exporter"))
        return

    # let's create our tracer
    resource = Resource.create({SERVICE_NAME: "chaostoolkit"})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = create_tracer(trace)

    # now let's attach a concrete exporter to it
    if exporter == "jaeger-thrift":
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter

        host = kwargs.get("host", configuration.get("tracing_host", "localhost"))
        port = kwargs.get("port", configuration.get("tracing_port", 6831))
        ot_exporter = JaegerExporter(agent_host_name=host, agent_port=port)
    elif exporter == "jaeger-grpc":
        from opentelemetry.exporter.jaeger.proto.grpc import JaegerExporter

        collector_endpoint = kwargs.get(
            "collector_endpoint",
            configuration.get(
                "tracing_opentelemetry_collector_endpoint", "localhost:14250"
            ),
        )
        insecure = kwargs.get(
            "collector_insecure",
            configuration.get(
                "tracing_opentelemetry_collector_endpoint_insecure", False
            ),
        )
        ot_exporter = JaegerExporter(
            collector_endpoint=collector_endpoint, insecure=insecure
        )
    elif exporter == "oltp-grpc":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        collector_endpoint = kwargs.get(
            "collector_endpoint",
            configuration.get(
                "tracing_opentelemetry_collector_endpoint", "http://localhost:4317"
            ),
        )
        insecure = kwargs.get(
            "collector_insecure",
            configuration.get(
                "tracing_opentelemetry_collector_endpoint_insecure", False
            ),
        )
        headers = kwargs.get(
            "collector_headers",
            configuration.get("tracing_opentelemetry_collector_headers", None),
        )
        ot_exporter = OTLPSpanExporter(
            endpoint=collector_endpoint, headers=headers, insecure=insecure
        )
    elif exporter == "oltp-http":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        collector_endpoint = kwargs.get(
            "collector_endpoint",
            configuration.get(
                "tracing_opentelemetry_collector_endpoint",
                os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
            ),
        )
        headers = kwargs.get(
            "collector_headers",
            configuration.get("tracing_opentelemetry_collector_headers"),
        )
        ot_exporter = OTLPSpanExporter(endpoint=collector_endpoint, headers=headers)

    baggage = kwargs.get(
        "baggage_prefix", configuration.get("tracing_opentelemetry_baggage_prefix")
    )
    if baggage:
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.propagators.b3 import B3Format

        set_global_textmap(B3Format())

    span_processor = BatchSpanProcessor(ot_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    return tracer


def _log_kv(key_values: Dict[str, Any], tracer: Any, span: Span):
    """
    OpenTracing allows for any payload to be sent by OpenTelemetry supports
    only native datatypes. So, in that case, we serialize to a json string
    when we can.
    """
    if not key_values:
        return

    if tracer.__class__.__name__ != "TracerShim":
        span.log_kv(key_values)
        return

    # opentelemetry doesn't tolerate anything but this list of types for
    # values so we can't send anything that is not one of these
    kv = {}
    for k, v in key_values.items():
        if isinstance(v, (bool, str, bytes, int, float)):
            kv[k] = v
        else:
            try:
                kv[k] = json.dumps(v, indent=False)
            except Exception:
                pass
    span.log_kv(kv)
