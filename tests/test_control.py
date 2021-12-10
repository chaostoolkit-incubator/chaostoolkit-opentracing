# -*- coding: utf-8 -*-
from unittest.mock import patch

import opentracing
from chaoslib.types import Configuration

from chaostracing.control import cleanup_control, configure_control


def test_create_noop_tracer(configuration: Configuration):
    assert opentracing.is_global_tracer_registered() is False
    tracer = configure_control()
    assert opentracing.is_global_tracer_registered() is True
    assert isinstance(tracer, opentracing.Tracer)
    assert tracer == opentracing.global_tracer()


def test_cleanup_control(configuration: Configuration):
    tracer = opentracing.global_tracer()
    tracer.start_active_span("boom")
    scope = tracer.scope_manager.active
    assert scope is not None

    with patch.object(scope, "close") as close:
        cleanup_control()
        assert close.call_count == 1
