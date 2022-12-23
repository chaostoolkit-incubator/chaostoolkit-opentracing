from chaoslib.types import Configuration, Experiment, Journal, Secrets

__all__ = ["after_experiment_control", "configure_control", "cleanup_control"]
METER = None
EXPERIMENT_DURATION = None


def configure_control(
    configuration: Configuration = None, secrets: Secrets = None, **kwargs
) -> None:
    """
    Create recorders and counters for the experiment's lifetime
    """
    raise NotImplementedError()


def after_experiment_control(context: Experiment, state: Journal, **kwargs):
    raise NotImplementedError()


def cleanup_control() -> None:
    raise NotImplementedError()
