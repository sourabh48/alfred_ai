"""Lets live code read a historical schema that predates the FIN-15 currency columns."""
from django.apps import apps
from django.db import connection


def add_live_currency_columns(app_label):
    """Add the live models' nullable currency columns to tables that lack them.

    Only for rehearsals that run live code against an older schema: the app's money-decimal
    migration rebuilds these tables, and its FIN-15 migration then adds the columns properly.
    """
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
        for model in apps.get_app_config(app_label).get_models():
            table = model._meta.db_table
            if table not in tables:
                continue
            existing = {column.name for column in connection.introspection.get_table_description(cursor, table)}
            for field in model._meta.local_concrete_fields:
                if field.name.endswith("currency") and field.column not in existing:
                    cursor.execute(f'ALTER TABLE "{table}" ADD COLUMN "{field.column}" varchar(3) NULL')
