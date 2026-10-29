"""Pinned source scanning and runner isolation; all data and repositories are synthetic."""
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import release_gate as release
from scripts import release_validation as validation
from tests.test_release_gate import ReleaseRepositoryFixture


class ReleasePrivacyTests(ReleaseRepositoryFixture, unittest.TestCase):
    def test_complete_history_is_scanned_in_deterministic_bounded_batches(self):
        self.commit('first.txt', 'x' * 400)
        self.commit('second.txt', 'y' * 400)
        self.manifest['candidate_sha'] = self.git('rev-parse', 'HEAD')
        actual_run = validation.subprocess.run
        batches = []

        def run(command, **kwargs):
            result = actual_run(command, **kwargs)
            if command[-2:] == ['cat-file', '--batch']:
                batches.append((kwargs['input'].decode().splitlines(), len(result.stdout)))
            return result

        with patch.object(validation, 'SOURCE_SCAN_BATCH_BYTES', 512), \
             patch.object(validation, 'SOURCE_SCAN_TOTAL_BYTES', 2048), \
             patch.object(validation.subprocess, 'run', side_effect=run):
            result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result['status'], 'PASS')
        self.assertGreater(len(batches), 1)
        oids = [oid for batch, _ in batches for oid in batch]
        self.assertEqual(oids, sorted(set(oids)))
        self.assertTrue(all(size <= 512 for _, size in batches))
        self.assertGreater(result['evidence']['scanned_bytes'], 512)

    def test_last_batch_and_removed_history_credentials_still_fail(self):
        import hashlib

        self.commit('padding.txt', 'x' * 400)
        largest = max(line.split()[2] for line in self.git('ls-tree', '-r', 'HEAD').splitlines())
        secret = 'sk-proj-' + 'a' * 40
        for number in range(256):
            text = f'# synthetic {number} credential={secret!r}'
            raw = text.encode()
            oid = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
            if oid > largest:
                break
        else:
            self.fail('Synthetic last-batch fixture unavailable')
        self.commit('credential.txt', text)
        actual_run = validation.subprocess.run
        requests = []

        def run(command, **kwargs):
            if command[-2:] == ['cat-file', '--batch']:
                requests.append(kwargs['input'].decode().splitlines())
            return actual_run(command, **kwargs)

        with patch.object(validation, 'SOURCE_SCAN_BATCH_BYTES', 512), \
             patch.object(validation.subprocess, 'run', side_effect=run):
            self.manifest['candidate_sha'] = self.git('rev-parse', 'HEAD')
            result = validation.privacy(self.repo, self.manifest)
            self.assertEqual(requests[-1][-1], oid)
            self.assertGreater(len(requests), 1)
            self.assertEqual(result['status'], 'FAIL')
            self.assertNotIn(secret, json.dumps(result))
            self.commit('credential.txt', '# removed synthetic credential')
            self.manifest['candidate_sha'] = self.git('rev-parse', 'HEAD')
            self.assertEqual(validation.privacy(self.repo, self.manifest)['status'], 'FAIL')

    def test_historical_alias_prevents_fixture_exemption_across_batches(self):
        text = (Path(__file__).parent / 'memory_s3_fixture.py').read_text(encoding='utf-8')
        self.commit('tests/memory_s3_fixture.py', text)
        self.commit('shadow.py', text)
        self.commit('shadow.py', '# removed alias')
        self.commit('padding.txt', 'x' * len(text))
        self.manifest['candidate_sha'] = self.git('rev-parse', 'HEAD')
        with patch.object(validation, 'SOURCE_SCAN_BATCH_BYTES', len(text.encode()) + 200):
            result = validation.privacy(self.repo, self.manifest)
        self.assertGreater(result['evidence']['batches'], 1)
        self.assertEqual(result['status'], 'FAIL')

    def test_malformed_batch_output_never_retains_a_prior_pass(self):
        actual_run = validation.subprocess.run
        for mutation in ('oid', 'type', 'size', 'extra_field', 'truncated', 'delimiter', 'trailing'):
            def run(command, **kwargs):
                result = actual_run(command, **kwargs)
                if command[-2:] != ['cat-file', '--batch']:
                    return result
                header, body = result.stdout.split(b'\n', 1)
                fields = header.split()
                if mutation == 'oid': fields[0] = b'0' * 40
                if mutation == 'type': fields[1] = b'tree'
                if mutation == 'size': fields[2] = str(int(fields[2]) + 1).encode()
                if mutation == 'extra_field': fields.append(b'extra')
                result.stdout = b' '.join(fields) + b'\n' + body
                if mutation == 'truncated': result.stdout = result.stdout[:-2]
                if mutation == 'delimiter': result.stdout = result.stdout[:-1] + b'x'
                if mutation == 'trailing': result.stdout += b'unexpected'
                return result

            with self.subTest(mutation=mutation), patch.object(validation.subprocess, 'run', side_effect=run):
                release.gate(self.manifest, 'privacy', 'PASS', 'synthetic_old_scan')
                with self.assertRaisesRegex(release.GateError, 'source_blob_identity_mismatch'):
                    validation.privacy(self.repo, self.manifest)
                self.assertEqual(self.manifest['gates']['privacy']['status'], 'NOT_RUN')

    def test_later_batch_timeout_or_failure_does_not_report_success(self):
        self.commit('padding.txt', 'x' * 400)
        self.manifest['candidate_sha'] = self.git('rev-parse', 'HEAD')
        actual_run = validation.subprocess.run
        for timeout in (False, True):
            batches = []

            def run(command, **kwargs):
                if command[-2:] == ['cat-file', '--batch']:
                    batches.append(kwargs['timeout'])
                    if len(batches) == 2:
                        if timeout:
                            raise subprocess.TimeoutExpired('git', 1, output=b'synthetic-private-content')
                        return subprocess.CompletedProcess(command, 1, b'synthetic-private-content', b'')
                return actual_run(command, **kwargs)

            with self.subTest(timeout=timeout), patch.object(validation, 'SOURCE_SCAN_BATCH_BYTES', 512), \
                 patch.object(validation.subprocess, 'run', side_effect=run):
                with self.assertRaisesRegex(release.GateError, '^source_blob_scan_failed$') as failure:
                    validation.privacy(self.repo, self.manifest)
                self.assertEqual(len(batches), 2)
                self.assertLess(batches[1], batches[0])
                self.assertNotIn('synthetic-private-content', str(failure.exception) + json.dumps(self.manifest))
                self.assertEqual(self.manifest['gates']['privacy']['status'], 'NOT_RUN')

    def test_total_work_cap_rejects_before_reading_bodies(self):
        actual_run = validation.subprocess.run
        bodies = []

        def run(command, **kwargs):
            if command[-2:] == ['cat-file', '--batch']:
                bodies.append(command)
            return actual_run(command, **kwargs)

        with patch.object(validation, 'SOURCE_SCAN_TOTAL_BYTES', 1), \
             patch.object(validation.subprocess, 'run', side_effect=run):
            with self.assertRaisesRegex(release.GateError, 'source_scan_object_budget'):
                validation.privacy(self.repo, self.manifest)
        self.assertEqual(bodies, [])

    def test_scan_expiring_after_last_response_cannot_pass(self):
        clock, scanned = [0], []

        def scan(content):
            scanned.append(content)
            if len(scanned) == 2:
                clock[0] = 121
            return iter(())

        with patch.object(validation.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(validation, 'SECRET') as pattern:
            pattern.finditer.side_effect = scan
            with self.assertRaisesRegex(release.GateError, '^source_blob_scan_failed$'):
                validation.privacy(self.repo, self.manifest)
        self.assertEqual(len(scanned), 2)
        self.assertEqual(self.manifest['gates']['privacy']['status'], 'NOT_RUN')

    def test_exact_batch_frame_boundary_is_enforced(self):
        entries = [entry.split() for entry in self.git('ls-tree', '-r', '-l', 'HEAD').splitlines()]
        framed = sum(int(row[3]) + len(f'{row[2]} blob {row[3]}\n'.encode()) + 1 for row in entries)
        for limit, expected in ((framed, 1), (framed - 1, 2)):
            with self.subTest(limit=limit), patch.object(validation, 'SOURCE_SCAN_BATCH_BYTES', limit):
                result = validation.privacy(self.repo, self.manifest)
                self.assertEqual(result['status'], 'PASS')
                self.assertEqual(result['evidence']['batches'], expected)

    def test_commit_limit_is_checked_before_tree_traversal(self):
        actual_git = release.git
        trees = []

        def git(repo, *args):
            if args[0] == 'rev-list': return '\n'.join([self.candidate] * 1001)
            if args[0] == 'ls-tree': trees.append(args)
            return actual_git(repo, *args)

        with patch.object(release, 'git', side_effect=git):
            with self.assertRaisesRegex(release.GateError, 'source_scan_object_budget'):
                validation.privacy(self.repo, self.manifest)
        self.assertEqual(trees, [])

    def test_object_limit_and_oversized_blob_fail_before_body_reads(self):
        actual_git = release.git
        for count, size in ((10001, 1), (1, 16 * 1024 * 1024 + 1)):
            def git(repo, *args):
                if args[0] == 'ls-tree':
                    return ''.join(f'100644 blob {i:040x} {size}\tfile{i}.txt\0' for i in range(count))
                return actual_git(repo, *args)

            with self.subTest(count=count), patch.object(release, 'git', side_effect=git), \
                 patch.object(validation.subprocess, 'run', wraps=validation.subprocess.run) as run:
                if count > 10000:
                    with self.assertRaisesRegex(release.GateError, 'source_scan_object_budget'):
                        validation.privacy(self.repo, self.manifest)
                else:
                    self.assertEqual(validation.privacy(self.repo, self.manifest)['status'], 'FAIL')
                self.assertFalse(any(call.args[0][-2:] == ['cat-file', '--batch'] for call in run.call_args_list))

    def test_quoted_json_access_and_refresh_tokens_fail_without_disclosing_values(self):
        for name in ("access_token", "refresh_token", "client_secret", "api_key"):
            value = "synthetic-credential-" + "x" * 40
            self.commit("provider-profile.json", json.dumps({name: value}))
            self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
            result = validation.privacy(self.repo, self.manifest)
            self.assertEqual(result["status"], "FAIL", name)
            self.assertNotIn(value, json.dumps(result))
            self.assertNotIn(value, json.dumps(self.manifest))
    def test_clean_source_passes_without_loading_runtime_configuration(self):
        result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["evidence"]["history_commits"], 1)

    def test_private_database_and_memory_payload_paths_are_blocked(self):
        self.commit("artifacts/private-memory-v2/index.sqlite3", "synthetic private memory")
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        release.source_checks(self.repo, self.manifest)
        result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn("synthetic private memory", json.dumps(result))
        self.assertNotIn("index.sqlite3", json.dumps(result))
        self.assertNotIn("index.sqlite3", json.dumps(self.manifest))

    def test_secret_removed_in_later_commit_still_blocks_history_push(self):
        secret = "sk-proj-" + "a" * 40
        self.commit("settings.py", "credential = '" + secret + "'")
        self.commit("settings.py", "# removed synthetic credential")
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn(secret, json.dumps(result))

    def test_test_filename_is_not_a_blanket_credential_exemption(self):
        self.commit("tests/memory_s3_fixture.py", "token='" + "sk-proj-" + "b" * 40 + "'")
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        self.assertEqual(validation.privacy(self.repo, self.manifest)["status"], "FAIL")

    def test_exact_public_examples_are_classified_without_a_blanket_test_exemption(self):
        for name in ("memory_s3_fixture.py", "test_memory_reasoning.py"):
            self.commit("tests/" + name, (Path(__file__).parent / name).read_text(encoding="utf-8"))
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        result = validation.privacy(self.repo, self.manifest)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["evidence"]["reviewed_synthetic_identifiers"], 3)

    def test_profile_environment_and_logs_never_include_operator_secrets(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-secret", "AWS_SECRET_ACCESS_KEY": "synthetic-secret",
                    "ALFRED_DATA_DIR": "synthetic-production", "ALFRED_MEMORY_CLOUD_AUTHORIZED": "true"}):
            env = validation.environment(self.root / "sandbox")
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
        self.assertEqual(env["ALFRED_MEMORY_CLOUD_AUTHORIZED"], "false")
        self.assertEqual(env["ALFRED_MEMORY_OPENAI_AUTHORIZED"], "false")
        self.assertEqual(env["ALFRED_MEMORY_SYNC_PROVIDER"], "")
        self.assertEqual(env["ALFRED_MEMORY_SYNC_MOCK_DIR"], "")
        self.assertEqual(env["ALFRED_MEDIA_ROOT"], str(self.root / "sandbox/media"))
        self.assertNotIn("synthetic-production", json.dumps(env))
        raw = "FAIL: test_example (tests.synthetic.Case)\nC:\\private\\account.pdf amount=123456\nOCR synthetic-secret\nRan 2 tests in 1.2s\nFAILED (failures=1)"
        safe = validation.safe_log(raw)
        self.assertIn("test_example", safe)
        self.assertIn("Ran 2 tests", safe)
        self.assertNotIn("account.pdf", safe)
        self.assertNotIn("123456", safe)
        self.assertNotIn("synthetic-secret", safe)

    def test_runner_counts_and_timeout_are_explicit(self):
        completed = subprocess.CompletedProcess([], 1, "Ran 3 tests in 1.2s\nFAILED (failures=1)", "synthetic-secret")
        with patch.object(validation.subprocess, "run", return_value=completed):
            result = validation.run(self.repo, ["unused"], {}, self.root, "test", 1)
        self.assertEqual((result["status"], result["tests"]), ("FAIL", 3))
        self.assertNotIn("synthetic-secret", (self.root / "test.log").read_text())
        with patch.object(validation.subprocess, "run", side_effect=subprocess.TimeoutExpired("unused", 1)):
            result = validation.run(self.repo, ["unused"], {}, self.root, "timeout", 1)
        self.assertEqual(result["code"], "suite_timeout")

    def test_failure_headers_retain_setup_and_subtest_ids_without_parameter_values(self):
        raw = ("ERROR: setUpClass (tests.synthetic.Case)\n"
               "FAIL: test_owner (tests.synthetic.Case.test_owner) (document='private-account.pdf')\n"
               "Traceback secret-value /private/statement.pdf\n")
        safe = validation.safe_log(raw)
        self.assertIn("ERROR: setUpClass (tests.synthetic.Case)", safe)
        self.assertIn("FAIL: test_owner (tests.synthetic.Case.test_owner)", safe)
        self.assertNotIn("private-account", safe)
        self.assertNotIn("secret-value", safe)
        self.assertNotIn("statement.pdf", safe)

    def test_slowest_timings_retain_only_test_ids_and_numeric_durations(self):
        raw = ("Slowest test durations\n"
               "12.345s    test_owner (tests.synthetic.Case.test_owner)\n"
               "1.234s test_private (tests.synthetic.Case) (document='private-account.pdf')\n"
               "2.345s /private/statement.pdf amount=123456\n")
        safe = validation.safe_log(raw)
        self.assertIn('12.345s    test_owner (tests.synthetic.Case.test_owner)', safe)
        self.assertNotIn('private-account', safe)
        self.assertNotIn('statement.pdf', safe)
        self.assertNotIn('123456', safe)

    def test_targeted_tests_do_not_satisfy_full_backend_gate(self):
        result = {"status": "PASS", "code": "suite_exit", "tests": 3, "skips": 0,
                  "log": "synthetic.log", "log_sha256": "a" * 64}
        with patch.object(validation, "run", return_value=result):
            validation.validate(self.repo, self.manifest, self.root / "output", "targeted", ["tests.synthetic"])
        self.assertEqual(self.manifest["gates"]["backend"]["status"], "NOT_RUN")
        self.assertEqual(self.manifest["targeted_runs"][-1]["tests"], 3)

    def test_failed_gate_can_be_explicitly_rerun_without_losing_prior_result(self):
        release.gate(self.manifest, "backend", "FAIL", "synthetic_prior_failure")
        result = {"status": "PASS", "code": "suite_exit", "tests": 3, "skips": 0,
                  "log": "synthetic.log", "log_sha256": "a" * 64}
        with patch.object(validation, "run", return_value=result):
            validation.validate(self.repo, self.manifest, self.root / "retry", "backend")
        self.assertEqual(self.manifest["gates"]["backend"]["status"], "PASS")
        self.assertEqual(self.manifest["validation_history"][-1]["previous"]["backend"]["status"], "FAIL")

    def test_skipped_or_zero_backend_tests_do_not_pass(self):
        for count, skips in ((0, 0), (3, 1)):
            result = {"status": "PASS", "code": "suite_exit", "tests": count, "skips": skips,
                      "log": "synthetic.log", "log_sha256": "a" * 64}
            with self.subTest(count=count, skips=skips), patch.object(validation, "run", return_value=result):
                validation.validate(self.repo, self.manifest, self.root / ("run-" + str(count)), "backend")
                self.assertEqual(self.manifest["gates"]["backend"]["status"], "NOT_RUN")
                self.assertEqual(release.decision(self.manifest, ["backend"])["status"], "BLOCKED")
                self.manifest = release.new_manifest("synthetic-1", self.candidate, self.baseline)

    def test_failed_backend_stops_full_gate_before_expensive_browser_or_native_runs(self):
        passed={"status":"PASS","code":"suite_exit","tests":0,"skips":0,
                "log":"synthetic.log","log_sha256":"a"*64}
        failed=passed|{"status":"FAIL","tests":1}
        with patch.object(validation,"run",side_effect=[passed,passed,failed]) as run:
            validation.validate(self.repo,self.manifest,self.root/'fail-fast','full',with_ollama=True)
        self.assertEqual(run.call_count,3)
        self.assertEqual(self.manifest['gates']['backend']['status'],'FAIL')
        self.assertEqual(self.manifest['gates']['browser']['status'],'NOT_RUN')
        self.assertEqual(self.manifest['gates']['native']['status'],'NOT_RUN')

    def test_absent_package_is_not_run_instead_of_pass(self):
        validation.packaged(self.repo, self.manifest, self.root, {}, None, None)
        self.assertEqual(self.manifest["gates"]["packaged"]["status"], "NOT_RUN")

    def test_packaged_source_and_executable_identity_are_required_before_execution(self):
        manifest = self.root / "package.json"
        manifest.write_text(json.dumps({"source_commit": self.baseline, "source_dirty": False}))
        with self.assertRaisesRegex(release.GateError, "packaged_source_identity_mismatch"):
            validation.packaged(self.repo, self.manifest, self.root, {}, self.root, manifest)
        (self.root / "ALFRED.exe").write_bytes(b"synthetic executable")
        manifest.write_text(json.dumps({"source_commit": self.candidate, "source_dirty": False, "artifacts": {}}))
        with self.assertRaisesRegex(release.GateError, "packaged_executable_hash_mismatch"):
            validation.packaged(self.repo, self.manifest, self.root, {}, self.root, manifest)


if __name__ == "__main__":
    unittest.main()
