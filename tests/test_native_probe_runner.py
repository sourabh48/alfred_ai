"""Real subprocess exits must agree with source-bound native assertion receipts."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time

from django.test import SimpleTestCase

from alfred_native import InstanceLock
from scripts.native_probe_runner import ROOT, run_probe


CHILD = '''import argparse, json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from alfred_private_storage import private_directory
from alfred_native import runtime_directory, write_json
from scripts.native_probe_runner import source_binding
parser=argparse.ArgumentParser()
parser.add_argument('--child',action='store_true')
parser.add_argument('--report',type=Path)
parser.add_argument('--mode',default='good')
args=parser.parse_args()
data=private_directory(Path(os.environ['ALFRED_PROBE_DIRECTORY'])/'runtime')
run=os.environ['ALFRED_PROBE_RUN_ID']
(data/'.native-probe-owner.json').write_text(json.dumps({'run_id':run}),encoding='utf-8')
write_json(runtime_directory(data)/'runtime.json',{'status':'stopped'})
report=dict(run_id=run,data_dir=str(data),journey_passed=True,passed=True,
            checks={'assertion':True,'owned_native_processes_stopped':True},**source_binding(Path(__file__)))
if args.mode=='stale': report['run_id']='old-run'
if args.mode=='source': report['source_files'][Path(__file__).relative_to(Path(__file__).resolve().parents[3]).as_posix()]='wrong'
if args.mode=='incomplete': report['checks'].pop('assertion')
if args.mode=='cleanup': write_json(runtime_directory(data)/'runtime.json',{'status':'running'})
if args.mode!='missing': args.report.write_text(json.dumps(report),encoding='utf-8')
sys.stderr.write('synthetic CRLF diagnostic\\r\\n')
sys.stderr.flush()
if args.mode=='timeout': time.sleep(30)
if args.mode=='held':
    (data/'ready').touch()
    deadline=time.monotonic()+10
    while not (data/'locked').exists():
        assert time.monotonic()<deadline
        time.sleep(.01)
raise SystemExit(7 if args.mode=='nonzero' else 0)
'''


class NativeProbeRunnerTests(SimpleTestCase):
    def setUp(self):
        self.temporary = self.enterContext(TemporaryDirectory(prefix='native-runner-', dir=ROOT / 'artifacts'))
        self.folder = Path(self.temporary)
        # Keep the fixture three levels below the repo for its explicit source binding.
        self.child_folder = self.folder / 'fixture'
        self.child_folder.mkdir()
        self.script = self.child_folder / 'probe.py'
        self.script.write_text(CHILD, encoding='utf-8')

    def run_mode(self, mode, **options):
        return run_probe(self.script, self.folder / ('run-' + mode), ('assertion',),
                         extra_args=('--mode', mode), **options)

    def test_stderr_and_crlf_do_not_override_actual_zero_exit(self):
        result = self.run_mode('good')
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['process']['exit'], 0)
        self.assertFalse(result['process']['timed_out'])
        self.assertTrue(result['cleanup']['verified'])
        self.assertIn('synthetic CRLF diagnostic', (self.folder / 'run-good' / 'stderr.log').read_text())
        self.assertTrue(json.loads((self.folder / 'run-good' / 'report.json').read_text())['passed'])

    def test_nonzero_exit_rejects_even_a_complete_passed_child_report(self):
        result = self.run_mode('nonzero')
        self.assertFalse(result['passed'])
        self.assertEqual(result['process']['exit'], 7)
        self.assertEqual(result['failure'], 'child_exit')
        self.assertTrue(result['cleanup']['verified'])

    def test_zero_exit_requires_fresh_complete_source_bound_assertions(self):
        for mode, failure in (('missing', 'parent_FileNotFoundError'), ('stale', 'child_identity'),
                              ('source', 'child_source'), ('incomplete', 'child_assertions')):
            with self.subTest(mode=mode):
                result = self.run_mode(mode)
                self.assertFalse(result['passed'], result)
                self.assertEqual(result['process']['exit'], 0)
                self.assertEqual(result['failure'], failure)

    def test_claimed_cleanup_cannot_override_running_native_state(self):
        result = self.run_mode('cleanup')
        self.assertFalse(result['passed'])
        self.assertEqual(result['failure'], 'cleanup_unverified')
        self.assertFalse(result['cleanup']['initial_verified'])
        self.assertTrue(result['cleanup']['verified'])
        self.assertEqual(result['cleanup']['stop_exit'], 0)

    def test_real_held_worker_lock_rejects_cleanup_claim(self):
        data = self.folder / 'run-held' / 'data' / 'runtime'
        release = threading.Event()

        def hold():
            deadline = time.monotonic() + 15
            while not (data / 'ready').exists():
                if time.monotonic() >= deadline:
                    return
                time.sleep(.01)
            with InstanceLock(data, 'worker.lock'):
                (data / 'locked').touch()
                release.wait(15)

        thread = threading.Thread(target=hold)
        thread.start()
        try:
            result = self.run_mode('held')
            self.assertFalse(result['passed'])
            self.assertEqual(result['failure'], 'cleanup_unverified')
        finally:
            release.set()
            thread.join(15)
        self.assertFalse(thread.is_alive())

    def test_timeout_never_accepts_early_passed_json(self):
        result = self.run_mode('timeout', timeout=2)
        self.assertFalse(result['passed'])
        self.assertTrue(result['process']['timed_out'])
        self.assertIsNotNone(result['process']['exit'])
        self.assertTrue(result['cleanup']['verified'])

    def test_existing_evidence_is_never_overwritten(self):
        result = self.run_mode('good')
        self.assertTrue(result['passed'], result)
        path = self.folder / 'run-good' / 'report.json'
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_mode('good')
        self.assertEqual(path.read_bytes(), original)
