# Data Privacy And Storage

ALFRED handles bank statements, credit reports, loan documents, resumes, and vehicle documents. Treat every production deployment as sensitive financial-data infrastructure.

## Current Encryption Status

- Email OAuth access and refresh tokens are encrypted before database save.
- Raw uploaded documents are not treated as long-term records in production. `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true` deletes the uploaded binary from Django storage after parser extraction and records `raw_file_retention` metadata in the parsed payload.
- Parsed fields remain in PostgreSQL because ALFRED needs them for dashboards, review queues, learning memory, and calculations.
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

ALFRED keeps only the database records needed for product behavior:

- parsed transaction rows and statement metadata
- extracted credit score and tradeline fields
- loan, foreclosure, and repayment metadata
- investment holdings metadata
- resume/JD structured fields and learning memory
- vehicle document fields and service logs
- parser status, confidence, and `raw_file_retention` audit metadata

## Local Storage Controls

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

This does not make ALFRED zero-knowledge. It prevents routine developer access to raw uploaded files and production secrets.

## If You Need Stronger Privacy Later

The next step beyond this policy is a local-first or client-side encrypted document flow:

- browser or desktop client extracts text locally
- cloud receives only approved structured fields
- user-held keys encrypt any retained document copy
- server cannot decrypt raw files

That is a larger architecture change and would reduce server-side OCR convenience.
