"""Signing pipeline tests. They use only the standard library, so no Django or runtime data is involved.

Fail-closed rules run with injected signature results. Set ALFRED_SIGNING_E2E=1 on
Windows to also use real Authenticode with a throwaway untrusted test certificate.
"""
import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts import package_windows_release as package
from scripts import windows_signing as signing


PUBLISHER = "CN=Synthetic Publisher, O=Synthetic Publisher, C=IN"
THUMBPRINT = "A" * 40
TIMESTAMP_URL = "http://timestamp.example.test/rfc3161"


def tiny_pe(extra=b""):
    """A minimal valid x64 PE, so no real binary is needed."""
    dos = b"MZ" + b"\0" * 58 + struct.pack("<I", 64)
    coff = struct.pack("<HHIIIHH", 0x8664, 1, 0, 0, 0, 240, 0x22)
    optional = struct.pack("<HBBIIIII", 0x20B, 14, 0, 512, 0, 0, 0x1000, 0x1000)
    optional += struct.pack("<QIIHHHHHHIIIIHHQQQQII", 0x140000000, 0x1000, 512, 6, 0, 0, 0, 6, 0, 0,
                            0x2000, 512, 0, 3, 0x8160, 0x100000, 0x1000, 0x100000, 0x1000, 0, 16)
    optional += b"\0" * 128
    section = struct.pack("<8sIIIIIIHHI", b".text", 512, 0x1000, 512, 512, 0, 0, 0, 0, 0x60000020)
    headers = dos + b"PE\0\0" + coff + optional + section
    return headers.ljust(512, b"\0") + (b"\xc3" + extra).ljust(512, b"\0")


def signed_record(**overrides):
    return {"status": "Valid", "type": "Authenticode", "subject": PUBLISHER, "issuer": "CN=Public CA",
            "thumbprint": THUMBPRINT, "not_after": "2030-01-01T00:00:00+00:00",
            "ekus": [signing.CODE_SIGNING_EKU], "timestamp_subject": "CN=Public TSA", **overrides}


VENDOR = signed_record(subject="CN=Vendor", thumbprint="B" * 40)
UNSIGNED = {"status": "NotSigned", "type": "None", "subject": None, "ekus": [], "timestamp_subject": None}
SIGNTOOL_OK = ("Hash of file (sha256): ABCD\nThe signature is timestamped: Mon Nov  2 10:00:00 2026\n"
               "Successfully verified: file\n")


class SigningCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.work = Path(directory.name)
        self.signtool = self.work / "signtool.exe"
        self.signtool.write_bytes(tiny_pe())
        self.bundle = self.work / "bundle"
        (self.bundle / "_internal").mkdir(parents=True)
        for name in signing.OWNED:
            (self.bundle / name).write_bytes(tiny_pe())
        (self.bundle / "Start ALFRED.cmd").write_text("@echo off\n", encoding="ascii")
        self.status = {}
        patcher = mock.patch.object(signing, "inspect_signatures", side_effect=self.fake_inspect)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_inspect(self, paths):
        rows = {}
        for path in paths:
            relative = Path(path).relative_to(self.bundle).as_posix() if Path(path).is_relative_to(self.bundle) else Path(path).name
            rows[str(path)] = {"path": str(path), **self.status.get(relative, UNSIGNED)}
        return rows

    def config(self, **overrides):
        return {"schema": 1, "provider": "certificate_store", "publisher_subject": PUBLISHER,
                "certificate_sha1": THUMBPRINT, "timestamp_url": TIMESTAMP_URL,
                "signtool": str(self.signtool), **overrides}

    def config_file(self, **overrides):
        path = self.work / "signing-config.json"
        path.write_text(json.dumps(self.config(**overrides)), encoding="utf-8")
        return path

    def all_signed(self):
        for row in signing.scan_tree(self.bundle):
            if row["kind"] == "signable":
                self.status.setdefault(row["path"], signed_record())


class ConfigurationTests(SigningCase):
    def test_missing_configuration_is_refused_without_fallback(self):
        with self.assertRaisesRegex(signing.SigningError, "no unsigned fallback"):
            signing.load_config(None)
        with self.assertRaisesRegex(signing.SigningError, "missing"):
            signing.load_config(self.work / "absent.json")

    def test_secret_fields_are_refused_and_their_values_not_echoed(self):
        for key in ("password", "pfx", "token", "pin"):
            with self.assertRaises(signing.SigningError) as caught:
                signing.load_config(self.config_file(**{key: "super-secret-value"}))
            self.assertIn(key, str(caught.exception))
            self.assertNotIn("super-secret-value", str(caught.exception))

    def test_invalid_fields_are_refused(self):
        for overrides in ({"provider": "pfx_file"}, {"certificate_sha1": "abc"}, {"certificate_sha1": None},
                          {"publisher_subject": "Someone"}, {"timestamp_url": ""}, {"timestamp_url": "ftp://x.test"},
                          {"timestamp_url": "https://user:pw@x.test/"}, {"timestamp_url": "https://x.test/?key=abc"},
                          {"signtool": "signtool.exe"}, {"signtool": str(self.work / "other.exe")}, {"schema": 2},
                          {"dlib": str(self.signtool)}, {"provider": "remote_dlib"}):
            with self.subTest(overrides), self.assertRaises(signing.SigningError):
                signing.load_config(self.config_file(**overrides))

    def test_configuration_inside_the_repository_is_refused(self):
        with self.assertRaisesRegex(signing.SigningError, "outside the repository"):
            signing.load_config(signing.ROOT / "packaging" / "signing-config.json")

    def test_production_signing_needs_exact_authorization_and_refuses_ci(self):
        path = self.config_file()
        with mock.patch.dict(os.environ, {"CI": "", "GITHUB_ACTIONS": ""}):
            for authorization in (None, "HEAD", "0" * 39):
                with self.assertRaisesRegex(signing.SigningError, "exact source commit"):
                    signing.prepare_release(path, authorization, "0" * 40)
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with self.assertRaisesRegex(signing.SigningError, "refused in CI"):
                signing.prepare_release(path, "0" * 40, "0" * 40)

    def test_unsigned_or_foreign_signtool_is_refused(self):
        with mock.patch.dict(os.environ, {"CI": "", "GITHUB_ACTIONS": ""}):
            with self.assertRaisesRegex(signing.SigningError, "signed by Microsoft"):
                signing.prepare_release(self.config_file(), "0" * 40, "0" * 40)

    def test_invalid_certificate_is_refused_before_any_file_changes(self):
        self.status["signtool.exe"] = signed_record(subject="CN=Microsoft Corporation")
        with mock.patch.dict(os.environ, {"CI": "", "GITHUB_ACTIONS": ""}), \
                mock.patch.object(signing, "inspect_certificate", return_value={"thumbprint": THUMBPRINT, "subject": PUBLISHER, "issuer": PUBLISHER}):
            with self.assertRaisesRegex(signing.SigningError, "self-signed"):
                signing.prepare_release(self.config_file(), "0" * 40, "0" * 40)


class CertificateTests(SigningCase):
    def certificate(self, **overrides):
        now = datetime(2026, 11, 2, tzinfo=timezone.utc)
        return {"thumbprint": THUMBPRINT, "subject": PUBLISHER, "issuer": "CN=Public CA",
                "ekus": [signing.CODE_SIGNING_EKU], "has_private_key": True, "signature_algorithm": "sha384RSA",
                "not_before": (now - timedelta(days=1)).isoformat(), "not_after": (now + timedelta(days=1)).isoformat(),
                "chain_ok": True, "chain_status": [], "root_in_microsoft_store": True, **overrides}

    def problems(self, **overrides):
        return signing.certificate_problems(self.certificate(**overrides), self.config(), datetime(2026, 11, 2, tzinfo=timezone.utc))

    def test_valid_certificate_passes(self):
        self.assertEqual(self.problems(), [])

    def test_each_invalid_property_is_refused(self):
        cases = {"thumbprint": {"thumbprint": "C" * 40}, "subject differs": {"subject": "CN=Other"},
                 "self-signed": {"issuer": PUBLISHER}, "code-signing": {"ekus": ["1.3.6.1.5.5.7.3.1"]},
                 "private key": {"has_private_key": False}, "SHA-1": {"signature_algorithm": "sha1RSA"},
                 "validity": {"not_after": "2026-11-01T00:00:00+00:00"}, "chain failed": {"chain_ok": False},
                 "Microsoft-distributed": {"root_in_microsoft_store": False}}
        for expected, overrides in cases.items():
            with self.subTest(expected):
                self.assertTrue(any(expected in problem for problem in self.problems(**overrides)))


class CommandTests(SigningCase):
    def test_store_command_uses_sha256_rfc3161_and_explicit_identity(self):
        command = signing.sign_command(self.config(), "x.exe")
        for flag, value in (("/fd", "SHA256"), ("/td", "SHA256"), ("/tr", TIMESTAMP_URL), ("/sha1", THUMBPRINT)):
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertNotIn("/t", command)
        self.assertNotIn("/a", command)
        self.assertNotIn("/f", command)
        self.assertNotIn("/p", command)
        self.assertEqual(command[-1], "x.exe")

    def test_remote_command_uses_digest_library(self):
        command = signing.sign_command(self.config(provider="remote_dlib", dlib="d.dll", dmdf="m.json"), "x.exe")
        self.assertEqual(command[command.index("/dlib") + 1], "d.dll")
        self.assertNotIn("/sha1", command)

    def test_failed_signing_or_timestamp_fails_and_does_not_log_tool_output(self):
        failure = subprocess.CompletedProcess([], 1, "secret-output-line\n", "SignTool Error: The specified timestamp server could not be reached.\n")
        with mock.patch.object(signing.subprocess, "run", return_value=failure) as run, mock.patch.object(signing.time, "sleep"):
            with self.assertRaises(signing.SigningError) as caught:
                signing.sign_file(self.config(), self.bundle / "ALFRED.exe")
        self.assertEqual(run.call_count, 3)
        self.assertIn("timestamp server", str(caught.exception))
        self.assertNotIn("secret-output-line", str(caught.exception))

    def test_signed_without_timestamp_is_rejected(self):
        self.assertIn("signature has no timestamp", signing.signature_problems(signed_record(timestamp_subject=None), self.config()))
        result = subprocess.CompletedProcess([], 0, "Hash of file (sha256): AB\nSignTool Warning: Signature is not timestamped\n", "")
        with mock.patch.object(signing.subprocess, "run", return_value=result):
            problems, timestamp = signing.signtool_verification(str(self.signtool), "x.exe")
        self.assertIsNone(timestamp)
        self.assertIn("signtool found no timestamp", problems)

    def test_weak_file_digest_is_rejected(self):
        result = subprocess.CompletedProcess([], 0, "Hash of file (sha1): AB\nThe signature is timestamped: now\n", "")
        with mock.patch.object(signing.subprocess, "run", return_value=result):
            problems, _ = signing.signtool_verification(str(self.signtool), "x.exe")
        self.assertIn("file digest is not SHA-256", problems)

    def test_signature_identity_rules(self):
        cases = {"publisher does not match": {"subject": "CN=Other"}, "thumbprint does not match": {"thumbprint": "C" * 40},
                 "signature status is HashMismatch": {"status": "HashMismatch"},
                 "signature status is NotTimeValid": {"status": "NotTimeValid"},
                 "signature status is UnknownError": {"status": "UnknownError"},
                 "not embedded": {"type": "Catalog"}, "code-signing": {"ekus": []}}
        for expected, overrides in cases.items():
            with self.subTest(expected):
                problems = signing.signature_problems(signed_record(**overrides), self.config())
                self.assertTrue(any(expected in problem for problem in problems), problems)
        self.assertEqual(signing.signature_problems(signed_record(not_after="2020-01-01T00:00:00+00:00"), self.config()), [],
                         "an expired certificate stays acceptable while Windows reports its timestamped signature Valid")


class BundlePolicyTests(SigningCase):
    def sign(self, approve=False):
        with mock.patch.object(signing, "sign_file") as sign_file:
            try:
                plan = signing.sign_bundle(self.bundle, self.config(), approve)
            finally:
                self.signed = sorted(Path(call.args[1]).relative_to(self.bundle).as_posix() for call in sign_file.call_args_list)
        return {row["path"]: row for row in plan}

    def test_owned_are_signed_and_scripts_recorded_not_signed(self):
        plan = self.sign()
        self.assertEqual(self.signed, sorted(signing.OWNED))
        self.assertEqual(plan["Start ALFRED.cmd"]["role"], "recorded_unsignable")

    def test_vendor_signature_is_preserved_never_resigned(self):
        (self.bundle / "_internal/python312.dll").write_bytes(tiny_pe())
        self.status["_internal/python312.dll"] = VENDOR
        plan = self.sign()
        self.assertEqual(plan["_internal/python312.dll"]["role"], "vendor_preserved")
        self.assertNotIn("_internal/python312.dll", self.signed)

    def test_unsigned_third_party_blocks_everything_until_approved(self):
        (self.bundle / "_internal/numpy.pyd").write_bytes(tiny_pe())
        with self.assertRaisesRegex(signing.SigningError, "numpy.pyd.*--approve-unsigned-third-party"):
            self.sign()
        self.assertEqual(self.signed, [], "the owned executables must not change either")
        plan = self.sign(approve=True)
        self.assertEqual(plan["_internal/numpy.pyd"]["role"], "third_party_signed_as_distributor")
        self.assertIn("_internal/numpy.pyd", self.signed)

    def test_corrupt_vendor_signature_is_never_hidden_by_resigning(self):
        for status in ("HashMismatch", "NotTrusted", "UnknownError", "NotTimeValid"):
            (self.bundle / "_internal/lib.dll").write_bytes(tiny_pe())
            self.status["_internal/lib.dll"] = signed_record(subject="CN=Vendor", status=status)
            with self.subTest(status), self.assertRaisesRegex(signing.SigningError, "invalid vendor signature"):
                self.sign(approve=True)
            self.assertEqual(self.signed, [])

    def test_owned_binary_signed_by_someone_else_is_refused(self):
        self.status["ALFRED.exe"] = VENDOR
        with self.assertRaisesRegex(signing.SigningError, "ALFRED.exe: unexpected signature"):
            self.sign(approve=True)

    def test_missing_owned_binary_is_refused(self):
        (self.bundle / "ALFRED Launcher.exe").unlink()
        with self.assertRaisesRegex(signing.SigningError, "ALFRED Launcher.exe: required"):
            self.sign(approve=True)

    def test_unsupported_format_and_fake_dll_block(self):
        (self.bundle / "_internal/setup.msi").write_bytes(b"x")
        (self.bundle / "_internal/fake.dll").write_bytes(b"not a pe")
        with self.assertRaises(signing.SigningError) as caught:
            self.sign(approve=True)
        self.assertIn("setup.msi: unsupported", str(caught.exception))
        self.assertIn("fake.dll: invalid", str(caught.exception))

    def test_pe_is_found_by_content_and_data_is_never_a_candidate(self):
        (self.bundle / "_internal/renamed.bin").write_bytes(tiny_pe())
        for name in ("db.sqlite3", "model.onnx", "module.py", "app.js"):
            (self.bundle / "_internal" / name).write_bytes(b"data")
        (self.bundle / "_internal/looks-like-dos.dat").write_bytes(b"MZ" + b"\0" * 100)
        found = {row["path"] for row in signing.scan_tree(self.bundle)}
        self.assertIn("_internal/renamed.bin", found)
        self.assertFalse(found & {"_internal/" + name for name in ("db.sqlite3", "model.onnx", "module.py", "app.js", "looks-like-dos.dat")})

    def test_rerun_keeps_files_already_signed_by_this_publisher(self):
        self.all_signed()
        self.sign()
        self.assertEqual(self.signed, [])


class VerificationTests(SigningCase):
    def setUp(self):
        super().setUp()
        (self.bundle / "_internal/vendor.dll").write_bytes(tiny_pe())
        self.status["_internal/vendor.dll"] = VENDOR
        with mock.patch.object(signing, "sign_file"):
            self.plan = signing.sign_bundle(self.bundle, self.config())
        self.all_signed()
        self.output = self.work / "output"
        self.output.mkdir()
        (self.output / signing.SETUP).write_bytes(tiny_pe(b"setup"))
        self.status.update({signing.SETUP: signed_record(), signing.UNINSTALLER: signed_record()})
        for name in signing.OWNED_SCRIPTS:
            (self.output / name).write_text("# script", encoding="ascii")
            self.status[name] = signed_record()
        (self.output / "ALFRED-Windows-x64.zip").write_bytes(b"zip")
        self.log = self.output / "inno-signing-log.jsonl"
        self.log.write_text('{"file":"uninst.e32.tmp"}\n{"file":"ALFRED-Setup.exe"}\n', encoding="utf-8")
        patcher = mock.patch.object(signing.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, SIGNTOOL_OK, ""))
        patcher.start()
        self.addCleanup(patcher.stop)

    def manifest(self):
        return signing.write_signing_manifest(self.bundle, self.output, self.plan, self.config(), dict(source_commit="c" * 40, source_tree="t" * 40), self.log)

    def test_manifest_records_required_fields_and_no_secrets(self):
        path = self.manifest()
        text = path.read_text(encoding="utf-8")
        manifest = json.loads(text)
        rows = {row["path"]: row for row in manifest["bundle"] + manifest["output"]}
        for name in (*signing.OWNED, signing.SETUP):
            row = rows[name]
            self.assertEqual(row["publisher"], PUBLISHER)
            self.assertEqual(row["certificate_thumbprint"], THUMBPRINT)
            self.assertEqual(len(row["sha256"]), 64)
            self.assertEqual(row["signing_status"], "signed")
            self.assertEqual(row["verification"], "signtool+authenticode")
            self.assertIn("2026", row["timestamp"])
        self.assertEqual(rows["_internal/vendor.dll"]["role"], "vendor_preserved")
        self.assertEqual(rows["Start ALFRED.cmd"]["signing_status"], "cannot_carry_authenticode")
        self.assertIn("NOT_OBSERVED", manifest["smart_app_control"])
        self.assertTrue(any("_setup64.tmp" in blocker for blocker in manifest["acceptance_blockers"]))
        for word in ("password", "private_key", "pfx", "pin\""):
            self.assertNotIn(word, text.lower())
        self.assertEqual(signing.verify_release(path, self.bundle)["verified"], True)

    def test_wrong_publisher_fails(self):
        self.status["ALFRED.exe"] = signed_record(subject="CN=Other Publisher")
        with self.assertRaisesRegex(signing.SigningError, "ALFRED.exe: publisher does not match"):
            self.manifest()

    def test_missing_signed_component_fails(self):
        (self.bundle / "ALFRED.exe").unlink()
        with self.assertRaisesRegex(signing.SigningError, "ALFRED.exe: missing"):
            self.manifest()
        (self.bundle / "ALFRED.exe").write_bytes(tiny_pe())
        (self.output / signing.SETUP).unlink()
        with self.assertRaisesRegex(signing.SigningError, "ALFRED-Setup.exe: missing"):
            self.manifest()

    def test_unsigned_setup_fails(self):
        self.status[signing.SETUP] = UNSIGNED
        with self.assertRaisesRegex(signing.SigningError, "ALFRED-Setup.exe: signature status is NotSigned"):
            self.manifest()

    def test_signtool_verification_failure_fails(self):
        with mock.patch.object(signing.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "SignTool Error")):
            with self.assertRaisesRegex(signing.SigningError, "signtool verify exit code 1"):
                self.manifest()

    def test_missing_inno_signing_record_fails(self):
        self.log.unlink()
        with self.assertRaisesRegex(signing.SigningError, "signing record"):
            self.manifest()
        self.log.write_text('{"file":"ALFRED-Setup.exe"}\n', encoding="utf-8")
        with self.assertRaisesRegex(signing.SigningError, "both its uninstaller and Setup"):
            self.manifest()

    def test_binary_changed_after_signing_fails_even_if_its_signature_still_reads_valid(self):
        path = self.manifest()
        with (self.bundle / "ALFRED.exe").open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaisesRegex(signing.SigningError, "ALFRED.exe: changed after signing"):
            signing.verify_release(path, self.bundle)

    def test_setup_changed_after_signing_fails(self):
        path = self.manifest()
        (self.output / signing.SETUP).write_bytes(tiny_pe(b"other"))
        with self.assertRaisesRegex(signing.SigningError, "ALFRED-Setup.exe: changed after signing"):
            signing.verify_release(path)

    def test_portable_archive_changed_after_signing_fails(self):
        path = self.manifest()
        (self.output / "ALFRED-Windows-x64.zip").write_bytes(b"other")
        with self.assertRaisesRegex(signing.SigningError, "zip: changed after signing"):
            signing.verify_release(path)

    def test_unexpected_executable_fails(self):
        path = self.manifest()
        (self.bundle / "_internal/planted.dll").write_bytes(tiny_pe())
        with self.assertRaisesRegex(signing.SigningError, "planted.dll"):
            signing.verify_release(path, self.bundle)

    def test_unsigned_development_manifest_cannot_pass_release_verification(self):
        path = self.output / "development.json"
        path.write_text(json.dumps({"signing_mode": "development"}), encoding="utf-8")
        with self.assertRaisesRegex(signing.SigningError, "release signing manifest"):
            signing.verify_release(path)

    def install_copy(self):
        installed = self.work / "installed"
        for row in json.loads(self.manifest().read_text(encoding="utf-8"))["bundle"]:
            target = installed / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((self.bundle / row["path"]).read_bytes())
            self.status[row["path"]] = self.status.get(row["path"], UNSIGNED)
        self.bundle = installed
        return installed

    def test_installed_copy_requires_the_signed_uninstaller(self):
        path = self.output / "signing-manifest.json"
        installed = self.install_copy()
        with self.assertRaisesRegex(signing.SigningError, "unins000.exe: missing"):
            signing.verify_installed(path, installed)
        (installed / signing.UNINSTALLER).write_bytes(tiny_pe())
        (installed / "Uninstall ALFRED.cmd").write_text("@echo off\n", encoding="ascii")
        self.assertTrue(signing.verify_installed(path, installed)["verified"])
        self.status[signing.UNINSTALLER] = UNSIGNED
        with self.assertRaisesRegex(signing.SigningError, "unins000.exe: signature status is NotSigned"):
            signing.verify_installed(path, installed)

    def test_inno_callback_refuses_a_bad_result_and_records_nothing(self):
        path = self.work / "uninst.e32.tmp"
        path.write_bytes(tiny_pe())
        self.status["uninst.e32.tmp"] = signed_record(timestamp_subject=None)
        config_path = self.config_file()
        log = self.work / "calls.jsonl"
        with self.assertRaisesRegex(signing.SigningError, "no timestamp"):
            signing.inno_sign(config_path, log, path)
        self.assertFalse(log.exists())
        self.status["uninst.e32.tmp"] = signed_record()
        signing.inno_sign(config_path, log, path)
        self.assertEqual(json.loads(log.read_text(encoding="utf-8"))["file"], "uninst.e32.tmp")

    def test_inno_definition_escapes_paths_and_uses_its_file_token(self):
        definition = signing.inno_sign_tool(Path("C:/a$b/config.json"), Path("C:/x/log.jsonl"))
        self.assertTrue(definition.startswith("/Salfredsign=$q"))
        self.assertIn("a$$b", definition)
        self.assertTrue(definition.endswith(" $f"))
        self.assertIn(" -I ", definition)


class InnoScriptTests(unittest.TestCase):
    text = (signing.ROOT / "packaging/ALFRED.iss").read_text(encoding="utf-8")

    def test_signing_directives_exist_only_for_release(self):
        release, development = self.text.split("#ifdef AlfredReleaseSigned", 1)[1].split("#else", 1)
        development = development.split("#endif", 1)[0]
        for directive in ("SignTool=alfredsign", "SignedUninstaller=yes"):
            self.assertIn(directive, release)
            self.assertNotIn(directive, development)
        self.assertIn("UNSIGNED DEVELOPMENT BUILD", development)
        self.assertNotIn("UNSIGNED", release)

    def test_owned_executables_are_checked_not_signed_blindly(self):
        for name in signing.OWNED:
            self.assertIn(f'Source: "{{#BundleDir}}\\{name}"; DestDir: "{{app}}"; Flags: ignoreversion signcheck', self.text)
        self.assertNotRegex(self.text, r"Flags:[^\n]*\bsign(once)?\b")
        self.assertIn('Excludes: "\\ALFRED.exe,\\ALFRED Launcher.exe"', self.text)

    def test_install_behaviour_is_unchanged(self):
        for line in ("AppId={{D4BFC620-610B-4AF7-81BF-215ECAC7297B}", "PrivilegesRequired=lowest",
                     "UninstallDisplayName=ALFRED", "CloseApplications=no", "function StopAlfred: Boolean;"):
            self.assertIn(line, self.text)


class PackageModeTests(unittest.TestCase):
    """package_windows_release.main with an injected compiler and a small synthetic bundle."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.work = Path(directory.name)
        self.bundle = self.work / "bundle"
        self.bundle.mkdir()
        for name in (*signing.OWNED, "NOTICE.txt", "build-provenance.json"):
            (self.bundle / name).write_bytes(tiny_pe())
        (self.bundle / "project-identity.json").write_text("{}", encoding="utf-8")
        self.output = self.work / "output"
        self.commands = []
        source = dict(source_commit="c" * 40, source_tree="t" * 40, source_dirty=False)
        files = sorted(path for path in self.bundle.iterdir())
        for target, kwargs in ((package, dict(inspect_bundle=mock.Mock(return_value=files),
                                              verify_build_provenance=mock.Mock(return_value=source),
                                              write_acceptance_kit=mock.Mock(side_effect=self.fake_kit))),
                               (package.subprocess, dict(run=mock.Mock(side_effect=self.fake_compile)))):
            patcher = mock.patch.multiple(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def fake_kit(self, bundle, output):
        for name in signing.OWNED_SCRIPTS:
            (output / name).write_text("# script", encoding="ascii")

    def fake_compile(self, command, check):
        self.commands.append(command)
        (self.output / "ALFRED-Setup.exe").write_bytes(tiny_pe())

    def main(self, *extra):
        arguments = ["package", "--bundle", str(self.bundle), "--output", str(self.output), "--iscc", "ISCC.exe", *extra]
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", arguments), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            package.main()
        return stdout.getvalue()

    def test_mode_must_be_explicit(self):
        with self.assertRaises(SystemExit):
            self.main()
        self.assertEqual(self.commands, [])

    def test_development_build_is_labelled_and_defines_no_signing(self):
        text = self.main("--signing-mode", "development")
        self.assertIn("UNSIGNED DEVELOPMENT BUILD", text)
        self.assertFalse([part for part in self.commands[0] if "AlfredReleaseSigned" in part or part.startswith("/S")])
        self.assertIn("UNSIGNED DEVELOPMENT BUILD", (self.output / package.LABEL_FILE).read_text(encoding="utf-8"))
        manifest = json.loads((self.output / "release-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["signing"]["mode"], "development")
        self.assertEqual(manifest["signing"]["smart_app_control"], "not claimed")
        self.assertIn("ALFRED-Setup.exe", manifest["artifacts"])
        with zipfile.ZipFile(self.output / "ALFRED-Windows-x64.zip") as archive:
            self.assertIn(f"ALFRED/{package.LABEL_FILE}", archive.namelist())
        self.assertFalse((self.output / "signing-manifest.json").exists())

    def test_development_refuses_signing_options(self):
        with self.assertRaises(SystemExit):
            self.main("--signing-mode", "development", "--approve-unsigned-third-party")

    def test_release_without_credentials_stops_before_compiling(self):
        with mock.patch.dict(os.environ, {"CI": "", "GITHUB_ACTIONS": ""}), self.assertRaises(SystemExit):
            self.main("--signing-mode", "release", "--authorize-production-signing", "c" * 40)
        self.assertEqual(self.commands, [])
        self.assertFalse((self.output / "ALFRED-Setup.exe").exists())

    def test_release_without_authorization_stops_before_compiling(self):
        with mock.patch.dict(os.environ, {"CI": "", "GITHUB_ACTIONS": ""}), self.assertRaises(SystemExit):
            self.main("--signing-mode", "release")
        self.assertEqual(self.commands, [])

    def release_args(self):
        return ("--signing-mode", "release", "--signing-config", str(self.work / "config.json"),
                "--authorize-production-signing", "c" * 40)

    def test_failed_release_verification_leaves_no_release_and_no_unsigned_fallback(self):
        config = {"signtool": "signtool.exe"}
        with mock.patch.object(signing, "prepare_release", return_value=config), \
                mock.patch.object(signing, "sign_bundle", return_value=[]), \
                mock.patch.object(signing, "inno_sign_tool", return_value="/Salfredsign=x $f"), \
                mock.patch.object(signing, "sign_file"), \
                mock.patch.object(signing, "write_signing_manifest", side_effect=signing.SigningError("bad signature")):
            with self.assertRaisesRegex(signing.SigningError, "bad signature"):
                self.main(*self.release_args())
        self.assertIn("/DAlfredReleaseSigned=1", self.commands[0])
        self.assertEqual(len(self.commands), 1, "no second, unsigned compile")
        for name in ("ALFRED-Setup.exe", "ALFRED-Windows-x64.zip", "release-manifest.json", "SHA256SUMS.txt"):
            self.assertFalse((self.output / name).exists(), name)

    def test_failed_bundle_signing_never_reaches_the_compiler(self):
        with mock.patch.object(signing, "prepare_release", return_value={}), \
                mock.patch.object(signing, "sign_bundle", side_effect=signing.SigningError("refused")):
            with self.assertRaises(signing.SigningError):
                self.main(*self.release_args())
        self.assertEqual(self.commands, [])

    def test_successful_release_links_the_signing_manifest(self):
        def write_manifest(bundle, output, plan, config, source, log):
            path = output / "signing-manifest.json"
            path.write_text("{}", encoding="utf-8")
            return path
        with mock.patch.object(signing, "prepare_release", return_value={}), \
                mock.patch.object(signing, "sign_bundle", return_value=[]), \
                mock.patch.object(signing, "inno_sign_tool", return_value="/Salfredsign=x $f"), \
                mock.patch.object(signing, "sign_file") as sign_file, \
                mock.patch.object(signing, "write_signing_manifest", side_effect=write_manifest):
            self.main(*self.release_args())
        self.assertEqual(sign_file.call_count, len(signing.OWNED_SCRIPTS))
        manifest = json.loads((self.output / "release-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["signing"]["mode"], "release")
        self.assertIn("NOT_OBSERVED", manifest["signing"]["smart_app_control"])
        self.assertFalse((self.output / package.LABEL_FILE).exists())


@unittest.skipUnless(os.name == "nt" and os.environ.get("ALFRED_SIGNING_E2E") == "1",
                     "Set ALFRED_SIGNING_E2E=1 to use real Authenticode and Inno Setup with a throwaway certificate")
class RealAuthenticodeTests(unittest.TestCase):
    """Real PowerShell signatures made with an untrusted certificate, deleted afterwards. Nothing signed here is executed."""
    iscc = Path(os.environ.get("ALFRED_ISCC", "F:/ALFRED-tools/InnoSetup/ISCC.exe"))
    subject = "CN=ALFRED SYNTHETIC TEST NOT TRUSTED"

    @staticmethod
    def powershell(script):
        result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                                capture_output=True, text=True, errors="replace", timeout=120)
        if result.returncode:
            raise AssertionError(result.stderr[-1000:])
        return result.stdout.strip()

    @classmethod
    def setUpClass(cls):
        cls.thumbprint = cls.powershell(
            f"(New-SelfSignedCertificate -Subject '{cls.subject}' -Type CodeSigningCert -CertStoreLocation Cert:\\CurrentUser\\My "
            "-KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 -NotAfter (Get-Date).AddDays(1)).Thumbprint")

    @classmethod
    def tearDownClass(cls):
        cls.powershell(f"Remove-Item Cert:\\CurrentUser\\My\\{cls.thumbprint} -DeleteKey")

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.work = Path(directory.name)
        self.identity = {"publisher_subject": self.subject, "certificate_sha1": self.thumbprint}

    def sign(self, path):
        status = self.powershell(f"(Set-AuthenticodeSignature -LiteralPath '{path}' -HashAlgorithm SHA256 "
                                 f"-Certificate (Get-Item Cert:\\CurrentUser\\My\\{self.thumbprint})).Status")
        self.assertNotEqual(status, "NotSigned")

    def test_real_statuses_reject_unsigned_untrusted_and_tampered_files(self):
        path = self.work / "app.exe"
        path.write_bytes(tiny_pe())
        record = signing.inspect_signatures([path])[str(path)]
        self.assertEqual(record["status"], "NotSigned")
        self.sign(path)
        record = signing.inspect_signatures([path])[str(path)]
        self.assertEqual(record["thumbprint"], self.thumbprint)
        self.assertEqual(record["subject"], self.subject)
        self.assertIn(signing.CODE_SIGNING_EKU, record["ekus"])
        problems = signing.signature_problems(record, self.identity)
        self.assertTrue(any("signature status" in problem for problem in problems), "a self-signed chain must not pass")
        self.assertIn("signature has no timestamp", problems)
        data = bytearray(path.read_bytes())
        data[0x300] ^= 0xFF
        path.write_bytes(data)
        self.assertEqual(signing.inspect_signatures([path])[str(path)]["status"], "HashMismatch")

    def test_real_certificate_preflight_refuses_a_self_signed_certificate(self):
        record = signing.inspect_certificate(self.identity)
        self.assertTrue(record["has_private_key"])
        problems = signing.certificate_problems(record, self.identity)
        self.assertIn("certificate is self-signed", problems)
        self.assertTrue(any("chain failed" in problem for problem in problems))

    @unittest.skipUnless(iscc.is_file(), "Inno Setup compiler is not available")
    def test_real_inno_script_signs_uninstaller_and_setup_and_signcheck_blocks_unsigned(self):
        callback = self.work / "callback.py"
        calls = self.work / "calls.jsonl"
        callback.write_text(
            "import json, subprocess, sys\n"
            f"script = \"Set-AuthenticodeSignature -LiteralPath '\" + sys.argv[1] + \"' -HashAlgorithm SHA256 -Certificate (Get-Item Cert:\\\\CurrentUser\\\\My\\\\{self.thumbprint}) | Out-Null\"\n"
            "result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script])\n"
            f"open(r'{calls}', 'a').write(json.dumps(sys.argv[1]) + '\\n')\n"
            "sys.exit(result.returncode)\n", encoding="utf-8")
        bundle, out = self.work / "bundle", self.work / "out"
        (bundle / "_internal").mkdir(parents=True)
        (bundle / "_internal/data.txt").write_text("synthetic", encoding="ascii")
        for name in signing.OWNED:
            (bundle / name).write_bytes(tiny_pe())
        tool = f"/Salfredsign=$q{sys.executable}$q -I $q{callback}$q $f"

        def compile_release():
            return subprocess.run([str(self.iscc), "/Q", f"/DBundleDir={bundle}", f"/DReleaseDir={out}", "/DAlfredReleaseSigned=1", tool,
                                   str(signing.ROOT / "packaging/ALFRED.iss")], capture_output=True, text=True, errors="replace", timeout=300)

        refused = compile_release()
        self.assertNotEqual(refused.returncode, 0, "signcheck must refuse unsigned ALFRED executables")
        self.assertIn("ALFRED.exe", refused.stdout + refused.stderr)
        self.assertIn("sign", (refused.stdout + refused.stderr).lower())
        self.assertFalse((out / signing.SETUP).exists())
        calls.unlink(missing_ok=True)
        for name in signing.OWNED:
            self.sign(bundle / name)
        result = compile_release()
        self.assertEqual(result.returncode, 0, result.stdout[-800:] + result.stderr[-800:])
        names = [Path(json.loads(line)).name for line in calls.read_text(encoding="utf-8").splitlines()]
        self.assertIn("uninst.e32.tmp", names)
        self.assertEqual(names[-1], signing.SETUP)
        setup = signing.inspect_signatures([out / signing.SETUP])[str(out / signing.SETUP)]
        self.assertEqual(setup["thumbprint"], self.thumbprint)
        self.assertEqual(setup["type"], "Authenticode")

    def test_real_smart_app_control_script_refuses_this_development_pc(self):
        kit = self.work / "kit"
        kit.mkdir()
        script = signing.ROOT / "scripts/verify_smart_app_control.ps1"
        (kit / script.name).write_bytes(script.read_bytes())
        guid = self.powershell("(Get-ItemProperty -LiteralPath 'HKLM:\\SOFTWARE\\Microsoft\\Cryptography' -Name MachineGuid).MachineGuid")
        import hashlib
        (kit / "acceptance-manifest.json").write_text(json.dumps(
            {"development_machine_fingerprint": hashlib.sha256(guid.encode()).hexdigest()}), encoding="utf-8")
        result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                 f"& '{kit / script.name}' -Phase Uninstall -EvidenceDirectory '{self.work / 'evidence'}'"],
                                capture_output=True, text=True, errors="replace", timeout=120)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("separate clean PC", (result.stdout + result.stderr).replace("\n", " "))
        self.assertFalse((self.work / "evidence").exists())


if __name__ == "__main__":
    unittest.main()
