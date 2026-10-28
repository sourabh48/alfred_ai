"""Accounting/timing contracts without a browser or operator data."""
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from django.test import SimpleTestCase
from scripts.browser_test_runner import BrowserTestRunner


def passing_suite():
    class Cases(unittest.TestCase):
        @classmethod
        def _create_driver(cls):
            return 'synthetic driver'

        def test_first(self):
            self.assertEqual(self._create_driver(), 'synthetic driver')

        def test_second(self):
            self.assertTrue(True)
    return unittest.defaultTestLoader.loadTestsFromTestCase(Cases)


def negative_suite():
    class Cases(unittest.TestCase):
        def test_failed(self):
            self.fail('synthetic failure')

        def test_error(self):
            raise ValueError('synthetic error')

        def test_skipped(self):
            self.skipTest('synthetic skip')
    return unittest.defaultTestLoader.loadTestsFromTestCase(Cases)


def skipped_suite():
    class Cases(unittest.TestCase):
        def test_skipped(self):
            self.skipTest('synthetic skip')
    return unittest.defaultTestLoader.loadTestsFromTestCase(Cases)


def duplicate_execution_suite():
    class Cases(unittest.TestCase):
        def test_ok(self):
            pass

        def run(self, result):
            super().run(result)
            super().run(result)
    return unittest.defaultTestLoader.loadTestsFromTestCase(Cases)


class BrowserTestRunnerTests(SimpleTestCase):
    def runner(self, profile=False, **options):
        folder = self.enterContext(TemporaryDirectory(prefix='alfred-browser-accounting-'))

        class QuietRunner(BrowserTestRunner):
            def setup_test_environment(self, **kwargs):
                pass  # The enclosing Django test run already owns this environment.

            def teardown_test_environment(self, **kwargs):
                pass

            def get_test_runner_kwargs(self):
                return {**super().get_test_runner_kwargs(), 'stream': io.StringIO()}

        runner = QuietRunner(browser_report=str(Path(folder)/'result.json'), browser_profile=profile, verbosity=0, **options)
        return runner

    def test_every_pass_has_one_timing_and_exact_inventory(self):
        runner = self.runner()
        self.assertEqual(runner.run_tests([__name__+'.passing_suite']), 0)
        result = json.loads(runner.report_path.read_text())
        self.assertTrue(result['complete'])
        self.assertEqual(result['inventory'], sorted(row['id'] for row in result['tests']))
        self.assertEqual(len(result['tests']), 2)
        self.assertTrue(all(row['status']=='passed' and row['seconds']>=0 for row in result['tests']))
        self.assertEqual(len(result['checkout_sha']), 40)

    def test_failure_error_and_skip_cannot_create_passing_proof(self):
        runner = self.runner()
        self.assertEqual(runner.run_tests([__name__+'.negative_suite']), 2)
        result = json.loads(runner.report_path.read_text())
        self.assertFalse(result['complete'])
        self.assertEqual({row['status'] for row in result['tests']}, {'failed','error','skipped'})

    def test_skip_only_is_fail_closed(self):
        runner = self.runner()
        with self.assertRaisesRegex(RuntimeError, 'accounting incomplete'):
            runner.run_tests([__name__+'.skipped_suite'])
        self.assertFalse(json.loads(runner.report_path.read_text())['complete'])

    def test_duplicate_execution_is_fail_closed(self):
        runner=self.runner()
        with self.assertRaisesRegex(RuntimeError,'accounting incomplete'):
            runner.run_tests([__name__+'.duplicate_execution_suite'])
        report=json.loads(runner.report_path.read_text())
        self.assertFalse(report['complete']);self.assertEqual(len(report['execution_ids']),2)

    def test_profile_preserves_classmethod_and_records_fixture_phases(self):
        runner = self.runner(profile=True)
        self.assertEqual(runner.run_tests([__name__+'.passing_suite']), 0)
        result = json.loads(runner.report_path.read_text())
        self.assertTrue(result['complete'])
        self.assertEqual(result['phases']['Cases._create_driver']['calls'], 1)
        self.assertGreaterEqual(result['phases']['suite']['seconds'], 0)

    def test_collect_only_does_not_execute_or_claim_acceptance(self):
        runner=self.runner(browser_collect_only=True)
        self.assertEqual(runner.run_tests([__name__+'.passing_suite']),0)
        report=json.loads(runner.report_path.read_text())
        self.assertFalse(report['complete']);self.assertEqual(report['tests'],[])
        self.assertEqual(len(report['inventory']),2)

    def test_each_shard_executes_only_its_measured_assignment(self):
        cases=list(passing_suite())
        folder=self.enterContext(TemporaryDirectory(prefix='alfred-shard-duration-'))
        path=Path(folder)/'durations.json'
        path.write_text(json.dumps({'durations':{case.id():index+1 for index,case in enumerate(cases)}}))
        actual=[]
        for index in range(2):
            runner=self.runner(browser_shard_count=2,browser_shard_index=index,browser_durations_file=str(path))
            self.assertEqual(runner.run_tests([__name__+'.passing_suite']),0)
            report=json.loads(runner.report_path.read_text())
            self.assertTrue(report['complete']);self.assertEqual(len(report['tests']),1)
            actual.extend(row['id'] for row in report['tests'])
        self.assertEqual(sorted(actual),sorted(case.id() for case in cases))
