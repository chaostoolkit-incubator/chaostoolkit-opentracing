from chaoslib.types import Configuration, Experiment, Journal, Secrets
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController

__all__ = ["after_experiment_control", "before_experiment_control"]
METER = None
EXPERIMENT_DURATION = None


def configure_control(
    configuration: Configuration = None, secrets: Secrets = None, **kwargs
) -> None:
    """
    Create recorders and counters for the experiment's lifetime
    """
    global EXPERIMENT_DURATION, METER

    metrics.set_meter_provider(MeterProvider(shutdown_on_exit=False))
    METER = metrics.get_meter(__name__, True)
    exporter = ConsoleMetricsExporter()
    controller = PushController(METER, exporter, 1)

    EXPERIMENT_DURATION = METER.create_valuerecorder(
        name="experiment-duration",
        description="duration of the experiment",
        unit="millisecond",
        value_type=float,
    )


def after_experiment_control(context: Experiment, state: Journal, **kwargs):
    duration = state["duration"]
    EXPERIMENT_DURATION.record(duration, {})


def cleanup_control() -> None:
    METER.shutdown()


import time

configure_control()
after_experiment_control(None, {"duration": 67.9})
after_experiment_control(None, {"duration": 47.9})
time.sleep(5)
