"""Structured browser accounting and opt-in phase timings, using Django's runner."""
from collections import defaultdict
from contextlib import ExitStack
from functools import wraps
import inspect
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from django.conf import settings
from django.test.runner import DiscoverRunner
from django.test.utils import iter_test_cases
from scripts.browser_test_plan import plan_tests


class BrowserTestRunner(DiscoverRunner):
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.add_argument('--browser-report', required=True)
        parser.add_argument('--browser-profile', action='store_true')
        parser.add_argument('--browser-shard-index', type=int, default=0)
        parser.add_argument('--browser-shard-count', type=int, default=1)
        parser.add_argument('--browser-durations-file')
        parser.add_argument('--browser-collect-only', action='store_true')

    def __init__(self, *args, browser_report, browser_profile=False, browser_shard_index=0,
                 browser_shard_count=1, browser_durations_file=None, browser_collect_only=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.report_path = Path(browser_report)
        self.profile = browser_profile
        self.records = {}
        self.execution_ids = []
        self.phases = defaultdict(lambda: {'seconds': 0.0, 'calls': 0})
        self.inventory = []
        self.classes = set()
        self.shard_index, self.shard_count = browser_shard_index, browser_shard_count
        self.durations_file, self.collect_only = browser_durations_file, browser_collect_only
        self.selected, self.plan = [], None
        self.test_database = ''

    def timed(self, key, function):
        @wraps(function)
        def measured(*args, **kwargs):
            started = time.monotonic()
            try:
                return function(*args, **kwargs)
            finally:
                self.phases[key]['seconds'] += time.monotonic() - started
                self.phases[key]['calls'] += 1
        return measured

    def build_suite(self, *args, **kwargs):
        suite = super().build_suite(*args, **kwargs)
        cases = list(iter_test_cases(suite))
        self.inventory = sorted(case.id() for case in cases)
        if not self.inventory or len(set(self.inventory)) != len(self.inventory):
            raise ValueError('Browser discovery must be nonempty and unique')
        self.classes = {type(case) for case in cases}
        if self.shard_count > 1 and not self.durations_file:
            raise ValueError('Measured durations required for sharding')
        if not 0 <= self.shard_index < self.shard_count:
            raise ValueError('Shard index outside requested count')
        if not self.durations_file:
            self.selected = self.inventory
            return suite
        durations = json.loads(Path(self.durations_file).read_text(encoding='utf-8'))['durations']
        self.plan = plan_tests(self.inventory, durations, self.shard_count)
        self.selected = self.plan['shards'][self.shard_index]
        selected = set(self.selected)
        return self.test_suite(case for case in cases if case.id() in selected)

    def setup_databases(self, **kwargs):
        result = self.timed('database_setup', super().setup_databases)(**kwargs)
        self.test_database = str(settings.DATABASES['default']['NAME'])
        return result

    def teardown_databases(self, *args, **kwargs):
        return self.timed('database_teardown', super().teardown_databases)(*args, **kwargs)

    def get_resultclass(self):
        owner = self

        class Result(unittest.TextTestResult):
            def startTest(self, test):
                owner.execution_ids.append(test.id())
                owner.records[test.id()] = {'id': test.id(), 'status': 'incomplete', 'started': time.monotonic()}
                super().startTest(test)

            def stopTest(self, test):
                record = owner.records[test.id()]
                record['seconds'] = round(time.monotonic() - record.pop('started'), 6)
                super().stopTest(test)

            def outcome(self, test, status):
                owner.records.setdefault(test.id(), {'id': test.id(), 'seconds': 0.0})['status'] = status

            def addSuccess(self, test):
                self.outcome(test, 'passed'); super().addSuccess(test)

            def addFailure(self, test, err):
                self.outcome(test, 'failed'); super().addFailure(test, err)

            def addError(self, test, err):
                self.outcome(test, 'error'); super().addError(test, err)

            def addSkip(self, test, reason):
                self.outcome(test, 'skipped'); super().addSkip(test, reason)

            def addExpectedFailure(self, test, err):
                self.outcome(test, 'expected_failure'); super().addExpectedFailure(test, err)

            def addUnexpectedSuccess(self, test):
                self.outcome(test, 'unexpected_success'); super().addUnexpectedSuccess(test)

            def addSubTest(self, test, subtest, err):
                if err is not None:
                    self.outcome(test, 'failed')
                super().addSubTest(test, subtest, err)

        return Result

    def run_suite(self, suite, **kwargs):
        with ExitStack() as patches:
            if self.profile:
                from tests.test_document_review_browser import DocumentReviewBrowserTests
                for cls in self.classes | {DocumentReviewBrowserTests}:
                    for name in ('setUpClass', 'setUp', 'tearDown', '_create_driver', 'login',
                                 '_login_browser', 'capture', '_capture_browser_artifacts'):
                        if name not in cls.__dict__:
                            continue
                        descriptor = inspect.getattr_static(cls, name)
                        function = descriptor.__func__ if isinstance(descriptor, (classmethod, staticmethod)) else descriptor
                        measured = self.timed(cls.__name__ + '.' + name, function)
                        if isinstance(descriptor, (classmethod, staticmethod)):
                            measured = type(descriptor)(measured)
                        patches.enter_context(patch.object(cls, name, measured))
                real_sleep = time.sleep

                def measured_sleep(seconds):
                    if sys._getframe(1).f_code.co_name == 'test_travel_d1_same_trip_complete_browser_journey' and seconds == settings.ALFRED_API_ACCOUNT_WINDOW_SECONDS:
                        return self.timed('rate_window_wait', real_sleep)(seconds)
                    return real_sleep(seconds)

                patches.enter_context(patch('time.sleep', measured_sleep))
            return self.timed('suite', super().run_suite)(suite, **kwargs)

    def run_tests(self, test_labels, **kwargs):
        started = time.monotonic()
        complete = False
        try:
            if self.collect_only:
                self.setup_test_environment()
                try:
                    self.build_suite(test_labels)
                    return 0
                finally:
                    self.teardown_test_environment()
            failures = super().run_tests(test_labels, **kwargs)
            complete = bool(self.selected) and len(self.execution_ids) == len(self.selected) and set(self.records) == set(self.selected) and all(
                row['status'] == 'passed' for row in self.records.values())
            if not failures and not complete:
                raise RuntimeError('Browser accounting incomplete or unexpected skips')
            return failures
        finally:
            payload = dict(version=1, complete=complete, inventory=self.inventory,
                execution_ids=self.execution_ids,
                selected=self.selected, plan=self.plan, shard_index=self.shard_index,
                shard_count=self.shard_count, collection_only=self.collect_only,
                tests=list(self.records.values()), phases=dict(self.phases),
                seconds=round(time.monotonic()-started, 6),
                checkout_sha=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                github_sha=os.environ.get('GITHUB_SHA',''),
                github_run_id=os.environ.get('GITHUB_RUN_ID',''),
                source_sha=os.environ.get('ALFRED_CI_SOURCE_SHA') or subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                runtime=os.environ.get('ALFRED_DATA_DIR',''), database=str(settings.DATABASES['default']['NAME']))
            payload.update(test_database=self.test_database, media=str(settings.MEDIA_ROOT),
                           cache_backend=settings.CACHES['default']['BACKEND'], process_id=os.getpid(),
                           platform=platform.system())
            self.report_path.parent.mkdir(parents=True, exist_ok=True)
            self.report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
