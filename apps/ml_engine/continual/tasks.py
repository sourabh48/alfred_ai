from celery import shared_task

from apps.ml_engine.training.orchestrator import run_training_cycle


@shared_task
def run_global_training_cycle():
    return run_training_cycle(trigger="scheduled")
