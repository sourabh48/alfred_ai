"""The application's small, shared subset of the Celery/Huey task APIs."""
import os
from functools import update_wrapper


if os.environ.get("ALFRED_TASK_BACKEND") != "huey":
    from celery import shared_task
else:
    from huey.contrib.djhuey import db_task

    class NativeTask:
        def __init__(self, function, **options):
            update_wrapper(self, function)
            self.run = function
            self.name = options.pop("name", f"{function.__module__}.{function.__name__}")
            self.queued = db_task(name=self.name, **options)(function)

        def __call__(self, *args, **kwargs):
            # Calling a Celery task directly has always been synchronous.
            return self.run(*args, **kwargs)

        def delay(self, *args, **kwargs):
            return self.queued(*args, **kwargs)

    def shared_task(function=None, **options):
        def decorate(fn):
            return NativeTask(fn, **options)
        return decorate(function) if function is not None else decorate
