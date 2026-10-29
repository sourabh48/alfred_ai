"""Bounded, synthetic Travel acceptance over real Windows native HTTP/Huey/Chrome.

All Python probe processes are loopback-only; the installed application and
operator configuration are never opened. Crash/restore/installer tests are separate.
"""
import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import ipaddress
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import time
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def allowed_address(host, port=None):
    if port == 11434:
        return False
    if isinstance(host, bytes):
        host = host.decode('ascii', errors='replace')
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


GUARD = '''import json, os, sys
from pathlib import Path
from scripts.verify_native_travel import allowed_address
log = Path(os.environ['ALFRED_NATIVE_TRAVEL_GUARD']) / ('network-' + str(os.getpid()) + '.jsonl')
def record(kind):
    with log.open('a', encoding='utf-8') as output:
        output.write(json.dumps(dict(pid=os.getpid(), parent_pid=os.getppid(), kind=kind)) + '\\n')
def guard(event, args):
    if event == 'socket.getaddrinfo':
        host, port = args[:2]
        # Waitress resolves its numeric default even with a prebound loopback listener.
        if host in ('0.0.0.0', '::', None) and port != 11434:
            return
    elif event in ('socket.gethostbyname', 'socket.gethostbyaddr'):
        host, port = args[0], None
    elif event in ('socket.bind', 'socket.connect', 'socket.sendto', 'socket.getnameinfo'):
        address = args[-1] if event == 'socket.sendto' else args[0] if event == 'socket.getnameinfo' else args[1]
        host, port = address[:2] if isinstance(address, tuple) else (None, None)
    else:
        return
    if not allowed_address(host, port):
        record('ollama_denied' if port == 11434 else 'external_denied')
        raise PermissionError('native_travel_probe_network_denied')
sys.addaudithook(guard)
record('guard_installed')
'''


def isolated_environment(folder):
    from alfred_private_storage import private_directory
    from scripts.release_validation import environment
    folder = Path(folder).resolve()
    env = environment(folder / 'runtime')
    private_directory(folder / 'runtime')
    guard = private_directory(folder / 'network-guard')
    (guard / 'sitecustomize.py').write_text(GUARD, encoding='utf-8')
    env.update(PYTHONPATH=os.pathsep.join((str(guard), str(ROOT))),
               ALFRED_NATIVE_TRAVEL_GUARD=str(guard), SE_OFFLINE='true', SE_AVOID_STATS='true')
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8046)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This drill requires actual Windows DPAPI and the native runtime.')
    from alfred_private_storage import private_directory
    folder = private_directory(ROOT / 'artifacts' / 'native-travel' / uuid4().hex[:10])
    report_path = args.report.resolve() if args.report else folder / 'report.json'
    report = dict(source_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  data_dir=str(folder), passed=False, checks={}, pending=['manual_accessibility', 'independent_review',
                    'D3-B_crash_restart', 'D3-C_backup_restore_install', 'production_acceptance'])
    changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT, text=True).splitlines()
    changed += subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'],
                                       cwd=ROOT, text=True).splitlines()
    report['source_files'] = {name: sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in changed if (ROOT / name).is_file()}
    env = isolated_environment(folder)
    data = folder / 'runtime'
    os.environ.clear(); os.environ.update(env)
    runpy.run_path(str(folder / 'network-guard' / 'sitecustomize.py'))
    stage = 'startup'
    browser = probe = None

    def save():
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')

    def passed(name, evidence=True):
        report['checks'][name] = evidence
        save()
        print('PASS ' + name, flush=True)

    def command(action):
        result = subprocess.run([sys.executable, str(ROOT / 'alfred_native.py'), action,
            '--data-dir', str(data), '--port', str(args.port), '--no-browser'], cwd=ROOT,
            env=os.environ.copy(), capture_output=True, text=True, timeout=300)
        (folder / (action + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        assert result.returncode == 0, 'Native lifecycle command failed: ' + action

    try:
        # These probes fail before DNS/connect and never contact external services/Ollama.
        for host, port in (('example.invalid', 443), ('203.0.113.1', 443), ('127.0.0.1', 11434)):
            try:
                socket.create_connection((host, port), timeout=.1)
            except PermissionError:
                continue
            raise AssertionError('Offline network fence did not reject its negative probe')
        command('start')
        from alfred_native import configure, read_state
        configure(data)
        from django.conf import settings
        from django.contrib.sessions.models import Session
        from django.core.cache import cache
        from django.db import connections
        from apps.mobility.models import TravelPlanningSession, TravelProviderRequest, TravelResearchSession
        from apps.mobility.services.travel_conversation import save_plan
        from alfred_ai.native_tasks import native_runtime_probe, native_travel_reminders
        from tests import test_travel_affordability as finance
        from tests.test_travel_financial_reconciliation import TravelFinancialReconciliationTests
        from tests.test_travel_ics_export import parse_calendar
        from tests.test_user_data_browser import UserDataBrowserTests as UI
        from tests.user_acceptance_scenario import PASSWORD
        import requests
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import StaleElementReferenceException

        state = read_state(data)
        base = 'http://127.0.0.1:' + str(state['port'])
        client = requests.Session(); client.trust_env = False
        assert client.get(base + '/health/native/', timeout=15).status_code == 200
        assert Path(settings.DATABASES['default']['NAME']).resolve() == data / 'db.sqlite3'
        worker = native_runtime_probe('native-travel-' + uuid4().hex).get(blocking=True, timeout=30)
        assert worker['worker_pid'] != os.getpid()
        guarded = {json.loads(path.read_text().splitlines()[0])['pid']: json.loads(path.read_text().splitlines()[0])
                   for path in (folder / 'network-guard').glob('network-*.jsonl')}
        assert worker['worker_pid'] in guarded and state['pid'] in guarded
        # Windows venv launchers can retain a wrapper PID around the interpreter.
        assert state['worker_pid'] in (worker['worker_pid'], guarded[worker['worker_pid']]['parent_pid'])
        passed('native_loopback_waitress_sqlite_huey_and_child_fences', dict(worker_pid=worker['worker_pid']))

        class Probe(unittest.TestCase):
            memory_click = UI.memory_click
            text = UI.text
            login = UI.login
            travel_editor_fixture = UI.travel_editor_fixture
            affordability_fields = UI.affordability_fields
            savings_fields = UI.savings_fields
            reminder_fields = UI.reminder_fields

        probe = Probe()
        finance.TravelAffordabilityTests.setUp(probe)
        probe.user.city = 'Bengaluru'; probe.user.monthly_income = '3100'
        probe.user.set_password(PASSWORD); probe.user.save()
        probe.other.set_password(PASSWORD); probe.other.save()
        probe.scenario = {'user': probe.user}
        trip = probe.travel_editor_fixture(); save_plan(trip); trip.refresh_from_db()
        endpoint = f'/api/mobility/planner/sessions/{trip.pk}/'
        provider_before = (TravelProviderRequest.objects.count(), TravelResearchSession.objects.count())

        def money_snapshot():
            rows = TravelFinancialReconciliationTests.snapshot(probe)
            rows = {key: value for key, value in rows.items() if not key.startswith('mobility.')}
            for row in rows.get('users.User', []):
                row.pop('last_login', None)
            return rows

        before = money_snapshot()

        def post(path, body=None, files=None, form=False):
            if not client.cookies.get('csrftoken'):
                client.get(base + '/login/', timeout=15).raise_for_status()
            options = dict(data=body, files=files) if files or form else dict(json=body)
            return client.post(base + path, headers={'X-CSRFToken': client.cookies['csrftoken'],
                'Referer': base + path}, allow_redirects=False, timeout=45, **options)

        assert post('/login/', {'username': probe.user.username, 'password': PASSWORD}, form=True).status_code == 302
        upload = post('/api/ai/document-corpus/upload/', {'consent': 'true', 'days': '7'},
            files={'file': ('native-travel-private.txt', b'Synthetic private packing reference; not a booking.', 'text/plain')})
        assert upload.status_code == 200, 'Private synthetic document upload failed'
        options = webdriver.ChromeOptions()
        for argument in ('--headless=new', '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
                         '--window-size=1440,1200', '--disable-background-networking', '--disable-quic',
                         '--proxy-server=http://127.0.0.1:9', '--proxy-bypass-list=127.0.0.1;localhost;[::1]',
                         '--user-data-dir=' + str(private_directory(folder / 'chrome-profile'))):
            options.add_argument(argument)
        if env.get('CHROME_BINARY'):
            options.binary_location = env['CHROME_BINARY']
        browser = webdriver.Chrome(options=options)
        downloads = private_directory(folder / 'downloads')
        browser.execute_cdp_cmd('Browser.setDownloadBehavior', dict(behavior='allow', downloadPath=str(downloads)))
        browser.execute_cdp_cmd('Network.enable', {})
        browser.execute_cdp_cmd('Network.setBlockedURLs', {'urls': ['https://*']})
        probe.browser, probe.By, probe.wait = browser, By, WebDriverWait(browser, 25, ignored_exceptions=(StaleElementReferenceException,))
        probe.live_server_url, probe.artifacts = base, folder
        probe.login(probe.user.username)
        browser.get(base + '/mobility/?session=' + str(trip.pk))
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, '[data-editor-add]'))
        passed('saved_owned_trip_reopens_on_native_http_without_public_network_or_ollama')

        stage = 'model_unavailable'
        response = post('/api/ai/personal-insights/',
                        {'query': 'Suggest a quiet holiday activity.', 'scope': 'general'})
        assert response.status_code == 503 and response.json()['code'] == 'local_model_unavailable'
        assert response.json()['error_id'] and 'native_travel_probe_network_denied' not in response.text
        browser.get(base + '/ai/insights/')
        probe.wait.until(lambda _: probe.text('intelligenceLocalStatus') == 'Ollama unavailable')
        draft = browser.find_element(By.ID, 'intelligenceQuery')
        draft.send_keys('Suggest a quiet holiday activity.', Keys.CONTROL, Keys.ENTER)
        probe.wait.until(lambda _: 'Reference:' in probe.text('intelligenceFeedback'))
        assert browser.find_element(By.ID, 'intelligenceRetry').is_displayed()
        assert draft.get_attribute('value') == 'Suggest a quiet holiday activity.'
        assert probe.text('intelligenceCloudStatus') == 'OpenAI disabled'
        assert not browser.find_elements(By.CSS_SELECTOR, '#intelligenceAnswers article')
        browser.save_screenshot(str(folder / 'model-unavailable.png'))
        browser.get(base + '/mobility/?session=' + str(trip.pk))
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, '[data-editor-add]'))
        passed('blocked_local_model_safe_503_and_browser_draft_retry_without_cloud')

        stage = 'packing_and_reminders'
        browser.find_element(By.CSS_SELECTOR, '[data-packing-add] input').send_keys('Native offline gloves', Keys.ENTER)
        probe.wait.until(lambda _: 'Native offline gloves' in probe.text('plannerPacking'))
        trip.plan.refresh_from_db()
        item = next(row for row in trip.plan.planning_state['_packing_checklist']['items'] if row['label'] == 'Native offline gloves')
        probe.memory_click('[data-packing-toggle="' + item['id'] + '"]')
        probe.wait.until(lambda _: '1 of' in probe.text('packingStatus'))
        assert not browser.find_element(By.CSS_SELECTOR, '[data-reminder-consent]').is_selected()
        browser.find_element(By.CSS_SELECTOR, '[data-reminder-consent]').send_keys(Keys.SPACE)
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, '[data-reminder-form="create"]'))
        due = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=2)
        probe.reminder_fields('[data-reminder-form="create"]', 'Native offline pack', 'UTC', due.strftime('%Y-%m-%dT%H:%M'))
        probe.memory_click('[data-reminder-form="create"] button')
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, '[data-reminder-id]'))
        passed('packing_and_explicit_opt_in_reminder_scheduled')

        stage = 'private_original'
        probe.memory_click('[data-trip-document-list]')
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, '[data-trip-document-link]'))
        probe.memory_click('[data-trip-document-link]')
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, '#plannerDocuments a[href*="/original/"]'))
        original = browser.find_element(By.CSS_SELECTOR, '#plannerDocuments a[href*="/original/"]').get_attribute('href')
        probe.memory_click('#plannerDocuments a[href*="/original/"]')
        probe.wait.until(lambda _: (downloads / 'native-travel-private.txt').is_file())
        assert (downloads / 'native-travel-private.txt').read_bytes() == b'Synthetic private packing reference; not a booking.'
        passed('private_dpapi_original_link_and_owner_download')

        stage = 'editor'
        # Return explicitly after the original's new-tab download/privacy revalidation.
        browser.get(base + '/mobility/?session=' + str(trip.pk))
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, '[data-editor-add]'))
        probe.memory_click('[data-day="1"] details:has([data-editor-add]) > summary')
        probe.wait.until(lambda _: browser.find_element(By.CSS_SELECTOR, '[data-day="1"] [data-editor-add] input').is_displayed())
        browser.find_element(By.CSS_SELECTOR, '[data-day="1"] [data-editor-add] input').send_keys('Native offline activity', Keys.ENTER)
        probe.wait.until(lambda _: 'Native offline activity' in probe.text('plannerItinerary'))
        trip.refresh_from_db(); activity = trip.itinerary['days'][0]['items'][-1]
        selector = '[data-editor-item="' + activity['id'] + '"]'
        probe.memory_click(selector + ' [data-editor-remove]')
        probe.wait.until(lambda _: not browser.find_elements(By.CSS_SELECTOR, selector))
        probe.memory_click('[data-editor-undo]')
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, selector))
        probe.memory_click('#plannerSave')
        probe.wait.until(lambda _: 'Travel Plan saved' in probe.text('plannerAlert'))
        browser.refresh()
        probe.wait.until(lambda _: 'Native offline gloves' in probe.text('plannerPacking'))
        assert browser.find_elements(By.CSS_SELECTOR, selector)
        assert browser.find_elements(By.CSS_SELECTOR, '#plannerDocuments a[href*="/original/"]')
        passed('editor_undo_save_reopen_preserves_packing_documents_and_reminders')

        stage = 'exports_offline_retry'
        probe.memory_click('#plannerPrepareICS')
        probe.wait.until(lambda _: browser.find_elements(By.CSS_SELECTOR, '[data-calendar-event]'))
        browser.execute_cdp_cmd('Network.emulateNetworkConditions', dict(offline=True, latency=0, downloadThroughput=-1, uploadThroughput=-1))
        probe.memory_click('#plannerExportPDF')
        probe.wait.until(lambda _: probe.text('plannerAlert') and browser.find_element(By.ID, 'plannerExportPDF').is_enabled())
        assert not (downloads / 'alfred-itinerary.pdf').exists()
        browser.execute_cdp_cmd('Network.emulateNetworkConditions', dict(offline=False, latency=0, downloadThroughput=-1, uploadThroughput=-1))
        for kind in ('PDF', 'GPX', 'ICS'):
            probe.memory_click('#plannerExport' + kind)
            probe.wait.until(lambda _: (downloads / ('alfred-itinerary.' + kind.lower())).is_file() and not list(downloads.glob('*.crdownload')))
        from lxml import etree
        from pypdf import PdfReader
        pdf = '\n'.join(page.extract_text() for page in PdfReader(downloads / 'alfred-itinerary.pdf', strict=True).pages)
        xml = etree.parse(str(downloads / 'alfred-itinerary.gpx'), etree.XMLParser(resolve_entities=False, no_network=True))
        calendar = parse_calendar((downloads / 'alfred-itinerary.ics').read_bytes())
        trip.plan.refresh_from_db(); names = [stop['name'] for stop in trip.plan.itinerary['stops']]
        assert ' → '.join(names) in pdf and xml.xpath('//*[local-name()="wpt"]/*[local-name()="name"]/text()') == names
        assert not xml.xpath('//*[local-name()="rte" or local-name()="trk"]')
        assert calendar['roundtrip'] and calendar['events'][0]['location'] == ' → '.join(names)
        passed('pdf_gpx_ics_native_download_independent_parsers_and_offline_retry')

        stage = 'financial_scenarios'
        # Preserve real quotas: allow the actual rolling window after the dense UI actions.
        time.sleep(settings.ALFRED_API_ACCOUNT_WINDOW_SECONDS)
        probe.memory_click('#plannerAffordabilityDetails summary')
        probe.wait.until(lambda _: browser.find_elements(By.ID, 'plannerAffordabilityForm'))

        probe.affordability_fields()
        currency = browser.find_element(By.ID, 'affordCurrency'); currency.clear(); currency.send_keys('INR')
        probe.memory_click('#plannerAffordabilityForm [name="verified"]')
        probe.memory_click('#plannerAffordabilityForm button')
        probe.wait.until(lambda _: 'Affordable · scenario only' in probe.text('plannerAffordabilityResult'))
        probe.savings_fields()
        currency = browser.find_element(By.ID, 'affordCurrency'); currency.clear(); currency.send_keys('INR')
        probe.memory_click('#plannerAffordabilityForm [name="verified"]')
        probe.memory_click('#plannerAffordabilityForm [name="future_confirmed"]')
        probe.memory_click('#plannerAffordabilityForm button')
        probe.wait.until(lambda _: 'Future savings · projected estimates only' in probe.text('plannerAffordabilityResult'))
        assert money_snapshot() == before, 'Read-only scenarios changed canonical financial records'
        passed('current_and_future_explicit_same_currency_scenarios_no_financial_writes')

        stage = 'durable_reminder_delivery'
        wait_due = max(0, (due - datetime.now(timezone.utc)).total_seconds())
        assert wait_due < 125
        while datetime.now(timezone.utc) < due:
            time.sleep(min(1, max(0, (due - datetime.now(timezone.utc)).total_seconds())))
        from apps.mobility.services.travel.reminders import KEY as REMINDER_KEY
        deadline = time.monotonic() + 75
        while True:
            trip.plan.refresh_from_db()
            if trip.plan.planning_state[REMINDER_KEY]['deliveries']:
                break
            assert time.monotonic() < deadline, 'Native scheduler did not deliver the due reminder'
            time.sleep(1)
        from huey.contrib.djhuey import HUEY
        # Huey deliberately omits result-store entries for periodic tasks.
        for _ in range(2):
            queued = native_travel_reminders()
            deadline = time.monotonic() + 30
            while True:
                rows = HUEY.storage.sql('SELECT outcome, summary FROM native_history WHERE queue=? AND task_id=?',
                                       (HUEY.storage.name, queued.id), results=True)
                if rows:
                    assert rows[0][0] == 'complete' and json.loads(rows[0][1])['refreshed'] == 0
                    break
                assert time.monotonic() < deadline, 'Native worker did not acknowledge duplicate reminder sweep'
                time.sleep(.2)
        browser.refresh()
        probe.wait.until(lambda _: 'Delivered late' in probe.text('plannerReminders'))
        assert len(browser.find_elements(By.CSS_SELECTOR, '[data-reminder-delivery]')) == 1
        heartbeat = cache.get('native:scheduler-heartbeat')
        assert heartbeat and heartbeat['instance'] == state['instance']
        passed('actual_durable_worker_due_delivery_deduplication_and_scheduler')

        stage = 'owner_and_session_isolation'
        stranger = requests.Session(); stranger.trust_env = False
        stranger.get(base + '/login/', timeout=15).raise_for_status()
        assert stranger.post(base + '/login/', data={'username': probe.other.username, 'password': PASSWORD},
            headers={'X-CSRFToken': stranger.cookies['csrftoken']}, allow_redirects=False, timeout=15).status_code == 302
        assert stranger.get(base + endpoint, timeout=15).status_code == 404
        assert stranger.get(original, timeout=15).status_code == 404
        assert client.post(base + endpoint, json={'action': 'save'}, timeout=15).status_code == 403
        assert provider_before == (TravelProviderRequest.objects.count(), TravelResearchSession.objects.count())
        cookie = browser.get_cookie(settings.SESSION_COOKIE_NAME)
        Session.objects.filter(session_key=cookie['value']).delete()
        browser.delete_cookie(settings.SESSION_COOKIE_NAME)
        probe.memory_click('[data-packing-reload]')
        probe.wait.until(lambda _: not browser.find_element(By.ID, 'plannerPacking').is_displayed())
        assert probe.text('plannerDocuments') == ''
        assert money_snapshot() == before, 'Travel flow changed canonical financial records'
        passed('owner_session_csrf_no_provider_transmission_and_financial_invariants')
        report['downloads'] = {path.name: sha256(path.read_bytes()).hexdigest() for path in downloads.iterdir() if path.is_file()}
        report['journey_passed'] = True
    except Exception as error:
        report['failure'] = dict(stage=stage, exception_type=type(error).__name__)
        if browser:
            browser.save_screenshot(str(folder / 'failure.png'))
            (folder / 'failure.html').write_text(browser.page_source, encoding='utf-8')
        raise
    finally:
        cleanup_ok = False
        try:
            try:
                if browser:
                    browser.quit()
            finally:
                if probe:
                    assert probe.doCleanups(), 'Probe fixture cleanup failed'
            cleanup_ok = True
        finally:
            try:
                command('stop')
                from alfred_native import read_state, InstanceLock
                stopped = read_state(data)
                assert stopped.get('status') == 'stopped'
                with InstanceLock(data), InstanceLock(data, 'worker.lock'):
                    pass
                report['checks']['owned_native_processes_stopped'] = True
                if 'connections' in locals():
                    connections.close_all()
                report['passed'] = bool(report.get('journey_passed')) and cleanup_ok
            finally:
                save()
                print('Report: ' + str(report_path), flush=True)


if __name__ == '__main__':
    main()
