# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from chaoslib.types import Activity, Configuration, Experiment, Hypothesis
import opentracing
import pytest

from chaostracing.control import cleanup_control, configure_control, \
    before_experiment_control, after_experiment_control, \
    before_hypothesis_control, after_hypothesis_control, \
    before_method_control, after_method_control, before_rollback_control, \
    after_rollback_control, before_activity_control, after_activity_control


def test_create_noop_tracer(configuration: Configuration):
    assert opentracing.is_global_tracer_registered() is False
    tracer = configure_control()
    assert opentracing.is_global_tracer_registered() is True
    assert isinstance(tracer, opentracing.Tracer)
    assert tracer == opentracing.global_tracer()


def test_cleanup_control(configuration: Configuration):
    tracer = opentracing.global_tracer()
    span = tracer.start_active_span('boom')
    scope = tracer.scope_manager.active
    assert scope is not None

    with patch.object(scope, 'close') as close:
        cleanup_control()
        assert close.call_count == 1
