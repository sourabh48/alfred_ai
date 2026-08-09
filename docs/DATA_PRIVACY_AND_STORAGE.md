# Data Privacy And Storage

ALFRED handles bank statements, credit reports, loan documents, resumes, and vehicle documents. Treat every production deployment as sensitive financial-data infrastructure.

## Current Encryption Status

- Email OAuth access and refresh tokens are encrypted before database save.
- Raw uploaded documents are not treated as long-term records in production. `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true` deletes the uploaded binary from Django storage after parser extraction and records `raw_file_retention` metadata in the parsed payload.
- Parsed fields remain in PostgreSQL because ALFRED needs them for dashboards, review queues, learning memory, and calculations.
- True "developers cannot ever see user data" requires operational controls and, for raw documents, client-side encryption or local-only extraction. Server-side OCR/parsing means the server sees the file briefly during extraction.

## Production Default

AWS deployments must set:

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

## AWS Storage Controls

Use these controls before allowing real users:

- Enable RDS encryption at rest.
- Keep RDS private, not publicly reachable.
- Restrict database access to the app security group only.
- Use Redis inside a private network/security group.
- Do not grant developers production database credentials.
- Keep EC2 SSH access limited to operators who need deployment access.
- Store `/etc/alfred/alfred.env` outside the repo with `chmod 600`.
- Enable EBS encryption on the EC2 volume.
- If S3 is later used for media/artifacts, enable SSE-KMS, block public access, version/lifecycle policies, and least-privilege IAM.
- Keep backups encrypted and access controlled.

## Developer Access Boundary

The safest production operating model is:

1. Developers push code to GitHub.
2. GitHub Actions deploys to EC2 by SSH.
3. EC2 pulls code and restarts containers.
4. Developers do not receive production `.env`, database credentials, Redis credentials, S3 credentials, or shell access unless explicitly approved.

This does not make ALFRED zero-knowledge. It prevents routine developer access to raw uploaded files and production secrets.

## If You Need Stronger Privacy Later

The next step beyond this policy is a local-first or client-side encrypted document flow:

- browser or desktop client extracts text locally
- cloud receives only approved structured fields
- user-held keys encrypt any retained document copy
- server cannot decrypt raw files

That is a larger architecture change and would reduce server-side OCR convenience.
