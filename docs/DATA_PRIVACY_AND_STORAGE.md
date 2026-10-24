# Data Privacy And Storage

Post-audit development now routes source/debug and native media through the same
authenticated, owner-filtered handler. Anonymous, invalid-session, foreign-owner,
traversal and deleted-file regressions pass. This fix is not yet deployed; the
original AUD-11 reproduction remains historical evidence in the
[audit](../artifacts/audit/ALFRED_WHOLE_PROJECT_AUDIT_20261015.md).

**Current privacy boundary — 2026-10-15:** Local canonical finance SQLite is plaintext; M15 MemoryStore/index/journal encryption protects AI memory only. Read-only audit found broad local read grants on the private DB and runtime config; no ACL/key change was performed. Raw-upload cleanup is configurable, not a universal native default: native local-vault retention was explicitly deferred under ownership/deletion controls. Owner consent protects family financial summaries; it does not grant memory/document sharing. Real OpenAI/private cloud remain OFF; independent device-loss key recovery is UNVERIFIED. [Acceptance and recovery stages](ALFRED_END_TO_END_ACCEPTANCE.md).

ALFRED handles bank statements, credit reports, loan documents, resumes, and vehicle documents. Treat every production deployment as sensitive financial-data infrastructure.

## Current Encryption Status

- Email OAuth access and refresh tokens are encrypted before database save.
- Raw retention is an explicit runtime policy. `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true` deletes the binary after extraction and records `raw_file_retention`; the native local vault may retain owned files when that switch is false. Historical copies require their own retention policy.
- Parsed fields remain in the application database: SQLite for native Windows, or PostgreSQL for the optional Compose runtime. ALFRED uses these records for dashboards, review queues, learning memory, and calculations.
- Client-side operational diagnostics strip browser route URLs and route paths before storage.
- True "developers cannot ever see user data" requires operational controls and, for raw documents, client-side encryption or local-only extraction. Server-side OCR/parsing means the server sees the file briefly during extraction.

## Local Hosting Default

Local hosted deployments should keep:

```bash
ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true
```

With this enabled, uploaded files for these extraction families are deleted after the row is saved and parsed metadata is retained:

- bank and card statements
- resumes
- credit reports
- investment portfolio imports
- loan import documents
- loan closure / foreclosure documents
- vehicle documents and service invoices

Trip photos are user media, not extraction-only documents, and are not automatically deleted by this policy.

## What The App Keeps

The development FIN-MONEY Budget migration retains owner-scoped original float
representations and normalized cents in `BudgetMoneySnapshot` for recovery.
UserMoneySnapshot similarly retains original profile money for the development
User migration; profile APIs exclude it, owner reset removes it, and account
deletion cascades it. Neither snapshot type adds historical currency metadata.
CareerProfileMoneySnapshot retains original salary under the same owner boundary;
profile deletion keeps its unlinked recovery evidence, while owner reset/account
deletion removes it. It is not exposed by Career APIs and does not encrypt the DB.
MobilityMoneySnapshot similarly retains the original nine money fields and typed
source/parent links for the development Mobility migration. Source deletion
unlinks its evidence without recreating deleted records; owner reset/account
deletion removes owned snapshots, including orphans. Mobility APIs exclude these
snapshots. They share canonical database storage protections, not memory-journal
encryption, and do not establish historical currency.
This evidence is not exposed by Budget APIs. Deleting a Budget does not destroy
its recovery evidence; owner reset/account deletion removes that owner's
snapshots, including orphan rows. It lives in the canonical financial database
and shares that database's storage protections, not M15 memory encryption.
Historical backups may retain deleted evidence. This migration is not deployed.

ALFRED keeps only the database records needed for product behavior:

- parsed transaction rows and statement metadata
- extracted credit score and tradeline fields
- loan, foreclosure, and repayment metadata
- investment holdings metadata
- resume/JD structured fields and learning memory
- vehicle document fields and service logs
- parser status, confidence, and `raw_file_retention` audit metadata

## Local Storage Controls

The post-audit native launcher verifies its selected data directory before reading
configuration or starting writers. Fresh data/configuration, memory and backup
directories receive a protected owner/SYSTEM DACL. Parser/OCR files and disposable
recovery copies receive private permissions before sensitive bytes are written.
Inherited owner/SYSTEM access is accepted only below a verified private parent.
An existing unsafe directory is refused; existing keys/data are not replaced.
Source/debug startup also checks SQLite and file-backed caches before use, and
configuration files before reads. Retained media and Django streamed upload files
are protected before payload writes; this applies without the native launcher.
Existing unsafe storage requires the same explicit repair. Static assets remain
publicly serveable. Canonical SQLite is still plaintext, protected by access controls.
See the [explicit Windows repair procedure](NATIVE_WINDOWS.md#private-storage-permission-repair).
These are development protections, not evidence that production ACLs were repaired.
Filesystem permissions protect against other ordinary Windows identities; they
do not make data inaccessible to an authorized system administrator or the owner.

Use these controls before entering real financial documents:

- Keep the ALFRED host machine on a trusted private network.
- Do not expose port `8000` to the public internet.
- Use Windows Firewall or router rules to allow only trusted LAN devices if another device needs access.
- Keep `config/local.env` private and out of Git.
- Use a strong `DJANGO_SECRET_KEY`.
- Use a strong Windows account password and disk encryption where possible.
- Back up PostgreSQL and the media/artifact volumes regularly.
- Keep raw document deletion enabled unless you intentionally need retained source files.
- Give each family member their own account and use the family-link code instead of sharing passwords.

## Developer Access Boundary

For local hosting, the safest operating model is:

1. The owner runs the local machine and controls the Docker volumes.
2. Developers do not receive `config/local.env`, database dumps, raw documents, or machine access unless explicitly approved.
3. Updates are pulled from Git, then migrations and checks are run locally.

This does not make ALFRED zero-knowledge or establish filesystem access isolation. Runtime keys/configuration, canonical databases and retained files require effective OS permissions; the 2026-10-15 audit found broad local read grants requiring approved remediation.

## If You Need Stronger Privacy Later

The next step beyond this policy is a local-first or client-side encrypted document flow:

- browser or desktop client extracts text locally
- cloud receives only approved structured fields
- user-held keys encrypt any retained document copy
- server cannot decrypt raw files

That is a larger architecture change and would reduce server-side OCR convenience.
