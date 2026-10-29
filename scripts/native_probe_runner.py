"""Parent-owned exit, source and cleanup evidence for isolated native probes."""
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def source_binding(script):
    script = Path(script).resolve()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                   stderr=subprocess.PIPE, text=True).strip()
    changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT,
                                      stderr=subprocess.PIPE, text=True).splitlines()
    changed += subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'],
                                       cwd=ROOT, stderr=subprocess.PIPE, text=True).splitlines()
    paths = {name for name in changed if Path(name).suffix in {'.py', '.js', '.css', '.html'}}
    paths.update((script.relative_to(ROOT).as_posix(), 'scripts/native_probe_runner.py',
                  'scripts/verify_native_travel.py'))
    return dict(source_sha=head, source_files={name: sha256((ROOT / name).read_bytes()).hexdigest()
                                              for name in sorted(paths) if (ROOT / name).is_file()})


def _owned_cleanup(folder, run_id, env, *, stop_if_needed):
    from alfred_native import InstanceLock, read_state
    data = folder / 'runtime'
    owner = json.loads((folder / '.native-probe-owner.json').read_text(encoding='utf-8'))
    if owner != {'run_id': run_id} or not data.is_dir():
        return dict(verified=False, reason='owned_runtime_missing')

    def stopped():
        with InstanceLock(data), InstanceLock(data, 'worker.lock'):
            return read_state(data).get('status') == 'stopped'

    try:
        verified = stopped()
    except OSError:
        verified = False
    result = dict(verified=verified, initial_verified=verified)
    if not verified and stop_if_needed:
        process = subprocess.run([sys.executable, str(ROOT / 'alfred_native.py'), 'stop',
                                  '--data-dir', str(data), '--no-browser'], cwd=ROOT,
                                 env=env, capture_output=True, timeout=180)
        result['stop_exit'] = process.returncode
        result['verified'] = process.returncode == 0 and stopped()
    return result


def run_probe(script, output, required_checks, timeout=900, extra_args=()):
    """A child cannot certify its own process exit; only this fresh parent receipt can."""
    from alfred_private_storage import private_directory
    from scripts.release_validation import environment, safe_log
    script, output = Path(script).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Native probe output must be a new directory.')
    private_directory(output)
    folder = private_directory(output / 'data')
    run_id = uuid4().hex
    (folder / '.native-probe-owner.json').write_text(json.dumps({'run_id': run_id}), encoding='utf-8')
    child_path = output / 'child.json'
    binding = source_binding(script)
    env = environment(output / 'launcher')
    env.update(ALFRED_PROBE_DIRECTORY=str(folder), ALFRED_PROBE_RUN_ID=run_id)
    result = dict(passed=False, run_id=run_id, **binding, child_report='child.json', checks={},
                  process={'exit': None, 'timed_out': False}, cleanup={'verified': False})
    process = None
    try:
        with (output / 'stdout.log').open('wb') as stdout, (output / 'stderr.log').open('wb') as stderr:
            options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
            process = subprocess.Popen([sys.executable, str(script), '--child', '--report', str(child_path),
                                        *map(str, extra_args)], cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                       **options)
            result['process']['pid'] = process.pid
            try:
                result['process']['exit'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result['process']['timed_out'] = True
                if process.poll() is None:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                       capture_output=True, timeout=15, check=True)
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                result['process']['exit'] = process.wait(timeout=15)
        child = json.loads(child_path.read_text(encoding='utf-8'))
        result['checks'] = child.get('checks', {})
        result['child_sha256'] = sha256(child_path.read_bytes()).hexdigest()
        owned = json.loads((folder / 'runtime' / '.native-probe-owner.json').read_text(encoding='utf-8'))
        required = set(required_checks) | {'owned_native_processes_stopped'}
        if result['process']['timed_out']:
            result['failure'] = 'child_timeout'
        elif result['process']['exit'] != 0:
            result['failure'] = 'child_exit'
        elif child.get('run_id') != run_id or owned != {'run_id': run_id}:
            result['failure'] = 'child_identity'
        elif Path(child.get('data_dir', '')).resolve() != folder / 'runtime':
            result['failure'] = 'child_runtime'
        elif (child.get('source_sha') != binding['source_sha'] or
              any(child.get('source_files', {}).get(name) != value for name, value in binding['source_files'].items()) or
              source_binding(script) != binding):
            result['failure'] = 'child_source'
        elif (child.get('passed') is not True or child.get('journey_passed') is not True or child.get('failure') or
              not required.issubset(result['checks']) or any(not result['checks'][name] for name in required)):
            result['failure'] = 'child_assertions'
    except Exception as error:
        result['failure'] = 'parent_' + type(error).__name__
    finally:
        try:
            result['cleanup'] = _owned_cleanup(folder, run_id, env, stop_if_needed=True)
        except Exception as error:
            result['cleanup'] = dict(verified=False, reason=type(error).__name__)
        if not result.get('failure') and not result['cleanup'].get('initial_verified'):
            result['failure'] = 'cleanup_unverified'
        result['passed'] = not result.get('failure') and result['cleanup']['verified']
        if not result['passed'] and not result.get('failure'):
            result['failure'] = 'cleanup_unverified'
        for stream in ('stdout', 'stderr'):
            path = output / (stream + '.log')
            if path.is_file():
                result['process'][stream + '_sha256'] = sha256(path.read_bytes()).hexdigest()
                # Raw isolated child output stays in the protected evidence directory.
                (output / (stream + '-summary.log')).write_text(safe_log(path.read_text(encoding='utf-8', errors='replace')),
                                                              encoding='utf-8')
        (output / 'report.json').write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
    return result
