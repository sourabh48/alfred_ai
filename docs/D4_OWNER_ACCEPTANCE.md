# D4 owner acceptance worksheet

**All observations initially PENDING.** This worksheet prepares tests; it is not
evidence they ran or authorization to alter the production installation. Preserve
existing backups. Use a separate Windows user/PC and fresh synthetic data for
installation/failure tests. Real-account validation is normal read-only sign-in.
No credentials, decrypted keys, private originals or financial values in Git/chat.

Record once per run: tester/role and independence; date/time; exact source SHA;
executable/Setup SHA256 and provenance; Windows build; Chrome/NVDA versions;
theme/viewport/zoom; synthetic evidence directory; result and redacted evidence
reference per row. A later binary/source needs a new bound observation. Record
PASS/FAIL/PENDING/NOT_APPLICABLE(with reason), not a blanket checklist approval.

## NVDA, keyboard and visual contrast

Start NVDA with Speech Viewer available locally; credentials/personal speech
remain private. Use keyboard only (Tab/Shift+Tab,Enter,Space,arrows,Escape and
NVDA browse/form navigation as appropriate). Repeat light/dark desktop and a
narrow390px view, 200% zoom/reflow; record clipping/table scrolling separately.
Synthetic Travel data needs stops/activities, a private test PDF, packing items,
opted-in and opted-out reminders and a stale/insufficient affordability scenario.

| ID | Task and expected observation | Result / evidence |
| --- | --- | --- |
| A01 | Login, skip link, landmarks/headings/navigation: correct order/names/state, focus visible, no trap or unexpected focus jump | PENDING |
| A02 | Saved trip: edit/reorder activity and stop, save,undo; meaningful buttons and announcements, inputs/focus retained through refresh; stale conflict recoverable | PENDING |
| A03 | Private documents: list/link/unlink/open owned synthetic original; label expiry/unavailable honestly; logout/revoke clears names and links. Unlink must not silently delete original | PENDING |
| A04 | Packing: add/rename/check/remove using keyboard; checked state/name announced; focus after removal predictable; persisted state after reopen | PENDING |
| A05 | Reminder consent initially off; explicit opt-in/out and cancellation announced. Native date/time picker accessible; timezone/gap/fold errors explained; closing/reopening does not revive old delivery | PENDING |
| A06 | PDF/GPX/ICS: controls accessible; validation/expired/auth/stale errors announced and focus recoverable; downloaded filename/content truthful; no false bookings/coordinates/times | PENDING |
| A07 | Current/future affordability: read labels/amount units/assumptions, traverse tables/scroll regions; distinguish zero/unavailable/shortfall/stale; validation announced without canonical money changes | PENDING |
| A08 | Offline/server error/retry, modal/open-close, logout/session expiry: correct announcement, preserved safe draft and sensible focus; no stale private data after auth loss | PENDING |
| A09 | Light/dark/narrow/zoom: no obscured controls or clipped essential text; reduced motion honored; focus and selected state do not rely on color alone | PENDING |
| A10 | Contrast: measure each relevant foreground/background in normal/hover/focus/error/selected/disabled states, overlays and native widgets; record colors, font/weight, ratio, threshold and exception reason | PENDING |

Contrast acceptance uses4.5:1 for normal text and3:1 for qualifying large text
(18pt,or14pt bold); do not round a failing ratio upward. See
[W3C SC1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
Required visual control/state/graphic information needs3:1 against adjacent
colors, subject to its stated exceptions; not every decorative border needs a
separate requirement. See [SC1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
Keyboard focus must remain visible and at least partially unobscured by
author-created content; record any overlay problem, not just computed color.
See [SC2.4.11](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html).
The prior Axe contrast-incomplete and computed-sample exclusions stay open until
observed. These tasks are scoped acceptance, not a claim of complete WCAG conformance.

For every failure record exact steps, expected/actual announcement/visual state,
source/binary and a redacted local screenshot/Speech Viewer excerpt if safe.
Stop certification on missing evidence; source/automated pass is not manual PASS.

## Installation, failed update and current-package rollback

The current D4 source has no accepted installer. c287 portable proof is historical
for that exact binary; it predates the parser guards. Owner first selects a new
exact-source build/Setup and a compatible prior package. Inno Setup is absent in
the observed development environment; do not install a compiler or replace an
existing registered installation as an incidental checklist step.

| ID | Isolated test and required outcome | Result / evidence |
| --- | --- | --- |
| I01 | Verify source/provenance/executable and Setup hashes; scan bundle for private DB/env/key/media. Stop on mismatch; keep old binaries/backups | PENDING |
| I02 | Dedicated Windows user, no registered ALFRED; record existing shortcut/startup/registry state before install. Fresh install into path with spaces; launcher/static/OCR/private synthetic original/consent work without checkout Python | PENDING |
| I03 | Upgrade while test app is running: supported shutdown/exit and no simultaneous old/new writer. Trip/packing/reminder receipts, three SQLite integrity/FK checks, encrypted originals/keys and ownership preserved with no duplicates | PENDING |
| I04 | Failed fresh installation: on disposable VM/user, use reversible non-writable install target or approved fault point. Record nonzero Setup result/log; no accepted partial app/startup/shortcut; restore fault and reinstall successfully | PENDING |
| I05 | Failed upgrade: protect fresh synthetic snapshot, deny only disposable target replacement or approved fault point; no deletion/corruption of data/keys or silent success; old known-good package remains runnable or installer stops with explicit safe recovery. Remove fault and recover after actual restart | PENDING |
| I06 | Current-package rollback: record candidate/previous hashes and compatible schema; preserve later writes and new recovery archive; switch only through approved disposable procedure. Reconcile records/IDs/keys/originals and HTTP after restart. Incompatible or changed data must block blind rollback, not overwrite a database | PENDING |
| I07 | Uninstall test app while running; wait for actual completion/locks. Data/keys/backups retained; test-owned shortcuts/registration handled correctly. Reinstall and reopen same synthetic state | PENDING |
| I08 | Separate clean PC, no checkout/Python/Docker: bound Fresh proof, normal Windows reboot, same binary bound Reboot proof; then normal sign-in/offline check | PENDING |

Existing developer lifecycle runner (only when a current Setup and isolated user
are available) verifies normal install/upgrade/uninstall and refuses an existing
registered install. It temporarily owns the user's ALFRED startup value/shortcut
and retains recovery metadata; read it before running. It does **not** implement
I04/I05 failure injection or establish I06 rollback/clean-PC acceptance:

```powershell
# Use the configured development SDK, a NEW report path, and a DISPOSABLE Windows user.
& $python scripts/verify_windows_installer.py --installer $SelectedSetup --report $NewPrivateReport
```

Use [existing clean-PC instructions](WINDOWS_ACCEPTANCE.md) with the complete
bound acceptance kit, not a lone copied script. Fresh and Reboot must share the
same previously nonexistent evidence directory and exact executable:

```powershell
.\verify_windows_acceptance.ps1 -Executable $SelectedExecutable -Phase Fresh -EvidenceDirectory $NewPrivateEvidenceDirectory
# Save other work, reboot Windows normally on the same separate PC, then:
.\verify_windows_acceptance.ps1 -Executable $SelectedExecutable -Phase Reboot -EvidenceDirectory $NewPrivateEvidenceDirectory
```

Do not fault the real disk, kill unrelated processes, alter OS security policy,
delete backups or improvise destructive cleanup. If failure cannot be injected
reversibly in a disposable environment, leave that row PENDING. Failed/inconsistent
recovery must stop and retain evidence; do not mark success after manual rescue
without separately recording rescue and retesting the original contract.

## Independent recovery and real account

| ID | Observation | Result / evidence |
| --- | --- | --- |
| R01 | Approved off-device copy: archive/hash/source identity verified at independent location; plaintext verification trees not transferred | PENDING |
| R02 | Separately recoverable protected key accessible without original Windows profile. Same-profile DPAPI blob alone is not portable-key evidence; never expose key in a report | PENDING |
| R03 | Without original device/profile: authenticated decryption into new private destination; three DB integrity/FK/typed fingerprints and originals/keys reconcile; different OS user cannot read plaintext. Missing/corrupt archive/key fails closed with no overwrite | PENDING |
| R04 | Owner normal real-account sign-in/read-only review: expected historic records/trips/consents and canonical summaries; logout/revocation clears session. No password reset, financial correction, upload or live provider call unless separately authorized | PENDING |

## Reviewer and release decision

Assign an independent reviewer using [prepared request](D4_PR20_REVIEW.md).
Record exact reviewed SHA/date/identity, findings and recommendation. Same-harness
Codex, a review request, zero review threads and automated CI are not human approval.
Owner separately inspects GitHub required check names/provider identity and review
rules without changing them. Any unavailable governance evidence stays PENDING.
Residual dependency advisories require qualified reachability/upgrade triage.

| Decision | Identity / exact SHA / date / evidence | Status |
| --- | --- | --- |
| Independent source/privacy/finance/recovery review | Not assigned/submitted | PENDING |
| Dependency advisory/target-package decision | No blanket CVE clearance | PENDING |
| A01-A10 manual accessibility | No owner observations recorded | PENDING |
| I01-I08 installation/update/rollback/clean-PC | No current installer or independent run | PENDING |
| R01-R04 device-loss/real-account | No independent run | PENDING |
| Required check/review policy identity | Existing protection visibility incomplete | PENDING |
| Runtime time zone (D4-H3) | Owner chose Asia/Kolkata; stored records unchanged; loan verified-balance rejection fixed before master | RESOLVED |
| Merge and Pages | Owner instruction 2026-10-31: merge into master and publish `docs/` if checks pass | CONDITIONAL |
| Deployment/production | Not authorized | BLOCKED |

Acceptance signs only the specified observations; it never authorizes deployment,
or production migration. Keep original143 requirements and13
extensions unchanged until separate formal evidence supports a specific promotion.
