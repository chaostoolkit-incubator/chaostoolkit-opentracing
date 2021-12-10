import opentracing
import pytest
from chaoslib.types import Activity, Configuration, Experiment, Hypothesis

from chaostracing.control import cleanup_control, configure_control


@pytest.fixture
def configuration() -> Configuration:
    return {"tracing_provider": "noop"}


@pytest.fixture
def tracer(configuration: Configuration) -> opentracing.Tracer:
    try:
        tracer = configure_control(configuration)
        yield tracer
    finally:
        cleanup_control()


@pytest.fixture
def experiment() -> Experiment:
    return {
        "title": "This is an experiment",
        "tags": ["tag1", "tag2"],
        "contributions": {"availability": "high"},
        "steady-state-hypothesis": {
            "title": "This is an hypothesis",
            "probes": [
                {
                    "name": "probe-1",
                    "type": "probe",
                    "provider": {
                        "type": "python",
                        "module": "os.path",
                        "func": "exists",
                        "arguments": {"path": __file__},
                    },
                }
            ],
        },
        "method": [
            {
                "name": "action-1",
                "type": "action",
                "provider": {
                    "type": "python",
                    "module": "os.path",
                    "func": "mkdir",
                    "arguments": {"path": "/tmp/test"},
                },
            }
        ],
    }


@pytest.fixture
def hypothesis(experiment: Experiment) -> Hypothesis:
    return experiment.get("steady-state-hypothesis")


@pytest.fixture
def activity(experiment: Experiment) -> Activity:
    return experiment["method"][0]
