"""A file-backed copy of isolated SQLite fixtures for real child-process tests."""
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from django.db import connection
from alfred_private_storage import private_directory


@contextmanager
def durable_fixture_database():
    assert connection.vendor == 'sqlite', 'Native persistence proof uses isolated SQLite fixtures'
    assert not connection.in_atomic_block, 'Commit fixture writes before cold-process proof'
    database = str(connection.settings_dict['NAME'])
    if Path(database).is_file():
        yield database
        return
    with TemporaryDirectory() as directory:
        database = str(private_directory(Path(directory) / 'private') / 'cold-process.sqlite3')
        with closing(sqlite3.connect(database)) as target:
            connection.connection.backup(target)
        yield database
