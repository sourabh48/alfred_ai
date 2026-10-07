# Shared upload and parser limits (M14E)

Development source only. These limits have not been promoted to the live app.
Use untracked local environment configuration to adjust them for supported
documents; never commit documents or runtime secrets with configuration changes.

| Setting | Default | Meaning |
| --- | --- | --- |
| `ALFRED_UPLOAD_FILE_BYTES` | 26,214,400 (25 MiB) | Actual decoded bytes per file |
| `ALFRED_UPLOAD_REQUEST_BYTES` | 33,554,432 (32 MiB) | Multipart stream, including fields, headers and boundaries |
| `ALFRED_UPLOAD_FILES` | 4 | Files per request, including repeated field names |
| `ALFRED_UPLOAD_FIELDS` | 1,000 | Form fields per request |
| `ALFRED_UPLOAD_FORM_BYTES` | 262,144 | Non-file form data |
| `ALFRED_UPLOAD_PARSER_SECONDS` | 90 | Shared extraction deadline per upload or retry |
| `ALFRED_UPLOAD_PARSER_MEMORY_BYTES` | 1,073,741,824 | Windows worker and child-process commit memory |
| `ALFRED_UPLOAD_PDF_PAGES` | 500 | PDF pages |
| `ALFRED_UPLOAD_PDF_OBJECTS` | 50,000 | PDF objects, including sparse recovery object IDs |
| `ALFRED_UPLOAD_EXPANDED_BYTES` | 67,108,864 | Aggregate PDF streams / actual archive expansion |
| `ALFRED_UPLOAD_ARCHIVE_MEMBERS` | 256 | DOCX/ODT members |
| `ALFRED_UPLOAD_TEXT_BYTES` | 2,097,152 | Text input / recovered statement text |
| `ALFRED_UPLOAD_TEXT_ROWS` | 50,000 | Physical text/CSV lines and recovered statement lines |
| `ALFRED_UPLOAD_IMAGE_PIXELS` | 20,000,000 | Input image or PDF page rendered at 2x |
| `ALFRED_UPLOAD_PARSER_OUTPUT_BYTES` | 4,194,304 | Worker result JSON |
| `ALFRED_UPLOAD_CONNECTIONS` | 16 | Native Waitress connection limit; four task threads |
| `ALFRED_UPLOAD_MIN_FREE_BYTES` | 134,217,728 | Free temporary disk reserve, plus request budget |

All limits must be positive integers; file size cannot exceed request size.
Invalid configuration fails closed with a safe 503. Missing temporary storage
or insufficient free space also returns 503. A resource/size breach returns
413; malformed multipart or invalid DOCX/ODT returns a safe 400.

The shared handler counts decoded file chunks before Django writes them. The
multipart stream independently counts actual bytes. Content-Length is only an
early rejection hint; the application never reads past the server's HTTP framing.
Waitress buffers and de-chunks before WSGI, with a matching transport cap.
Its chunked transport count includes framing and can reject sooner than the
application's decoded-body count. An unframed WSGI request without a valid length
is not imported. Tests also exercise framed unknown/understated-length streams.

Files always spool to disk in 64 KiB chunks (`FILE_UPLOAD_MAX_MEMORY_SIZE=0`).
That setting is a storage choice, not the size gate. Upload and retry extraction
stream inputs to the local worker; whole files are not copied into parent RAM.
Installed extraction libraries receive bounded bytes inside the child process.
Windows Job Objects bound memory and terminate OCR children when a timed-out
worker dies. The parent removes the worker directory and its OCR temporary files.
Completed and interrupted Django upload files close after successful/rejected
requests. Cleanup failures emit class/reference-only ERROR diagnostics.

Limits cover statement import, loan import/payoff evidence, investment import,
resume/recruiter attachments, credit reports, and vehicle documents/service files,
including multipart uploads through model serializers. Existing authentication,
CSRF, ownership and file-format validation still apply. Write transactions open
after successful extraction, preserving SQLite writer availability during OCR;
failed multipart processing then rolls back those model writes. Recruiter
profile creation follows parsing. Existing review-only successful imports and source-file
retention policy remain intact; retained source documents are not temporary files.

DOCX/ODT members are streamed and counted without extracting paths. PDF streams
are checked before extraction; an individual decompression can allocate memory
before its size is known, so the worker memory/time boundary remains essential.
OCR fallbacks run inside that boundary. CSV remains a supported text-document
format; bank statements remain PDF-only. There is no existing Excel workbook
statement parser or general archive extraction workflow to extend in this task.

Native transport bounds limit simultaneous buffered bodies; free-space checks
cannot reserve disk against other applications. Other servers/proxies need their
own equivalent request and connection limits. POSIX address-space limiting is
implemented, but the Windows-native behavior is the verified platform. Frozen
worker dispatch is wired through the existing launcher; a new packaged executable
has not been built or promoted as part of this development milestone.

Framework references: [Django upload handlers](https://docs.djangoproject.com/en/5.2/topics/http/file-uploads/),
[Waitress arguments](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html),
[Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
