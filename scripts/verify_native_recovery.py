"""Offline Windows Travel recovery drill, confined to one owned synthetic runtime."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REQUIRED = ('graceful_restart', 'web_rollback', 'web_committed_retry', 'interrupted_upload',
            'worker_rollback_replay', 'worker_committed_replay', 'acknowledged_not_replayed',
            'worker_unavailable_queue', 'offline_model_unavailable', 'database_integrity', 'financial_source_invalidation',
            'key_and_vault_fail_closed', 'chrome_recovery_and_session_isolation',
            'privacy_and_financial_invariants', 'owned_native_processes_stopped')


def wait_for(predicate, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(.2)
    raise AssertionError('Bounded recovery condition was not reached')


def install_fault_hooks():
    """Loaded only by the disposable child-process sitecustomize, never by ALFRED."""
    import django
    original_setup = django.setup

    def setup(*args, **kwargs):
        result = original_setup(*args, **kwargs)
        from django.db import transaction
        from apps.mobility import planner_views
        from apps.mobility.services.travel import reminders
        role = next((name for name in ('serve', 'worker') if name in sys.argv), None)
        directory = Path(os.environ['ALFRED_NATIVE_TRAVEL_GUARD'])

        def point(kind, identity, occurrence=None):
            marker = directory / 'fault.json'
            if not marker.is_file():
                return
            fault = json.loads(marker.read_text(encoding='utf-8'))
            if (fault['role'] != role or fault['kind'] != kind or fault['identity'] != identity
                    or fault['run_id'] != os.environ['ALFRED_PROBE_RUN_ID']
                    or occurrence is not None and fault['occurrence'] not in occurrence):
                return
            if (directory / ('reached-' + fault['fault_id'] + '.json')).exists():
                return

            def pause():
                claims = []
                visible_occurrences = None
                if role == 'worker':
                    from huey.contrib.djhuey import HUEY
                    from alfred_ai.durable_queue import task_name
                    for row in HUEY.storage.sql('SELECT data FROM native_claim WHERE state=?', ('active',), results=True):
                        task = HUEY.deserialize_task(row[0])
                        if task_name(task).endswith('.native_travel_reminders'):
                            claims.append(task.id)
                    # A separate WAL reader observes committed state, not this worker's transaction.
                    with closing(sqlite3.connect(Path(os.environ['ALFRED_DATA_DIR'])/'db.sqlite3')) as db:
                        raw = db.execute('SELECT planning_state FROM mobility_travelplan WHERE id=?', (identity,)).fetchone()[0]
                    visible = json.loads(raw)[reminders.KEY]['deliveries']
                    visible_occurrences = sum(row['occurrence_id']==fault['occurrence'] for row in visible)
                    assert visible_occurrences == (1 if fault['mode']=='committed' else 0)
                reached = dict(run_id=fault['run_id'], fault_id=fault['fault_id'], role=role,
                               mode=fault['mode'], pid=os.getpid(), parent_pid=os.getppid(), claims=claims,
                               committed_occurrences=visible_occurrences)
                from alfred_native import write_json
                write_json(directory / ('reached-' + fault['fault_id'] + '.json'), reached)
                # The orchestrator must kill this owned process at the recorded boundary.
                deadline = time.monotonic() + 45
                while marker.exists() and time.monotonic() < deadline:
                    time.sleep(.1)
                if marker.exists():
                    raise RuntimeError('Synthetic recovery barrier expired')
            if fault['mode'] == 'committed':
                transaction.on_commit(pause)
            else:
                assert transaction.get_connection().in_atomic_block
                pause()

        original_edit = planner_views.apply_edit
        def edit(session, data):
            value = original_edit(session, data)
            point('editor', session.pk)
            return value
        planner_views.apply_edit = edit
        original_save = reminders._save
        def save(plan, policy):
            old = {row['occurrence_id'] for row in plan.planning_state.get(reminders.KEY, {}).get('deliveries', [])}
            value = original_save(plan, policy)
            new = {row['occurrence_id'] for row in policy['deliveries']} - old
            if new:
                point('reminder', plan.pk, new)
            return value
        reminders._save = save
        return result
    django.setup = setup


def child(args):
    from alfred_private_storage import private_directory
    from scripts.native_probe_runner import source_binding
    from scripts.verify_native_travel import GUARD, isolated_environment
    folder = private_directory(Path(os.environ['ALFRED_PROBE_DIRECTORY']).resolve())
    run_id = os.environ['ALFRED_PROBE_RUN_ID']
    env = isolated_environment(folder)
    env.update(ALFRED_PROBE_RUN_ID=run_id)
    guard = folder / 'network-guard'
    with (guard / 'sitecustomize.py').open('a', encoding='utf-8') as stream:
        stream.write('\nfrom scripts.verify_native_recovery import install_fault_hooks\ninstall_fault_hooks()\n')
    data = folder / 'runtime'
    (data / '.native-probe-owner.json').write_text(json.dumps(dict(run_id=run_id)), encoding='utf-8')
    report = dict(run_id=run_id, data_dir=str(data), passed=False, journey_passed=False,
                  checks={}, crashes=[], lifecycle=[], stage='startup', **source_binding(Path(__file__)))
    from alfred_native import InstanceLock, read_state, write_json, parent_is_running
    def save():
        write_json(args.report, report)
    def mark(name, evidence=True):
        report['checks'][name] = evidence
        save(); print('PASS ' + name, flush=True)
    def stage(name):
        report['stage'] = name; save()
    save()
    os.environ.clear(); os.environ.update(env)
    exec(GUARD, {'__name__': '__native_recovery_guard__'})
    browser = probe = None
    base = None

    def command(action, expected=True):
        began = time.monotonic()
        result = subprocess.run([sys.executable, str(ROOT / 'alfred_native.py'), action,
            '--data-dir', str(data), '--port', str(args.port), '--no-browser'], cwd=ROOT,
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        index = len(report['lifecycle'])
        (folder / f'lifecycle-{index}-{action}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        report['lifecycle'].append(dict(action=action, exit=result.returncode,
            expected_success=expected, seconds=round(time.monotonic()-began, 3)))
        save()
        assert (result.returncode == 0) == expected, 'Unexpected native lifecycle exit'
        return result

    def locks_free():
        try:
            with InstanceLock(data), InstanceLock(data, 'worker.lock'):
                return True
        except OSError:
            return False

    def start():
        nonlocal base
        command('start')
        state = read_state(data)
        base = 'http://127.0.0.1:' + str(state['port'])
        return state

    def arm(role, kind, identity, mode, occurrence=None):
        fault = dict(run_id=run_id, fault_id=uuid4().hex, role=role, kind=kind,
                     identity=identity, mode=mode, occurrence=occurrence)
        write_json(guard / 'fault.json', fault)
        return fault

    def reached(fault, seconds=30):
        path = guard / ('reached-' + fault['fault_id'] + '.json')
        wait_for(path.is_file, seconds)
        point = json.loads(path.read_text(encoding='utf-8'))
        assert point['run_id'] == run_id and point['fault_id'] == fault['fault_id']
        return point

    def terminate(point):
        assert (data / '.native-probe-owner.json').is_file()
        assert json.loads((data / '.native-probe-owner.json').read_text())['run_id'] == run_id
        state = read_state(data)
        entries = [json.loads(p.read_text().splitlines()[0]) for p in guard.glob('network-*.jsonl')]
        assert any(row['pid'] == point['pid'] and row['parent_pid'] == point['parent_pid'] for row in entries)
        if point['role'] == 'serve':
            assert point['pid'] == state['pid']
        else:
            assert state['worker_pid'] in (point['pid'], point['parent_pid'])
        assert point['pid'] != os.getpid() and parent_is_running(point['pid'])
        # Retain the pause until termination; never release an uncommitted write.
        os.kill(point['pid'], signal.SIGTERM)
        wait_for(lambda: not parent_is_running(point['pid']))
        (guard / 'fault.json').unlink(missing_ok=True)
        report['crashes'].append(point); save()

    try:
        start()
        from alfred_native import configure
        configure(data)
        from django.conf import settings
        assert Path(settings.DATABASES['default']['NAME']).resolve()==data/'db.sqlite3'
        assert Path(settings.ALFRED_MEMORY_DIR).resolve().is_relative_to(data)
        from django.contrib.sessions.models import Session
        from django.db import connections
        from django.core.cache import cache
        from django.utils import timezone as django_timezone
        from alfred_ai.native_tasks import native_runtime_probe
        from huey.contrib.djhuey import HUEY
        from apps.mobility.services.travel_conversation import save_plan
        from apps.mobility.services.travel import reminders
        from tests import test_travel_affordability as finance
        from tests.test_travel_financial_reconciliation import TravelFinancialReconciliationTests
        from tests.test_user_data_browser import UserDataBrowserTests as UI
        from tests.test_travel_ics_export import parse_calendar
        from tests.user_acceptance_scenario import PASSWORD
        import requests
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import StaleElementReferenceException
        class Probe(unittest.TestCase):
            travel_editor_fixture = UI.travel_editor_fixture
            login, text, memory_click = UI.login, UI.text, UI.memory_click
            affordability_fields = UI.affordability_fields
        probe = Probe(); finance.TravelAffordabilityTests.setUp(probe)
        probe.user.city = 'Bengaluru'; probe.user.set_password(PASSWORD); probe.user.save()
        probe.other.set_password(PASSWORD); probe.other.save()
        probe.scenario = {'user': probe.user}
        trip = probe.travel_editor_fixture(); save_plan(trip); trip.refresh_from_db()
        endpoint = f'/api/mobility/planner/sessions/{trip.pk}/'
        canary = 'D3B_PRIVATE_CANARY_' + uuid4().hex
        client = requests.Session(); client.trust_env = False

        def post(path, body=None, **kwargs):
            response = client.post(base + path, json=body if not kwargs else None,
                headers={'X-CSRFToken': client.cookies['csrftoken'], 'Referer': base + path},
                timeout=35, allow_redirects=False, **kwargs)
            return response
        def login(session, user):
            session.get(base + '/login/', timeout=15).raise_for_status()
            response = session.post(base + '/login/', data={'username':user.username, 'password':PASSWORD},
                headers={'X-CSRFToken':session.cookies['csrftoken']}, timeout=20, allow_redirects=False)
            assert response.status_code == 302
        login(client, probe.user)
        def payload():
            response = client.get(base + endpoint, timeout=20)
            assert response.status_code == 200
            return response.json()
        def change(body):
            response = post(endpoint, body)
            assert response.status_code == 200, 'Synthetic Travel action failed'
            return response.json()
        def money():
            rows = TravelFinancialReconciliationTests.snapshot(probe)
            rows = {k:v for k,v in rows.items() if not k.startswith('mobility.')}
            for row in rows.get('users.User', []): row.pop('last_login', None)
            return rows
        def digest(value):
            return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
        def trip_state():
            trip.refresh_from_db(); trip.plan.refresh_from_db()
            return dict(state=trip.state, itinerary=trip.itinerary, plan=trip.plan.planning_state,
                        saved=trip.plan.itinerary, revision=trip.revision)
        money_before = money()
        initial = payload()
        change(dict(action='packing', operation='add', checklist_revision=initial['packing_checklist']['revision'],
                    item_id=str(uuid4()), label='Recovery gloves'))
        def reminder(operation, **fields):
            return change(dict(action='reminders', operation=operation, request_id=str(uuid4()),
                               reminder_revision=payload()['travel_reminders']['revision']) | fields)
        reminder('consent', enabled=True)
        reminder('create', reminder_id=str(uuid4()), label='Pending across restart', zone='UTC',
                 local_time=(datetime.now(timezone.utc)+timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'))
        upload = post('/api/ai/document-corpus/upload/', data={'consent':'true','days':'7'},
                      files={'file':('recovery-private.txt', canary.encode(), 'text/plain')})
        assert upload.status_code == 200
        document = upload.json()['document']
        change(dict(action='trip_documents', operation='link', revision=payload()['revision'],
                    document_id=document['id'], fingerprint=document['source_fingerprint']))
        change(dict(action='save', revision=payload()['revision']))
        original = '/api/ai/document-corpus/' + document['id'] + '/original/'
        vault = Path(settings.ALFRED_MEMORY_DIR)
        def corpus_rows():
            with closing(sqlite3.connect(vault / 'verified.sqlite3')) as db:
                return db.execute('SELECT COUNT(*) FROM document_corpus').fetchone()[0]
        assert corpus_rows() == 1

        def exports():
            from io import BytesIO
            from lxml import etree
            from pypdf import PdfReader
            current = payload()
            preview = change(dict(action='calendar_preview', revision=current['revision']))
            for kind in ('pdf','gpx','ics'):
                body = dict(action='export_'+kind, revision=current['revision'])
                if kind == 'ics': body['calendar'] = dict(snapshot=preview['snapshot'], events=[])
                response = post(endpoint, body); assert response.status_code == 200
                if kind == 'pdf':
                    assert current['itinerary']['destination'] in '\n'.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
                elif kind == 'gpx':
                    xml = etree.fromstring(response.content, etree.XMLParser(resolve_entities=False, no_network=True))
                    assert xml.xpath('//*[local-name()="wpt"]') and not xml.xpath('//*[local-name()="trk" or local-name()="rte"]')
                else:
                    assert parse_calendar(response.content)['roundtrip']
        stage('graceful_restart')
        before = trip_state(); before_digest = digest(before)
        exports()
        assert client.get(base+original, timeout=20).content == canary.encode()
        first_instance = read_state(data)['instance']
        command('start'); assert read_state(data)['instance'] == first_instance
        command('stop'); wait_for(locks_free)
        queued = native_runtime_probe('d3b-offline-' + run_id)
        assert HUEY.pending_count() >= 1 and queued.get() is None
        start(); assert read_state(data)['instance'] != first_instance
        recovered = queued.get(blocking=True, timeout=30)
        assert recovered['worker_pid'] != os.getpid()
        assert digest(trip_state()) == before_digest
        exports(); assert client.get(base+original, timeout=20).content == canary.encode()
        assert corpus_rows() == 1 and money() == money_before
        mark('graceful_restart', dict(before=before_digest, after=digest(trip_state())))
        mark('worker_unavailable_queue')
        response=post('/api/ai/personal-insights/', {'query':'Suggest a quiet holiday activity.', 'scope':'general'})
        assert response.status_code==503 and response.json()['code']=='local_model_unavailable'
        assert client.get(base+'/health/native/',timeout=15).status_code==200
        mark('offline_model_unavailable')

        stage('web_crashes')
        for mode in ('rollback', 'committed'):
            current = payload(); before = trip_state()
            title = 'Recovery activity ' + mode
            body = dict(action='itinerary_edit', operation='add', revision=current['revision'], request_id=str(uuid4()),
                        day_id=current['itinerary']['days'][0]['id'], fields={'title':title})
            fault = arm('serve','editor',trip.pk,mode)
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(post, endpoint, body)
                point = reached(fault)
                terminate(point)
                try:
                    future.result(timeout=35)
                except requests.RequestException:
                    pass
                else:
                    raise AssertionError('Killed pending HTTP request unexpectedly succeeded')
            connections.close_all(); wait_for(locks_free)
            if mode == 'rollback': assert digest(trip_state()) == digest(before)
            else: assert trip_state()['revision'] == before['revision'] + 1
            start()
            change(body)
            after = payload()
            assert sum(item['title'] == title for day in after['itinerary']['days'] for item in day['items']) == 1
            assert after['revision'] == before['revision'] + 1
            change(body); assert payload()['revision'] == after['revision']
            mark('web_rollback' if mode == 'rollback' else 'web_committed_retry',
                 dict(before=digest(before), after=digest(trip_state()), crash=point))
        stale=dict(body,request_id=str(uuid4()))
        assert post(endpoint,stale).status_code==409
        change(dict(action='save', revision=payload()['revision']))

        stage('interrupted_upload')
        before_upload = corpus_rows()
        state = read_state(data)
        wire = socket.create_connection(('127.0.0.1',state['port']), timeout=5)
        cookies = '; '.join(k+'='+v for k,v in client.cookies.items())
        prefix = (f'POST /api/ai/document-corpus/upload/ HTTP/1.1\r\nHost: 127.0.0.1:{state["port"]}\r\n'
                  f'Cookie: {cookies}\r\nX-CSRFToken: {client.cookies["csrftoken"]}\r\n'
                  'Content-Type: multipart/form-data; boundary=d3b\r\nContent-Length: 65536\r\n\r\n'
                  '--d3b\r\nContent-Disposition: form-data; name="file"; filename="interrupted.txt"\r\n\r\npartial')
        wire.sendall(prefix.encode()); time.sleep(.3)
        entries = [json.loads(p.read_text().splitlines()[0]) for p in guard.glob('network-*.jsonl')]
        point = next(row for row in entries if row['pid'] == state['pid']) | {'role':'serve','kind':'interrupted_upload'}
        terminate(point); wire.close(); wait_for(locks_free); start()
        assert corpus_rows() == before_upload
        mark('interrupted_upload')

        stage('worker_crashes')
        for mode in ('rollback', 'committed'):
            due = datetime.now(timezone.utc).replace(second=0,microsecond=0) + timedelta(minutes=2)
            created = reminder('create', reminder_id=str(uuid4()), label='Crash boundary '+mode,
                               zone='UTC', local_time=due.strftime('%Y-%m-%dT%H:%M'))
            occurrence = created['travel_reminders']['reminders'][-1]['occurrence_id']
            old = deepcopy(payload()['travel_reminders']['deliveries'])
            fault = arm('worker','reminder',trip.plan_id,mode,occurrence)
            point = reached(fault, max(1,(due-datetime.now(timezone.utc)).total_seconds())+80)
            assert point['claims']
            assert point['committed_occurrences']==(1 if mode=='committed' else 0)
            terminate(point)
            def replayed():
                trip.plan.refresh_from_db()
                rows = trip.plan.planning_state[reminders.KEY]['deliveries']
                return rows if any(row['occurrence_id']==occurrence for row in rows) else None
            deliveries = wait_for(replayed, 45)
            assert len(deliveries) == len(old)+1
            assert sum(row['occurrence_id']==occurrence for row in deliveries) == 1
            def acknowledged():
                return all(HUEY.storage.sql('SELECT COUNT(*) FROM native_history WHERE task_id=? AND outcome=?',
                    (identity,'complete'),results=True)[0][0] == 1 for identity in point['claims'])
            wait_for(acknowledged, 45)
            recovery = json.loads((data/'artifacts/native/job-recovery.json').read_text())
            assert recovery['requeued'] >= 1
            mark('worker_rollback_replay' if mode=='rollback' else 'worker_committed_replay',
                 dict(crash=point, deliveries_before=len(old), deliveries_after=len(deliveries), recovery=recovery))
        acknowledged_ids = [identity for point in report['crashes'] for identity in point.get('claims', [])]
        command('stop'); wait_for(locks_free); start()
        for identity in acknowledged_ids:
            assert HUEY.storage.sql('SELECT COUNT(*) FROM native_history WHERE task_id=? AND outcome=?',
                                   (identity,'complete'),results=True)[0][0] == 1
        assert len(payload()['travel_reminders']['deliveries']) == 2
        mark('acknowledged_not_replayed')

        stage('financial_invalidation')
        source = client.get(base+endpoint+'affordability/',timeout=20).json()
        confirmation = finance.TravelAffordabilityTests.confirmation(probe)
        body = dict(revision=source['trip']['revision'], snapshot=source['trip']['snapshot'], confirmation=confirmation)
        assert post(endpoint+'affordability/',body).status_code == 200
        probe.expense.amount='51.00'; probe.expense.save(update_fields=['amount'])
        response = post(endpoint+'affordability/',body)
        assert response.status_code == 409 and response.json()['code'] == 'source_changed'
        probe.expense.amount='50.00'; probe.expense.save(update_fields=['amount'])
        assert money() == money_before
        mark('financial_source_invalidation')

        stage('key_and_vault')
        command('stop'); wait_for(locks_free); connections.close_all()
        key, index = vault/'journal.key', vault/'verified.sqlite3'
        key_bytes, index_bytes = key.read_bytes(), index.read_bytes()
        assert not Path(str(index)+'-wal').exists() or Path(str(index)+'-wal').stat().st_size==0
        assert key_bytes.startswith(b'M15DPAPI1\x00') and canary.encode() not in index_bytes
        (folder/'retained-key').write_bytes(key_bytes)
        (folder/'retained-index.sqlite3').write_bytes(index_bytes)
        for kind in ('missing_key','corrupt_key','corrupt_vault'):
            try:
                if kind == 'missing_key': key.rename(vault/'journal.key.retained')
                elif kind == 'corrupt_key': key.write_bytes(b'M15DPAPI1\x00invalid-synthetic-key')
                else: index.write_bytes(b'invalid-synthetic-sqlite-vault')
                command('start', expected=False); wait_for(locks_free)
                if kind == 'missing_key': assert not key.exists()
                elif kind == 'corrupt_key': assert key.read_bytes()==b'M15DPAPI1\x00invalid-synthetic-key'
                else: assert index.read_bytes()==b'invalid-synthetic-sqlite-vault'
            finally:
                command('stop'); wait_for(locks_free)
                if kind == 'missing_key':
                    if key.exists(): key.rename(vault/'journal.key.unexpected-retained')
                    (vault/'journal.key.retained').rename(key)
                elif kind == 'corrupt_key': key.write_bytes(key_bytes)
                else: index.write_bytes(index_bytes)
        index.rename(vault/'verified.sqlite3.retained')
        start()
        assert client.get(base+original,timeout=20).status_code == 404
        assert payload()['trip_documents'][0]['status'] != 'available'
        command('stop'); wait_for(locks_free)
        index.rename(vault/'verified.sqlite3.empty-retained')
        (vault/'verified.sqlite3.retained').rename(index)
        start()
        assert key.read_bytes() == key_bytes and client.get(base+original,timeout=20).content == canary.encode()
        assert corpus_rows() == 1
        mark('key_and_vault_fail_closed')

        stage('chrome_recovery')
        options = webdriver.ChromeOptions()
        for value in ('--headless=new','--disable-gpu','--no-sandbox','--window-size=1440,1200',
                      '--disable-background-networking','--disable-quic','--proxy-server=http://127.0.0.1:9',
                      '--proxy-bypass-list=127.0.0.1;localhost;[::1]', '--user-data-dir='+str(folder/'chrome-profile')):
            options.add_argument(value)
        browser=webdriver.Chrome(options=options)
        browser.execute_cdp_cmd('Network.enable', {})
        browser.execute_cdp_cmd('Network.setBlockedURLs', {'urls':['https://*']})
        probe.browser,probe.By,probe.wait=browser,By,WebDriverWait(browser,25,ignored_exceptions=(StaleElementReferenceException,))
        probe.live_server_url=base; probe.login(probe.user.username)
        browser.get(base+'/mobility/?session='+str(trip.pk))
        probe.wait.until(lambda _: 'Recovery gloves' in probe.text('plannerPacking'))
        assert 'Recovery activity committed' in probe.text('plannerItinerary')
        assert browser.find_elements(By.CSS_SELECTOR,'#plannerDocuments a[href*="/original/"]')
        probe.wait.until(lambda _: len(browser.find_elements(By.CSS_SELECTOR,'[data-reminder-delivery]'))==2)
        browser.save_screenshot(str(folder/'reopened-desktop.png'))
        command('stop'); wait_for(locks_free); start(); browser.refresh()
        probe.wait.until(lambda _: 'Recovery gloves' in probe.text('plannerPacking'))
        browser.set_window_size(390,1100)
        assert browser.execute_script('return document.documentElement.scrollWidth<=innerWidth')
        browser.save_screenshot(str(folder/'reopened-narrow.png'))
        stranger=requests.Session();stranger.trust_env=False;login(stranger,probe.other)
        assert stranger.get(base+endpoint,timeout=20).status_code==404
        assert stranger.get(base+original,timeout=20).status_code==404
        assert client.post(base+endpoint,json={'action':'save'},timeout=20).status_code==403
        cookie=browser.get_cookie(settings.SESSION_COOKIE_NAME)
        Session.objects.filter(session_key=cookie['value']).update(expire_date=django_timezone.now()-timedelta(seconds=1))
        probe.memory_click('[data-packing-reload]')
        probe.wait.until(lambda _: not browser.find_element(By.ID,'plannerPacking').is_displayed())
        assert probe.text('plannerDocuments')==''
        Session.objects.filter(session_key=client.cookies[settings.SESSION_COOKIE_NAME]).delete()
        assert client.get(base+original,timeout=20).status_code in (401,403)
        mark('chrome_recovery_and_session_isolation')
        command('stop'); wait_for(locks_free); connections.close_all()
        for database in (data/'db.sqlite3',data/'artifacts/native/jobs.sqlite3',vault/'verified.sqlite3'):
            with closing(sqlite3.connect(database)) as db:
                assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
                assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        mark('database_integrity')
        assert money()==money_before and corpus_rows()==1
        for path in folder.rglob('*.log'):
            content=path.read_bytes()
            assert canary.encode() not in content and key_bytes not in content, 'Private diagnostic canary leaked'
        mark('privacy_and_financial_invariants')
        report['journey_passed']=True
    except Exception as error:
        report['failure']=dict(stage=report['stage'], exception_type=type(error).__name__)
        if browser:
            browser.save_screenshot(str(folder/'failure.png'))
            (folder/'failure.html').write_text(browser.page_source,encoding='utf-8')
        raise
    finally:
        cleanup_ok=False
        try:
            try:
                if browser: browser.quit()
            finally:
                if probe: assert probe.doCleanups()
            cleanup_ok=True
        finally:
            try:
                if (guard/'fault.json').exists(): (guard/'fault.json').unlink()
                command('stop'); wait_for(locks_free)
                if 'connections' in locals(): connections.close_all()
                mark('owned_native_processes_stopped')
                report['passed']=bool(report['journey_passed']) and cleanup_ok and 'failure' not in report
            finally:
                save()
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child',action='store_true')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--port',type=int,default=8047)
    args=parser.parse_args()
    if os.name!='nt': parser.error('Actual Windows native/DPAPI required')
    if args.child:
        if not args.report or not os.environ.get('ALFRED_PROBE_RUN_ID'): parser.error('Owned parent runner required')
        return child(args)
    from scripts.native_probe_runner import run_probe
    output=args.output or ROOT/'artifacts/native-recovery'/uuid4().hex[:10]
    result=run_probe(Path(__file__),output,REQUIRED,timeout=1500,extra_args=('--port',str(args.port)))
    print(json.dumps(dict(passed=result['passed'], report=str(output/'report.json'))))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
