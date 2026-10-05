# Private ALFRED backup before Windows reinstall

The current active installation is the native application using `F:\ALFRED\db.sqlite3`, `media\`, `config\`, `ml_models\`, and the durable queue at `artifacts\native\jobs.sqlite3`. A second native data directory exists at `%LOCALAPPDATA%\ALFRED`; preserve it separately even though its last recorded runtime state is stopped. The script discovers both locations, any process `ALFRED_DATA_DIR`, and explicitly supplied `-AdditionalDataDirectory` values.

The source `config\local.env` also configures the inactive local Compose PostgreSQL route. Native settings override that route with SQLite. Docker/pg_dump are unavailable in the inspected installation, no PostgreSQL process was found, and the Compose host is unreachable. A historical Docker disk still exists at `%LOCALAPPDATA%\Docker\wsl\main\ext4.vhdx`; preserve it because its contents have not been mounted or classified. If a live Compose installation is discovered, use the existing `scripts/local_stack_ops.py backup` procedure and its verification before reinstalling. This native script refuses `-Runtime Source` when that source route is not SQLite.

No actual private backup has been made by preparing these files. Choose and confirm a destination on a disk that will remain untouched during reinstall. Do not choose the repository, a runtime directory, or the Windows disk you will erase. The current disk map places E/F/G on the same physical disk and D on a separate disk; drive letters alone do not establish backup independence.

## Close writers

Use ALFRED's graceful stop command before backup. For the currently running application:

```powershell
& 'F:\ALFRED\dist\ALFRED\ALFRED.exe' stop --data-dir 'F:\ALFRED'
```

The source equivalent is:

```powershell
& '.\.venv\Scripts\python.exe' alfred_native.py stop --data-dir 'F:\ALFRED'
```

Wait for successful shutdown and close independent training jobs, source servers, and workers. Do not start ALFRED while backing up. `-Quiesced` records this explicit precondition; the script also refuses known live native writers and holds the launcher's instance/worker locks while copying, creating missing lock files when necessary. These stop commands are documented here and were not executed while preparing the backup.

## Make the private backup

Replace the destination with the confirmed untouched location. This example is a command template, not evidence that E has been selected or that a backup exists.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_before_windows_reinstall.ps1 `
    -Destination 'E:\ALFRED_PRIVATE_BACKUP' `
    -Quiesced `
    -AdditionalPrivatePath "$env:LOCALAPPDATA\Docker\wsl\main\ext4.vhdx"
```

The process-only execution-policy option accommodates Windows' current restricted script policy without changing the machine policy. Additional reviewed private files or directories, such as Git access recovery files, can be supplied to `-AdditionalPrivatePath`. Do not supply a whole user profile or a global cache directory. Preserve authentication secrets in the private backup/password manager; never add its contents to Git.

Every run creates a new timestamped directory. The private manifest maps each original root/file to its backup relative path, includes SHA256 hashes, and records completion only after re-reading every copied file. SQLite's backup API includes committed WAL data and runs an integrity check on database and durable queue snapshots. Runtime logs, control files, locks, generated static files/cache, build output, environments, and known temporary/cache directories are excluded. Uploaded media and learned model state are preserved conservatively. The manifest itself may contain private filenames and must stay outside Git.

A failure returns a nonzero exit code. Any partially written timestamp directory has `complete: false`; keep it for diagnosis and rerun into a new timestamp directory after addressing the problem. Nothing is deleted or overwritten in the source installation.

## Independently verify the chosen backup

Use the actual timestamp directory returned by the script:

```powershell
$backup = 'E:\ALFRED_PRIVATE_BACKUP\ACTUAL_TIMESTAMP_DIRECTORY'
$manifest = Get-Content -LiteralPath (Join-Path $backup 'manifest.json') -Raw | ConvertFrom-Json
if (-not $manifest.complete -or $manifest.files.Count -eq 0) { throw 'Backup is incomplete.' }
foreach ($file in $manifest.files) {
    $copied = Join-Path $backup $file.backup_path
    if ((Get-FileHash -LiteralPath $copied -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) {
        throw 'Private backup hash verification failed.'
    }
}
'Private backup hashes verified.'
```

Record the successful path and verification result in the pre-reinstall status without copying private manifest contents into Git. Confirm that the retained disk is readable and will not be formatted. Keep the existing native secret file and any fallback key: they protect encrypted email credentials and signed sessions. Do not regenerate keys as a substitute for backing them up.

The reusable synthetic check does not read operator files:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test_backup_before_windows_reinstall.ps1
```

It checks committed WAL data, durable queue rows, private/config/media/model/external file hashes, generated-file exclusions, and refusals for a repository destination, absent quiescence, active writers, and a non-SQLite source route. No post-Windows restoration is performed by these checks.

Prepared-script verification on 2026-10-05: the synthetic check passed all ten named groups with exit code 0, including missing-lock creation and refusal of a physically held worker lock. It also verifies that an invalid private environment-file line is not printed. Both PowerShell scripts parse with zero syntax errors. These results validate the script on synthetic data; they do not establish that operator data has been backed up.
