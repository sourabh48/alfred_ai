# Windows code signing

ALFRED has two explicit build modes. `scripts/package_windows_release.py` refuses
to run without `--signing-mode`, and it never falls back from signed to unsigned.

| | `development` | `release` |
|---|---|---|
| Certificate | None | Public-CA certificate, required |
| Label | `UNSIGNED DEVELOPMENT BUILD` on the console, Setup's version name and file description, ZIP and output folder | None |
| Smart App Control | Nothing is claimed. Windows may block it. Never disable Windows security for it | Needs a separate clean-PC observation |
| Failure | Unchanged behaviour | Stops, and removes that run's Setup, ZIP and manifests |

**Current status: `BLOCKED_CERTIFICATE`.** Owner decision, 2026-11-02: no paid certificate
will be bought ("i dont wanna pay for a cert"). No public-CA certificate is configured, so no
build is publicly trusted and final trusted-signature acceptance stays blocked.

Unsigned development builds are the working mode. Windows, including Smart App Control on the
owner's PC, may block them, and that block is never bypassed. Release mode stays in place and
refuses to run without a certificate. It can be used only if this decision changes.

## What Smart App Control needs

[Microsoft's guidance](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control)
says it only considers certificates from trusted providers, and that it accepts
both RSA and ECC. A self-signed certificate is never presented as publicly trusted:
the preflight refuses one. A valid signature does not prove that Smart App Control
or SmartScreen will allow every execution, so the result must be observed.

## Certificate requirements, if the decision changes

**Nothing here is planned: the owner declined a paid certificate on 2026-11-02.** This section
is reference only. A release would need an **individual-validated (IV) code-signing
certificate** from a CA in the Microsoft Trusted Root Program. Do not put a private key, PFX,
password, PIN or token in chat, in a file in this repository, or in the signing configuration.

**Prerequisites for an individual developer in India, as far as checked on 2026-11-02:**

- [Microsoft Artifact Signing is not available](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart):
  individual developers must be in the United States or Canada.
- [SSL.com sells IV certificates](https://www.ssl.com/faqs/ssl-ov-validation-requirements/) and verifies identity,
  address and telephone number. Delivery is a FIPS 140-2 USB token or its eSigner cloud service.
- [Certum sells Open Source Code Signing](https://shop.certum.eu/open-source-code-signing.html)
  to natural persons, with a SimplySign cloud key. Certum adds "Open Source Developer" to the
  certificate name. ALFRED's licensing must meet that product's terms, so ask Certum first.
- EV is not a requirement. This pipeline does not need it.
- Before paying, ask the CA in writing: is an applicant resident in India accepted, which
  Indian identity documents are accepted, and can it be used with Windows SignTool on this PC?
  **Those three answers were not confirmed by this research.** Prices are not recorded here.

**Rules that shape the choice:**

- The private key must live in hardware (FIPS 140-2 Level 2 or Common Criteria EAL 4+). A
  downloadable PFX is not how a public CA issues these, so this pipeline has no PFX mode.
- Since [1 March 2026, a certificate lasts at most 460 days](https://knowledge.digicert.com/alerts/code-signing-certificates-459-day-validity).
  Plan a renewal about once a year.

**Provide these non-secret values in your local configuration. None is a secret, but none is needed in chat:**

| Value | Where it comes from |
|---|---|
| `publisher_subject` | The certificate's exact subject, from `certutil -store -user My` or the certificate's Details tab |
| `certificate_sha1` | The certificate's thumbprint |
| `timestamp_url` | The RFC 3161 URL in **your CA's** documentation. None is built in |
| `signtool` | Absolute path of `signtool.exe` |

**Publisher name decision for the owner.** `AppPublisher` in `packaging/ALFRED.iss` is "Life on
our Trails", but an IV certificate carries your legal name. Windows prompts will show the
certificate's name. Keep one stable identity, and decide whether `AppPublisher` should change to match.

## Install SignTool

SignTool comes with the [Windows SDK](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool).
Install only its "Windows SDK Signing Tools for Desktop Apps" feature. It is typically at
`C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64\signtool.exe`. It is **not installed on
this PC today**, so real `signtool` output parsing is covered only by recorded samples in tests,
and it must be proved by the first real signing run. The preflight refuses a SignTool that is not validly signed by Microsoft.

## Signing configuration

Keep this file **outside the repository**. Anything else in it, such as a password field, is refused.

```json
{
  "schema": 1,
  "provider": "certificate_store",
  "publisher_subject": "CN=Exact Name, O=Exact Name, L=City, S=State, C=IN",
  "certificate_sha1": "40 HEX CHARACTERS",
  "machine_store": false,
  "timestamp_url": "URL FROM YOUR CA'S DOCUMENTATION",
  "signtool": "C:\\Program Files (x86)\\Windows Kits\\10\\bin\\VERSION\\x64\\signtool.exe"
}
```

| Key location | Provider | Note |
|---|---|---|
| USB token or HSM whose certificate appears in the Windows store | `certificate_store` | The token's own software handles the PIN |
| CA cloud key that appears in the Windows store through its client (for example SimplySign) | `certificate_store` | Same command |
| Remote service with a SignTool digest library | `remote_dlib`, with `dlib` and `dmdf` paths | `certificate_sha1` is optional because some services rotate certificates. The publisher still must match |

Commands use `signtool sign /fd SHA256 /tr <url> /td SHA256 /d ALFRED /sha1 <thumbprint>`, or
`/dlib` and `/dmdf` for a remote library. A failed timestamp fails the build, after three attempts.

Signing is refused in CI (`CI` or `GITHUB_ACTIONS` set). Production credentials stay off ordinary CI and development machines.

## Build

Unsigned, for isolated synthetic testing:

```powershell
.\.venv\Scripts\python.exe scripts/package_windows_release.py --bundle artifacts/releases/next-build/ALFRED --output artifacts/releases/next-build/distributables --iscc F:/ALFRED-tools/InnoSetup/ISCC.exe --signing-mode development
```

Signed. This needs the owner's explicit decision for that exact commit, because signing changes the bundle in place:

```powershell
.\.venv\Scripts\python.exe scripts/package_windows_release.py --bundle artifacts/releases/next-build/ALFRED --output artifacts/releases/next-build/distributables --iscc F:/ALFRED-tools/InnoSetup/ISCC.exe --signing-mode release --signing-config D:\private\alfred-signing.json --authorize-production-signing (git rev-parse HEAD) --approve-unsigned-third-party
```

The order is: check configuration, SignTool and certificate; refuse the whole plan if any file is
unacceptable; sign the bundle; let Inno embed it; sign the kit's PowerShell scripts; verify everything; then write the manifests.

Hardware tokens may ask for a PIN on each signature. A release signs hundreds of files, so
enable the token's single-logon option for the signing session if the CA allows it.

## What gets signed

The roles come from `python scripts/windows_signing.py inventory --bundle <bundle>`, which changes
nothing. Files are classified by content, so a renamed PE is still found.

| Role | Files | Treatment |
|---|---|---|
| `alfred_owned` | `ALFRED.exe`, `ALFRED Launcher.exe` | Signed before embedding. Inno's `signcheck` refuses unsigned copies. Any other signature blocks |
| `vendor_preserved` | Third-party PE with a valid embedded vendor signature | Never re-signed. Hash must not change |
| `third_party_signed_as_distributor` | Third-party PE with no signature | Blocks unless `--approve-unsigned-third-party` is given. Original hash is kept in the manifest |
| Blocked | Corrupt, expired or untrusted vendor signature; PE-named non-PE file; unsupported format such as `.msi` or `.jar` | The build stops. Re-signing never hides a bad vendor signature |
| `recorded_unsignable` | `.cmd`, `.bat` | Cannot carry Authenticode. Recorded with a hash, and covered only by the clean-PC observation |
| Generated by Inno | Setup, `unins000.exe`, temporary self-copies | Signed by Inno during compile, using `SignTool=alfredsign` and `SignedUninstaller=yes` |
| Inno's helper | `_isetup/_setup64.tmp`, extracted to temp | **Unsigned, and SignTool does not reach it.** Listed in the manifest's `acceptance_blockers` |
| Never candidates | Python source, databases, model files, other data | Never signed or changed |

The portable ZIP cannot carry Authenticode. Its PE contents are signed, its hash is recorded, and
extracted `.cmd` files may be treated differently by Windows than installed ones.

**Inventory of one real frozen bundle (master `96d4637`, read-only, 2026-11-02):** 2 owned, 47
vendor-signed (Python Software Foundation, Microsoft, Intel, Eclipse), 414 unsigned third-party
(`.pyd`, DLLs and `torch/bin/protoc.exe`), 2 `.cmd`, 0 blockers.

**Those 414 files are the main release decision.** Windows App Control policies evaluate loaded
DLLs as well as executables, so leaving them unsigned is expected to fail on a protected PC, though
this has not been observed for this bundle. Signing them states that you distribute them. It adds a
signature and does not change their code.

Timestamping is what keeps a signature valid after the certificate's normal expiry, subject to trust and
revocation rules. Windows then reports it `Valid`. An expired signature with no timestamp reports `NotTimeValid`, and the pipeline rejects it.

## Verify

`signing-manifest.json` records each file's SHA-256, name, role, publisher, thumbprint, status,
timestamp and result, with no secrets. A release build writes it only after everything verifies.

```powershell
python scripts/windows_signing.py verify-release --manifest <output>/signing-manifest.json --bundle <bundle> --signtool <signtool.exe>
python scripts/windows_signing.py verify-installed --manifest <output>/signing-manifest.json --install-dir <installed folder>
.\.venv\Scripts\python.exe scripts/verify_windows_installer.py --installer <output>/ALFRED-Setup.exe --report <new report path> --signing-manifest <output>/signing-manifest.json
signtool verify /pa /v <file>
```

```powershell
Get-AuthenticodeSignature <file> | Format-List Status, SignatureType, SignerCertificate, TimeStamperCertificate
```

Rejected: missing, corrupt or unexpected signatures; a wrong publisher or thumbprint; no timestamp; a non-SHA-256 file digest; any changed byte; any unlisted executable.

## Smart App Control test

Never turn Smart App Control off on the owner's PC, and do not run this there. The script refuses that PC by its fingerprint.

1. Prepare a clean Windows 11 PC or VM with Smart App Control **On**. Microsoft documents that
   switching its mode is one-way unless the current mode is Evaluation, so plan for a fresh install or reset.
2. Copy the signed release folder there, then run these from it:

```powershell
.\verify_smart_app_control.ps1 -Phase Install -Installer .\ALFRED-Setup.exe
```

3. Restart Windows, then run:

```powershell
.\verify_smart_app_control.ps1 -Phase AfterRestart
```

```powershell
.\verify_smart_app_control.ps1 -Phase Uninstall
```

Each phase writes `<phase>-observed.json`: Setup launch, temporary code and its signatures, install, ALFRED launch, the
native background processes, restart, uninstaller launch and completion, plus [CodeIntegrity events
3076, 3077](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control), 3033 and 3034.
Run `-Phase Install -Interactive` on one pass to observe the wizard, and save screenshots of any prompt in the evidence folder.
The JSON records what happened. It is not a pass for anything it did not observe.

**Status: `NOT_OBSERVED`.** This test needs a signed release, so it cannot run while the certificate is declined.

**Evidence from Inno Setup 6.7.3 on 2026-11-02, using a synthetic Setup and a throwaway untrusted
certificate on this PC, with no ALFRED code or data.** The compiler asked to sign `uninst.e32.tmp`, then the finished Setup. At
run time `is-*.tmp/Probe-Setup.tmp` and the installed `unins000.exe` carried that certificate's
signature. `_isetup/_setup64.tmp` (6,144 bytes) did not. The log gave no sign it was executed.
Windows ran this untrusted Setup here and logged no CodeIntegrity event, so that run says
nothing about what Smart App Control will do with a real release.

### Common errors

| Symptom | Likely meaning | Do |
|---|---|---|
| `WinError 4551`, or "An Application Control policy has blocked this file" | Code Integrity blocked an unsigned, untrusted or low-reputation file | Read events 3077. Fix the file named there. Never disable the protection |
| Identical unsigned file sometimes runs, sometimes not | Seen on this PC; a varying cloud reputation answer is a possible cause, not a confirmed one | Do not treat one success as proof. Sign the file |
| Event 3077 names a `.pyd` or `.dll` | Third-party binary was left unsigned | Rebuild with the approved distributor signing |
| Event 3077 names `is-*.tmp` or `_iu*.tmp` | Inno's temporary copy was not trusted | Confirm `SignedUninstaller=yes` and the certificate |
| `NotTimeValid` | Expired with no timestamp | Re-sign with a working timestamp URL |
| `HashMismatch` | Bytes changed after signing | Treat as tampering. Rebuild |
| `UnknownError`, or chain failure | Root is not trusted on this PC | Check the CA's chain. Do not add a root by hand to get past it |
| SmartScreen "unknown publisher" warning on a signed file | New certificates can have little reputation | Observe and record. Reputation grows with use, and signing does not guarantee it |

## Renewal and rotation

Renew before expiry, ideally keeping the same subject so the publisher stays stable. Then update
`certificate_sha1` and rebuild. Files signed and timestamped earlier stay valid. A changed subject
is a publisher change: tell users and update `publisher_subject` deliberately. If a key is
compromised, ask the CA to revoke it, build again with a new certificate, and withdraw affected releases.

## Release and rollback

Signing does not authorize publication, deployment or a merge. Signed release builds need the owner's
authorization per commit. Keep the prior release and its manifest. To roll back, reinstall the prior
signed Setup. Saved data lives in `%LOCALAPPDATA%\ALFRED` and is not touched by signing, which adds
no data migration, key rotation or backup deletion. Signing and timestamping are the only network
steps, carrying file hashes and not private data. The installed application stays local-first and offline-capable.

Large installers: Inno's documentation recommends disk spanning for large signed Setup files because Windows
verification at launch can be slow. It would change delivery from one file to several, so it is not
enabled. Reconsider it if the clean-PC run shows a long delay at launch.
