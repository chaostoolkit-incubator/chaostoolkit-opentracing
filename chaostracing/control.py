# -*- coding: utf-8 -*-
from typing import Any, Dict, List
import threading
import time

from chaoslib.types import Activity, Configuration, Experiment, Hypothesis, \
    Journal, Run, Secrets
from logzero import logger
import opentracing

__all__ = ["configure_control", "cleanup_control", "before_experiment_control",
           "after_experiment_control", "before_hypothesis_control",
           "after_hypothesis_control", "before_method_control",
           "after_method_control", "before_activity_control",
           "before_rollback_control", "after_rollback_control",
           "after_activity_control"]

# hold a reference to the tracer for the given thread
local = threading.local()


def configure_control(configuration: Configuration = None,
                      secrets: Secrets = None):
    """
    Configure the tracer once for the life of the experiment's execution.
    """
    provider = configuration.get("tracing_provider", "noop").lower()
    logger.debug("Creating a {} tracer".format(provider))

    if provider == "noop":
        local.tracer = create_noop_tracer(configuration, secrets)
    elif provider == "jaeger":
        local.tracer = create_jaeger_tracer(configuration, secrets)
    else:
        logger.debug("Unsupported tracer provider: {}".format('provider'))
        return

    # this should not be needed if all providers supported OpenTracing 2 but
    # this is not the case (notably Jaeger is lagging badly)
    tracer = local.tracer
    tracer.experiment_span = None
    tracer.hypothesis_span = None
    tracer.method_span = None
    tracer.rollback_span = None
    tracer.activity_span = None


def cleanup_control():
    """
    Cleanup the tracer's resources after the experiment has completed
    """
    tracer = local.tracer
    local.tracer = None
    tracer.experiment_span = None
    tracer.hypothesis_span = None
    tracer.method_span = None
    tracer.rollback_span = None
    tracer.activity_span = None

    if hasattr(tracer, 'close'):
        time.sleep(0.2)
        tracer.close()
        time.sleep(0.5)


def before_experiment_control(context: Experiment, **kwargs):
    """
    Create a tracing span when the experiment's execution begins.
    """
    tracer = local.tracer
    name = context.get("title")
    span = tracer.start_span(name)
    tracer.experiment_span = span

    span.set_tag('type', 'experiment')
    tags = context.get("tags")
    if tags:
        span.set_tag('target', ', '.join(tags))

    contributions = context.get("contributions")
    if contributions:
        for contribution in contributions:
            span.set_tag(contribution, contributions[contribution])

    if kwargs:
        span.log_kv(kwargs)


def after_experiment_control(context: Experiment, state: Journal, **kwargs):
    """
    Finishes the span created when the experiment's execution began
    """
    tracer = local.tracer
    span = tracer.experiment_span
    try:
        if not span:
            return

        status = state.get("status")
        span.set_tag('status', status)
    finally:
        tracer.experiment_span = None
        span.finish()


def before_hypothesis_control(context: Hypothesis, **kwargs):
    """
    Create a span, child of the experiment's span, before the steady-state
    hypothesis probes are applied
    """
    tracer = local.tracer
    name = context.get("title")
    span = tracer.start_span(name, child_of=tracer.experiment_span)
    tracer.hypothesis_span = span
    span.set_tag('type', 'hypothesis')
    if kwargs:
        span.log_kv(kwargs)


def after_hypothesis_control(context: Hypothesis, state: Dict[str, Any],
                             **kwargs):
    """
    Finishes the span created when the steady-state hypothesis began
    """
    tracer = local.tracer
    span = tracer.hypothesis_span
    if not tracer.hypothesis_span:
        return

    try:
        deviated = not state.get("steady_state_met")
        span.set_tag('deviated', deviated)
        if deviated and "probes" in state:
            deviated_probe = state["probes"][-1]
            span.log_kv({
                "probe": deviated_probe["activity"]["name"],
                "expected": deviated_probe["activity"]["tolerance"],
                "computed": deviated_probe["output"]
            })
    finally:
        tracer.hypothesis_span = None
        span.finish()


def before_method_control(context: Experiment, **kwargs):
    """
    Create a span, child of the experiment's span, before the method activities
    are applied
    """
    tracer = local.tracer
    span = tracer.start_span(
        "Method", child_of=tracer.experiment_span)
    tracer.method_span = span
    span.set_tag('type', 'method')
    if kwargs:
        span.log_kv(kwargs)


def after_method_control(context: Experiment, state: List[Run], **kwargs):
    """
    Finishes the span created when the method began
    """
    tracer = local.tracer
    if tracer.method_span:
        tracer.method_span.finish()
        tracer.method_span = None


def before_rollback_control(context: Experiment, **kwargs):
    """
    Create a span, child of the experiment's span, before the rollback
    activities are applied
    """
    tracer = local.tracer
    span = tracer.start_span(
        "Rollbacks", child_of=tracer.experiment_span)
    tracer.rollback_span = span
    span.set_tag('type', 'rollback')
    if kwargs:
        span.log_kv(kwargs)


def after_rollback_control(context: Experiment, state: List[Run], **kwargs):
    """
    Finishes the span created when the rollback began
    """
    tracer = local.tracer
    if tracer.rollback_span:
        tracer.rollback_span.finish()
        tracer.rollback_span = None


def before_activity_control(context: Activity, **kwargs):
    """
    Create a span, child of the method or rollback's span, before the
    activitiy is applied
    """
    tracer = local.tracer
    name = context.get("name")
    parent_span = tracer.hypothesis_span or tracer.method_span or \
        tracer.rollback_span or tracer.experiment_span
    span = tracer.start_span(name, child_of=parent_span)
    tracer.activity_span = span
    span.set_tag('type', 'activity')
    span.set_tag('activity', context.get("type"))

    # special treatment for HTTP activities
    # we inject the metadata of the HTTP request
    provider = context["provider"]
    span.log_kv(provider)
    if provider["type"] == "http":
        headers = provider.get("headers", {})
        span.set_tag(
            'http.method', provider.get("method", "GET").upper())
        span.set_tag('http.url', provider["url"])
        span.set_tag('span.kind', 'client')
        span.tracer.inject(span, 'http_headers', headers)
        provider["headers"] = headers

    if kwargs:
        span.log_kv(kwargs)


def after_activity_control(context: Activity, state: Run, **kwargs):
    """
    Finishes the span created when the activity began
    """
    tracer = local.tracer
    span = tracer.activity_span
    try:
        # special treatment for HTTP activities
        # we inject the status code of the HTTP response
        provider = context["provider"]
        if provider["type"] == "http":
            output = state.get("output")
            if isinstance(output, dict):
                status = output.get("status")
                if status is not None:
                    span.set_tag('http.status_code', status)

        status = state.get("status")
        span.set_tag('status', status)
        if status == "failed":
            span.log_kv({
                "event": "error",
                "stack": state["exception"]
            })

        tolerance_met = state.get("tolerance_met")
        if tolerance_met is not None:
            span.set_tag('deviated', 1 if tolerance_met else 0)

        span.finish()
    finally:
        tracer.activity_span = None


###############################################################################
# Internals
###############################################################################
def create_noop_tracer(configuration: Configuration = None,
                       secrets: Secrets = None):
    """
    Create a dummy tracer that will respond to the OpenTRacing API but will
    do nothing
    """
    logger.debug("The noop tracer will not send any data out")
    return opentracing.tracer


def create_jaeger_tracer(configuration: Configuration = None,
                         secrets: Secrets = None):
    """
    Create a Jaeger tracer
    """
    from jaeger_client.config import DEFAULT_REPORTING_PORT
    from jaeger_client.constants import TRACE_ID_HEADER, \
        BAGGAGE_HEADER_PREFIX
    from jaeger_client import Config

    host = configuration.get("tracing_host", "localhost")
    port = configuration.get("tracing_port", DEFAULT_REPORTING_PORT)
    tracer_config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
            'propagation': configuration.get('tracing_propagation', None),
            'trace_id_header': configuration.get(
                "tracing_id_name", TRACE_ID_HEADER),
            'baggage_header_prefix': configuration.get(
                "baggage_prefix", BAGGAGE_HEADER_PREFIX),
            'local_agent': {
                'reporting_host': host,
                'reporting_port': port
            }
        },
        service_name='chaostoolkit',
        validate=True,
    )
    addr = "{}:{}".format(host, port)
    logger.debug("Configured Jaeger Tracer to send to '{}'".format(addr))
    return tracer_config.initialize_tracer()
