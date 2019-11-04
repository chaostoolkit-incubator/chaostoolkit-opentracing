# -*- coding: utf-8 -*-
from typing import Any, Dict, List, NoReturn, Optional
import time

from chaoslib.types import Activity, Configuration, Experiment, Hypothesis, \
    Journal, Run, Secrets
from logzero import logger
import opentracing
from opentracing import Tracer

__all__ = ["configure_control", "cleanup_control", "before_experiment_control",
           "after_experiment_control", "before_hypothesis_control",
           "after_hypothesis_control", "before_method_control",
           "after_method_control", "before_activity_control",
           "before_rollback_control", "after_rollback_control",
           "after_activity_control"]


def configure_control(configuration: Configuration = None,
                      secrets: Secrets = None, **kwargs) -> Optional[Tracer]:
    """
    Configure the tracer once for the life of the experiment's execution.
    """
    logger.debug("Configuring opentracing control...")
    tracer = None
    configuration = configuration or {}
    provider = kwargs.get(
        "provider", configuration.get("tracing_provider", "noop")).lower()
    logger.debug("Creating a {} tracer".format(provider))

    if provider == "noop":
        tracer = create_noop_tracer(configuration, secrets)
    elif provider == "jaeger":
        tracer = create_jaeger_tracer(configuration, secrets, **kwargs)
    else:
        logger.debug("Unsupported tracer provider: {}".format('provider'))

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

    if tracer is not None and hasattr(tracer, 'close'):
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
    scope = tracer.start_active_span(
        name, child_of=parent, finish_on_close=True)
    scope.span.set_tag('type', 'experiment')
    tags = context.get("tags")
    if tags:
        scope.span.set_tag('target', ', '.join(tags))

    contributions = context.get("contributions")
    if contributions:
        for contribution in contributions:
            scope.span.set_tag(contribution, contributions[contribution])

    if kwargs:
        scope.span.log_kv(kwargs)


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
        span.set_tag('status', status)
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
    scope = tracer.start_active_span(
        name, child_of=scope.span, finish_on_close=True)
    scope.span.set_tag('type', 'hypothesis')
    if kwargs:
        scope.span.log_kv(kwargs)


def after_hypothesis_control(context: Hypothesis, state: Dict[str, Any],
                             **kwargs):
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
        span.set_tag('deviated', deviated)
        if deviated and "probes" in state:
            deviated_probe = state["probes"][-1]
            span.set_tag("error", True)
            span.log_kv({
                "probe": deviated_probe["activity"]["name"],
                "expected": deviated_probe["activity"]["tolerance"],
                "computed": deviated_probe["output"]
            })
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
        "Method", child_of=scope.span, finish_on_close=True)
    scope.span.set_tag('type', 'method')
    if kwargs:
        scope.span.log_kv(kwargs)


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
        "Rollbacks", child_of=scope.span, finish_on_close=True)
    scope.span.set_tag('type', 'rollback')
    if kwargs:
        scope.span.log_kv(kwargs)


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
    scope = tracer.start_active_span(
        name, child_of=scope.span, finish_on_close=True)
    scope.span.set_tag('type', 'activity')
    scope.span.set_tag('activity', context.get("type"))

    # special treatment for HTTP activities
    # we inject the metadata of the HTTP request
    provider = context["provider"]
    scope.span.log_kv(provider)
    if provider["type"] == "http":
        headers = provider.get("headers", {})
        scope.span.set_tag(
            'http.method', provider.get("method", "GET").upper())
        scope.span.set_tag('http.url', provider["url"])
        scope.span.set_tag('span.kind', 'client')
        scope.span.tracer.inject(scope.span, 'http_headers', headers)
        provider["headers"] = headers

    if kwargs:
        scope.span.log_kv(kwargs)


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
                    span.set_tag('http.status_code', status)

        status = state.get("status")
        span.set_tag('status', status)
        if status == "failed":
            span.set_tag("error", True)
            span.log_kv({
                "event": "error",
                "stack": state["exception"]
            })

        tolerance_met = state.get("tolerance_met")
        if tolerance_met is not None:
            span.set_tag('deviated', 1 if tolerance_met else 0)
            span.set_tag('error', True if tolerance_met else False)

    finally:
        if scope:
            scope.close()


###############################################################################
# Internals
###############################################################################
def create_noop_tracer(configuration: Configuration = None,
                       secrets: Secrets = None):
    """
    Create a dummy tracer that will respond to the OpenTracing API but will
    do nothing
    """
    logger.debug("The noop tracer will not send any data out")
    return opentracing.tracer


def create_jaeger_tracer(configuration: Configuration = None,
                         secrets: Secrets = None, **kwargs):
    """
    Create a Jaeger tracer
    """
    from jaeger_client.config import DEFAULT_REPORTING_PORT
    from jaeger_client.constants import TRACE_ID_HEADER, \
        BAGGAGE_HEADER_PREFIX
    from jaeger_client import Config

    host = kwargs.get(
        "host", configuration.get("tracing_host", "localhost"))
    port = kwargs.get(
        "port", configuration.get("tracing_port", DEFAULT_REPORTING_PORT))
    tracer_config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
            'propagation': kwargs.get(
                "propagation", configuration.get('tracing_propagation', None)),
            'trace_id_header': kwargs.get(
                "id_name", configuration.get(
                    "tracing_id_name", TRACE_ID_HEADER)),
            'baggage_header_prefix': kwargs.get(
                "baggage_prefix", configuration.get(
                    "baggage_prefix", BAGGAGE_HEADER_PREFIX)),
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
