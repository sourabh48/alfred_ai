from django.apps import AppConfig


class MlEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ml_engine"
    verbose_name = "ALFRED ML Engine"

    def ready(self):
        from .auto_training import bootstrap_startup_training

        bootstrap_startup_training()
