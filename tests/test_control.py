# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from chaoslib.types import Activity, Configuration, Experiment, Hypothesis
import opentracing
import pytest

from chaostracing.control import local, cleanup_control, configure_control, \
    before_experiment_control, after_experiment_control, \
    before_hypothesis_control, after_hypothesis_control, \
    before_method_control, after_method_control, before_rollback_control, \
    after_rollback_control, before_activity_control, after_activity_control


def test_create_tracer(configuration: Configuration):
    assert getattr(local, "tracer", None) is None
    configure_control(configuration)

    tracer = getattr(local, "tracer", None)
    assert isinstance(tracer, opentracing.Tracer)


def test_cleanup_control(configuration: Configuration):
    tracer = local.tracer
    assert isinstance(tracer, opentracing.Tracer)

    cleanup_control()
    assert getattr(local, "tracer", None) is None


def test_before_experiment_control(tracer, experiment: Experiment):
    assert tracer.experiment_span is None
    before_experiment_control(experiment)
    assert tracer.experiment_span is not None


def test_after_experiment_control(tracer, experiment: Experiment):
    before_experiment_control(experiment)
    assert tracer.experiment_span is not None
    after_experiment_control(experiment, state={})
    assert tracer.experiment_span is None


def test_before_hypothesis_control(tracer, hypothesis: Hypothesis):
    assert tracer.hypothesis_span is None
    before_hypothesis_control(hypothesis)
    assert tracer.hypothesis_span is not None


def test_after_hypothesis_control(tracer, hypothesis: Hypothesis):
    before_hypothesis_control(hypothesis)
    assert tracer.hypothesis_span is not None
    after_hypothesis_control(hypothesis, state={})
    assert tracer.hypothesis_span is None


def test_before_method_control(tracer, experiment: Experiment):
    assert tracer.method_span is None
    before_method_control(experiment)
    assert tracer.method_span is not None


def test_after_method_control(tracer, experiment: Experiment):
    before_method_control(experiment)
    assert tracer.method_span is not None
    after_method_control(experiment, state={})
    assert tracer.method_span is None


def test_before_rollback_control(tracer, experiment: Experiment):
    assert tracer.rollback_span is None
    before_rollback_control(experiment)
    assert tracer.rollback_span is not None


def test_after_method_control(tracer, experiment: Experiment):
    before_rollback_control(experiment)
    assert tracer.rollback_span is not None
    after_rollback_control(experiment, state={})
    assert tracer.rollback_span is None


def test_before_activity_control(tracer, activity: Activity):
    assert tracer.activity_span is None
    before_activity_control(activity)
    assert tracer.activity_span is not None


def test_after_activity_control(tracer, activity: Activity):
    before_activity_control(activity)
    assert tracer.activity_span is not None
    after_activity_control(activity, state={})
    assert tracer.activity_span is None
