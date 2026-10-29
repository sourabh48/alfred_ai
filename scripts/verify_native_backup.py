"""Same-device Windows backup/restore proof using a fresh synthetic runtime only."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REQUIRED = ('encrypted_backup_and_independent_restore', 'corrupt_missing_wrong_key_rejected',
            'interrupted_restore_not_published', 'existing_destination_preserved',
            'restored_databases_keys_originals_and_permissions', 'native_restart_http_and_chrome',
            'privacy_and_no_duplicate_records')


def child(args):
    from alfred_private_storage import verify_private
    from alfred_native import InstanceLock, configure, read_state, write_json
    from scripts.native_probe_runner import source_binding
    from scripts.verify_native_travel import isolated_environment, GUARD
    from scripts.verify_native_recovery import wait_for
    from scripts import release_recovery as recovery
    from scripts.release_gate import GateError
    from apps.ml_engine.services.memory_key import protect_key
    from cryptography.fernet import Fernet
    folder = Path(os.environ['ALFRED_PROBE_DIRECTORY']).resolve()
    run_id = os.environ['ALFRED_PROBE_RUN_ID']
    # Recovery destinations must remain outside the source checkout.
    assert not folder.is_relative_to(ROOT) and json.loads((folder/'.native-probe-owner.json').read_text()) == {'run_id': run_id}
    env = isolated_environment(folder)
    env['ALFRED_PROBE_RUN_ID'] = run_id
    data = folder/'runtime'
    (data/'.native-probe-owner.json').write_text(json.dumps(dict(run_id=run_id)))
    report = dict(run_id=run_id, data_dir=str(data), passed=False, journey_passed=False,
                  checks={}, stage='startup', **source_binding(Path(__file__)))
    def stage(name):
        report['stage'] = name
        write_json(args.report, report)
    def mark(name, evidence=True):
        report['checks'][name] = evidence
        stage(name)
        print('PASS '+name, flush=True)
    os.environ.clear(); os.environ.update(env)
    exec(GUARD, {'__name__': '__native_backup_guard__'})
    browser = None
    connections = None
    interrupted = None
    base = None
    def command(action, expected=True):
        nonlocal base
        result = subprocess.run([sys.executable, str(ROOT/'alfred_native.py'), action,
            '--data-dir', str(data), '--port', str(args.port), '--no-browser'], cwd=ROOT,
            capture_output=True, timeout=180)
        with (folder/'lifecycle.log').open('ab') as log:
            log.write(result.stdout+result.stderr)
        assert (result.returncode == 0) == expected
        if action == 'start' and expected:
            base = 'http://127.0.0.1:'+str(read_state(data)['port'])
    def locks_free():
        try:
            with InstanceLock(data), InstanceLock(data, 'worker.lock'):
                return True
        except OSError:
            return False
    def stop():
        command('stop'); wait_for(locks_free)
        if connections is not None:
            connections.close_all()
    stage('startup')
    try:
        command('start')
        configure(data)
        from django.conf import settings
        from django.db import connections
        from tests import test_travel_affordability as finance
        from tests.test_user_data_browser import UserDataBrowserTests as UI
        from tests.user_acceptance_scenario import PASSWORD
        from apps.mobility.services.travel_conversation import save_plan
        import requests
        class Probe(unittest.TestCase):
            travel_editor_fixture = UI.travel_editor_fixture
        probe = Probe(); finance.TravelAffordabilityTests.setUp(probe)
        probe.scenario = {'user': probe.user}
        for user in (probe.user, probe.other):
            user.set_password(PASSWORD); user.save()
        trip = probe.travel_editor_fixture(); save_plan(trip)
        endpoint = f'/api/mobility/planner/sessions/{trip.pk}/'
        base = 'http://127.0.0.1:'+str(read_state(data)['port'])
        def login(user):
            session = requests.Session(); session.trust_env = False
            session.get(base+'/login/', timeout=15).raise_for_status()
            result = session.post(base+'/login/', data={'username':user.username, 'password':PASSWORD},
                headers={'X-CSRFToken':session.cookies['csrftoken']}, timeout=20, allow_redirects=False)
            assert result.status_code == 302
            return session
        client = login(probe.user)
        canary = ('D3C_PRIVATE_'+uuid4().hex).encode()
        upload = client.post(base+'/api/ai/document-corpus/upload/', data={'consent':'true','days':'7'},
            files={'file':('backup-original.txt',canary,'text/plain')},
            headers={'X-CSRFToken':client.cookies['csrftoken']}, timeout=35)
        assert upload.status_code == 200
        document = upload.json()['document']
        original = '/api/ai/document-corpus/'+document['id']+'/original/'
        payload = client.get(base+endpoint,timeout=20).json()
        link = client.post(base+endpoint, json=dict(action='trip_documents',operation='link',
            revision=payload['revision'],document_id=document['id'],fingerprint=document['source_fingerprint']),
            headers={'X-CSRFToken':client.cookies['csrftoken']}, timeout=20)
        assert link.status_code == 200
        assert client.get(base+original,timeout=20).content == canary
        stop()
        vault = Path(settings.ALFRED_MEMORY_DIR)
        assert vault.resolve().is_relative_to(data)
        vault_key = (vault/'journal.key').read_bytes()
        assert vault_key.startswith(b'M15DPAPI1\0')
        key = folder/'synthetic-backup.key'
        key.write_bytes(b'M15DPAPI1\0'+protect_key(Fernet.generate_key()))
        backup = folder/'encrypted-backup'
        stage('backup')
        receipt = recovery.create(data, backup, key, 'd3c-'+run_id, report['source_sha'], report['source_sha'])
        assert receipt['LOCAL_BACKUP_VERIFIED']=='PASS' and receipt['key_kind']=='WINDOWS_PROFILE_BOUND'
        assert all(receipt[name]=='NOT_RUN' for name in ('OFF_DEVICE_COPY_VERIFIED','PORTABLE_KEY_VERIFIED','INDEPENDENT_DEVICE_LOSS_RESTORE_VERIFIED'))
        archive_hash = recovery.release.sha256(backup/'recovery.zip')
        assert canary not in (backup/'recovery.zip').read_bytes()
        mark('encrypted_backup_and_independent_restore', receipt)
        for name in ('missing','corrupt','wrong-key','missing-key','corrupt-key'):
            rejected = folder/('rejected-'+name)
            if name in ('missing','corrupt'):
                selected = folder/('backup-'+name)
                shutil.copytree(backup, selected)
                archive = selected/'recovery.zip'
                archive.rename(selected/'retained-recovery.zip')
                if name == 'corrupt': archive.write_bytes(b'synthetic corrupt archive')
                chosen_key = key
            else:
                selected = backup
                chosen_key = folder/(name+'.key')
                if name == 'wrong-key': chosen_key.write_bytes(b'M15DPAPI1\0'+protect_key(Fernet.generate_key()))
                if name == 'corrupt-key': chosen_key.write_bytes(b'M15DPAPI1\0invalid-synthetic-key')
            try:
                recovery.restore(selected, chosen_key, rejected)
            except Exception:
                assert not rejected.exists()
            else:
                raise AssertionError('Invalid backup/key was accepted')
        mark('corrupt_missing_wrong_key_rejected')
        destination = folder/'interrupted-restore'
        marker = folder/'restore-barrier.json'
        code = """import json,sys,time
from pathlib import Path
from scripts import release_recovery as r
def barrier(*args,**kwargs):
    import os
    from alfred_native import write_json
    write_json(Path(sys.argv[4]),{'pid':os.getpid(),'parent_pid':os.getppid(),'run':sys.argv[5]})
    time.sleep(120)
r.verify=barrier
r.restore(*map(Path,sys.argv[1:4]))
"""
        interrupted = subprocess.Popen([sys.executable,'-c',code,str(backup),str(key),str(destination),str(marker),run_id],
            env=env, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        wait_for(marker.is_file)
        reached = json.loads(marker.read_text())
        assert reached['run']==run_id and interrupted.poll() is None
        assert interrupted.pid in (reached['pid'],reached['parent_pid'])
        os.kill(reached['pid'],signal.SIGTERM)
        assert interrupted.wait(timeout=15)!=0
        assert not destination.exists()
        retained = list(folder.glob(destination.name+'.restore-incomplete-*'))
        assert len(retained)==1 and verify_private(retained[0])
        assert (retained[0]/'db.sqlite3').is_file()
        assert recovery.restore(backup,key,destination)['LOCAL_BACKUP_VERIFIED']=='PASS'
        assert retained[0].is_dir()
        mark('interrupted_restore_not_published',dict(child_exit=interrupted.returncode,retained_staging=True,fresh_retry=True))
        before = recovery.database_snapshot(destination/'db.sqlite3')
        try:
            recovery.restore(backup,key,destination)
        except GateError as error:
            assert str(error)=='recovery_destination_must_be_new'
        else:
            raise AssertionError('Existing restore was overwritten')
        assert recovery.database_snapshot(destination/'db.sqlite3')==before
        assert recovery.release.sha256(backup/'recovery.zip')==archive_hash
        mark('existing_destination_preserved')
        stage('restored_validation')
        verified = backup/'independent-local-restore'
        metadata = json.loads((verified/'manifest.json').read_text())
        for name,snapshot in metadata['database_snapshots'].items():
            assert recovery.database_snapshot(destination/name)==snapshot
        for row in metadata['files']:
            assert recovery.release.sha256(destination/row['backup_path'])==row['sha256']
            assert verify_private(destination/row['backup_path'])
        assert (destination/vault.relative_to(data)/'journal.key').read_bytes()==vault_key
        mark('restored_databases_keys_originals_and_permissions',dict(databases=len(metadata['database_snapshots']),files=len(metadata['files'])))
        from scripts.release_promotion import canonical_snapshot
        canonical = canonical_snapshot(data/'db.sqlite3')
        # Both trees are synthetic, stopped and confined by the parent's ownership nonce.
        assert json.loads((data/'.native-probe-owner.json').read_text())=={'run_id':run_id} and locks_free()
        os.chdir(folder)  # Windows cannot rename the process's current directory.
        data.rename(folder/'runtime-before-restore')
        destination.rename(data)
        (data/'.native-probe-owner.json').write_text(json.dumps(dict(run_id=run_id)))
        command('start')
        client = login(probe.user)
        assert client.get(base+endpoint,timeout=20).status_code==200
        assert client.get(base+original,timeout=20).content==canary
        foreign = login(probe.other)
        assert foreign.get(base+original,timeout=20).status_code==404
        assert foreign.get(base+endpoint,timeout=20).status_code==404
        assert client.post(base+endpoint,json={'action':'save'},timeout=20).status_code==403
        stop(); command('start')
        assert client.get(base+original,timeout=20).content==canary
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        options = webdriver.ChromeOptions()
        for value in ('--headless=new','--disable-gpu','--no-sandbox','--window-size=1440,1100',
                      '--disable-background-networking','--proxy-server=http://127.0.0.1:9',
                      '--proxy-bypass-list=127.0.0.1;localhost;[::1]','--user-data-dir='+str(folder/'chrome-profile')):
            options.add_argument(value)
        browser = webdriver.Chrome(options=options)
        browser.execute_cdp_cmd('Network.enable',{})
        browser.execute_cdp_cmd('Network.setBlockedURLs',{'urls':['https://*']})
        browser.get(base+'/login/')
        for cookie in client.cookies:
            browser.add_cookie(dict(name=cookie.name,value=cookie.value,path='/'))
        browser.get(base+'/mobility/?session='+str(trip.pk))
        WebDriverWait(browser,30).until(lambda b: b.find_elements(By.CSS_SELECTOR,'#plannerDocuments a[href*="/original/"]'))
        browser.save_screenshot(str(folder/'restored-desktop.png'))
        browser.set_window_size(390,1100)
        assert browser.execute_script('return document.documentElement.scrollWidth<=innerWidth')
        browser.save_screenshot(str(folder/'restored-narrow.png'))
        mark('native_restart_http_and_chrome')
        browser.quit(); browser=None
        stop()
        for name in metadata['database_snapshots']:
            with closing(sqlite3.connect(data/name)) as db:
                assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
                assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        with closing(sqlite3.connect(vault/'verified.sqlite3')) as db:
            assert db.execute('SELECT COUNT(*) FROM document_corpus').fetchone()[0]==1
        assert (vault/'journal.key').read_bytes()==vault_key
        assert canonical_snapshot(data/'db.sqlite3')==canonical
        for log in folder.rglob('*.log'):
            assert canary not in log.read_bytes() and vault_key not in log.read_bytes()
        assert recovery.release.sha256(backup/'recovery.zip')==archive_hash
        mark('privacy_and_no_duplicate_records')
        report['journey_passed']=True
    except Exception as error:
        report['failure']=dict(stage=report['stage'],exception_type=type(error).__name__)
        raise
    finally:
        if interrupted is not None and interrupted.poll() is None:
            interrupted.terminate(); interrupted.wait(timeout=15)
        if browser is not None: browser.quit()
        stop()
        mark('owned_native_processes_stopped')
        report['passed']=report['journey_passed'] and 'failure' not in report
        write_json(args.report,report)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child',action='store_true')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--port',type=int,default=8048)
    args=parser.parse_args()
    if os.name!='nt': parser.error('Actual Windows native/DPAPI required')
    if args.child:
        if not args.report or not os.environ.get('ALFRED_PROBE_RUN_ID'): parser.error('Owned parent runner required')
        child(args); return 0
    if not args.output or args.output.resolve().is_relative_to(ROOT):
        parser.error('Choose a new isolated output outside the source checkout')
    from scripts.native_probe_runner import run_probe
    result=run_probe(Path(__file__),args.output,REQUIRED,timeout=1200,extra_args=('--port',str(args.port)))
    print(json.dumps(dict(passed=result['passed'],report=str(args.output/'report.json'))))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
