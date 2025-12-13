from celery import shared_task

@shared_task
def retrain_global_models():
    """
    Periodically retrains global ML models using user data.
    """
    print("Retraining global Alfred models... (Phase 4 fills ML logic)")
