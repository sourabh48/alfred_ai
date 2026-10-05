# Windows recovery from the encrypted ALFRED backup

Prepared before the PC wipe. These are later recovery instructions; no Windows
reinstall, private-data restore or backup deletion was performed by writing this
document. A command example is not evidence of a completed backup. Use the final
verified backup evidence for the retained copy, archive names and source commit.

The permanent source repository is `sourabh48/alfred_ai`. The user reports uploading
the **Desktop recovery folder** to **OneDrive**. That report is not yet proof of
cloud recovery: a fresh download and the complete verification below are required.
A **6 GB pendrive** remains an alternative retained copy, separate from the Windows
target disk. The Desktop folder alone is temporary and will not survive the wipe.
No temporary GitHub backup repository has been created. Git LFS and its quota are
not required for OneDrive or the pendrive. The encrypted archive is
`alfred-private-backup-20261006.7z.001`, one part of 67,915,749 bytes, bound to
source commit `5bf9cbe3e4c0c609e5fff5adf135ebcdc6a213b4`. Its local archive,
extraction, private hashes and all 17 SQLite checks passed. These local results
do not prove the OneDrive or pendrive copy: verify the actual retained copy below.

Keep only the five approved backup files together in the encrypted folder:
`.gitattributes`, `README_RECOVERY.md`, `backup-manifest-public.json`,
`encrypted-backup-sha256.txt` and the encrypted archive part. The prepared Desktop
bundle is `ALFRED_RECOVERY_20261006`, with those five files in `encrypted/`,
portable `tools/7za.exe`, and recovery documentation in `docs/`. Copy the **whole
bundle** to the retained destination; after reinstall, download it from OneDrive
or copy it from the pendrive to the new Desktop before following the restore steps.
Later safe source documentation may advance HEAD; the archive's verified
`source_git_head` remains the application recovery checkpoint.

## Before wiping

Saving the bundle on this PC's Desktop or in a local OneDrive sync folder is not
proof of the retained backup. For OneDrive, use its normal web **Download** command
to download the whole uploaded folder into a new `C:\ALFRED_ONEDRIVE_REMOTE_VERIFY`
folder, outside OneDrive sync, the Desktop bundle and original staging. Keep the
downloaded ZIP if OneDrive supplies one. Extract it into a new folder using trusted
tools; reject absolute paths, `..` traversal and symbolic-link/reparse entries that
could write outside that folder. Do not overwrite an existing copy. Locate the
bundle root beneath any ZIP wrapper directory and confirm the entire bundle is
present, including `encrypted/.gitattributes`. Follow Microsoft's
[normal download instructions](https://support.microsoft.com/en-gb/onedrive/download-files-and-folders-from-onedrive-or-sharepoint).

Use the trusted existing checkout and local 7-Zip for pre-wipe verification.
Compare the downloaded encrypted archive and portable tool hashes against the
trusted local recovery evidence before running any downloaded script or tool.
Set `$SourceRoot` to `F:\ALFRED` and `$BackupClone` to the fresh cloud download's
`ALFRED_RECOVERY_20261006\encrypted` folder. For the pendrive alternative, use its
actual `encrypted` folder and read the bytes directly from that device. The later
restore example clones source into a new location.

Do not wipe until the final evidence confirms the complete retained copy,
matching SHA256 hashes read from the fresh cloud download or physical device,
successful decryption/archive test,
extraction, every private-file hash and all SQLite integrity checks.
Both runtime profiles and the historical Docker disk must be included unless
the disk is explicitly proved unnecessary. Keep originals until that gate
passes. Keep the archive password in a trusted source that survives the wipe;
never paste it into an agent/chat, command argument, script, Git or a manifest.
If using a pendrive, safely eject and disconnect it before Windows installation or
disk cleanup. It must survive the wipe. Do not reformat it, select it as the
Windows target disk or use it to create Windows installation media.

The prepared helper uses `-p` only when creating the encrypted archive. With
the verified Windows 7-Zip 26.03 console, test/extract commands omit that switch
and prompt automatically for encrypted archives; a bare `-p` there supplies an
empty password. Enter the real password directly in the visible local console,
with no transcript or redirected logging.

Confirm GitHub password/recovery, 2FA/recovery codes, email and later CLI/browser
authentication can be recovered independently of this PC. Confirm Windows
installation media and the intended target disk. Required ALFRED signing keys,
fallback keys, provider configuration and OAuth state must survive inside the
encrypted backup or another independently recoverable secure source.
For OneDrive recovery, separately confirm Microsoft-account login, 2FA/recovery
and recovery email are accessible after the wipe. GitHub readiness does not prove
Microsoft-account readiness. Request YES/NO only, never passwords or recovery codes.

7z AES-256 must use encrypted headers. If choosing the optional GitHub alternative
instead of OneDrive or the pendrive, use a **different, private** repository containing only
encrypted archives and safe metadata; never use `sourabh48/alfred_ai`. The
proposed temporary name is `sourabh48/alfred-private-recovery-202610`; verify the
actual repository and private visibility. The planned 1500 MiB volumes fit the
2 GB per-file Git LFS limit for GitHub Free/Pro, but check current account
storage/bandwidth usage and limits before uploading. At preparation time the
published Free/Pro allowances are 10 GiB storage and 10 GiB download bandwidth.
A fresh verification clone consumes download bandwidth. Do not omit data to
fit a quota. [Git LFS file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage),
[Git LFS billing/allowances](https://docs.github.com/en/billing/concepts/product-billing/git-lfs).

## Install recovery prerequisites after Windows reinstall

Install Git for Windows, a working authenticated GitHub Git client, and 64-bit
Python 3.12. Use the official portable 7-Zip included in the retained bundle, or
install official 7-Zip if needed. Git LFS and GitHub CLI are needed only for the
optional GitHub backup alternative. Follow
[Windows setup](WINDOWS_SETUP.md) for ALFRED's actual browser/OCR/runtime
requirements. Agent Node/Bun tools are separate from application dependencies.
Use [official 7-Zip](https://www.7-zip.org/) and [Git LFS](https://git-lfs.com/).

```powershell
git --version
py -3.12 --version
$BundleRoot = Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'ALFRED_RECOVERY_20261006'
$SevenZip = Join-Path $BundleRoot 'tools\7za.exe'
if (-not (Test-Path -LiteralPath $SevenZip -PathType Leaf)) { $SevenZip = 'C:\Program Files\7-Zip\7z.exe' }
if (-not (Test-Path -LiteralPath $SevenZip -PathType Leaf)) { throw 'Restore the portable 7-Zip tool or install official 7-Zip first.' }
```

Authenticate through the normal interactive flow. Do not transfer tokens into
the source or backup checkout. Use a recovery working folder with sufficient
free space for the archives, extracted private data and migration safety copies.
Protect this folder as private; decrypted data must never be committed.

## Clone source and use the retained Desktop bundle

Do not clone over an existing checkout. These example locations are new paths;
the source root is the folder containing `manage.py`, not its `alfred_ai` package.
The complete bundle should now have been downloaded from OneDrive or copied from
the retained pendrive to the new Desktop. Keep the retained backup untouched
through recovery verification.

```powershell
$ErrorActionPreference = 'Stop'
$SourceRoot = 'F:\ALFRED\alfred_ai'
$RecoveryRoot = 'C:\ALFRED_RECOVERY'
$BackupClone = Join-Path $BundleRoot 'encrypted'
$Recovered = Join-Path $RecoveryRoot 'decrypted-checkpoint'
$ExpectedSourceHead = '5bf9cbe3e4c0c609e5fff5adf135ebcdc6a213b4'
New-Item -ItemType Directory -Path 'F:\ALFRED', $RecoveryRoot -Force | Out-Null
git clone --branch codex/native-runtime-hardening-20260918 https://github.com/sourabh48/alfred_ai.git $SourceRoot
if ($LASTEXITCODE -ne 0) { throw 'Source clone failed.' }
if (-not (Test-Path -LiteralPath $BackupClone -PathType Container)) { throw 'Retained encrypted backup folder is unavailable.' }
```

Check every encrypted part after copying the retained bundle back to Desktop.
For the mandatory **pre-wipe retained-copy test**, set `$BackupClone` to the fresh
OneDrive download's `encrypted` folder or the actual USB `encrypted` folder;
read both the hash list and archive bytes from that copy, not the original Desktop,
sync cache or staging folder. Cross-check against the trusted final backup evidence:

```powershell
$HashRecords = @(Get-Content -LiteralPath (Join-Path $BackupClone 'encrypted-backup-sha256.txt') | Where-Object { $_.Trim() })
if ($HashRecords.Count -eq 0) { throw 'Encrypted archive hashes are missing.' }
foreach ($HashRecord in $HashRecords) {
    if ($HashRecord -notmatch '^([a-f0-9]{64})  (alfred-private-backup-\d{8}\.7z\.\d{3})$') { throw 'Invalid encrypted archive hash record.' }
    $ExpectedHash = $Matches[1]
    $Part = Join-Path $BackupClone $Matches[2]
    if ((Get-FileHash -LiteralPath $Part -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedHash) { throw 'Retained archive hash mismatch.' }
}
```

### Optional alternative: private GitHub backup

Skip this section for OneDrive or pendrive recovery. Only if a complete PRIVATE
GitHub backup was subsequently uploaded and its fresh download tested, replace
`$BackupClone` with a new local clone path and use its actual repository name:

```powershell
$BackupClone = Join-Path $RecoveryRoot 'encrypted-backup'
$BackupRepository = 'sourabh48/alfred-private-recovery-202610' # Use the verified actual name.
git lfs version
git lfs install
gh auth login
gh auth status
$RepositoryInfo = gh repo view $BackupRepository --json nameWithOwner,visibility | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $RepositoryInfo.visibility -ne 'PRIVATE') { throw 'Private backup repository cannot be confirmed.' }
git clone "https://github.com/$BackupRepository.git" $BackupClone
if ($LASTEXITCODE -ne 0) { throw 'Encrypted backup clone failed.' }
git -C $BackupClone lfs pull
if ($LASTEXITCODE -ne 0) { throw 'Git LFS download failed.' }
git -C $BackupClone lfs fsck
if ($LASTEXITCODE -ne 0) { throw 'Git LFS verification failed.' }
```

### Check the archive-bound source commit

For every method, cross-check the public manifest against the final pre-wipe
evidence and checkout the exact archive-bound source:

```powershell
$Public = Get-Content -LiteralPath (Join-Path $BackupClone 'backup-manifest-public.json') -Raw | ConvertFrom-Json
if ($Public.source_git_head -notmatch '^[0-9a-f]{40}$' -or $Public.source_git_head -ne $ExpectedSourceHead) { throw 'Recovery source commit differs from the verified checkpoint.' }
git -C $SourceRoot checkout --detach $Public.source_git_head
if ($LASTEXITCODE -ne 0) { throw 'Recovery source commit is unavailable.' }
if ((git -C $SourceRoot rev-parse HEAD).Trim() -ne $Public.source_git_head) { throw 'Source HEAD mismatch.' }
git -C $SourceRoot status --short
```

Use the SHA and backup location recorded in the final pre-wipe evidence to
cross-check the public manifest. After recovery validation, create a
development branch from this exact commit if continuing engineering work. Do not
let a newer branch tip silently replace the known recovery checkpoint.

The public manifest contains only its timestamp, source SHA, encrypted part
count/total, archive filename pattern and source/frozen/Docker inclusion flags.
Per-part names and SHA256 hashes are in `encrypted-backup-sha256.txt`; detailed
private filenames, counts and hashes remain inside the encrypted archive.

## Verify encrypted volumes from the retained backup and decrypt interactively

Run the versioned verifier from the exact source checkpoint against the retained
encrypted folder: the fresh OneDrive download or USB folder for the pre-wipe
copy test, the new Desktop copy after reinstall, or a newly downloaded GitHub
clone for that alternative.
It checks every
allowed file and volume, contiguous part
numbers, counts, sizes, SHA256, the independent hash file, archive test,
decryption, extraction, private manifest and SQLite databases. LFS pointer text
is not archive content and fails the size/hash check. The verifier uses only
Python's standard library; the application venv need not exist yet. Despite its
`VerifyDownloaded` mode name, this operation works directly on the retained folder
and makes no GitHub call. It does not require a temporary repository to exist.
Run this helper from the cloned source's `scripts/` directory as shown; its
source/runtime path checks depend on that location.

```powershell
$RecoveryPython = (py -3.12 -c "import sys; print(sys.executable)").Trim()
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is unavailable.' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $SourceRoot 'scripts/prepare_encrypted_recovery.ps1') `
    -Mode VerifyDownloaded -RepositoryDirectory $BackupClone `
    -SevenZipExecutable $SevenZip -PythonExecutable $RecoveryPython `
    -ExtractionDirectory $Recovered
if ($LASTEXITCODE -ne 0) { throw 'Retained encrypted recovery verification failed.' }
```

Enter the password only at the local 7-Zip console prompt. The helper never
passes the actual password in arguments. Do not enable transcripts or redirect decrypted archive listings
into material uploaded to GitHub. The internal `manifest.json` and
`backup-manifest.json` can contain private filenames, original roots and detailed
hashes; keep them inside the private recovery folder.

## Verify extracted private data before using it

The archive root contains the complete backup manifest and labelled data
directories. The preceding verifier checks every recorded private file, not only
a representative sample, including all 17 SQLite databases and historical WAL
state. Its safe `remote-verification.local.json` result is written beside the
backup folder; that filename records the chosen input verification, rather than
proving where the input was downloaded. Record fresh OneDrive download provenance
separately in the safe final evidence; no sharing URL or access token belongs in Git.
Keep the decrypted checkpoint private.
For a separate read-only recheck:

```powershell
$PrivateCheckpoint = $Recovered
& $RecoveryPython (Join-Path $SourceRoot 'scripts/verify_private_recovery.py') --backup-directory $PrivateCheckpoint
if ($LASTEXITCODE -ne 0) { throw 'Private backup verification failed.' }
```

Confirm the internal manifest represents both runtime labels, their databases,
the expected durable queues, private configuration, media and learned model
state. Check a representative uploaded file locally without publishing its name
or contents. Verify the additional-private label contains the historical Docker
disk when `included.docker_vhdx` is true. No ALFRED process should be started from
this extraction directory. A failed integrity check blocks startup and cleanup;
preserve the original encrypted download and extracted snapshots before repair.

## Map each runtime profile to its new location

The old active data root was `F:\ALFRED`, while the old Git root was also
`F:\ALFRED`. The new example clone is `F:\ALFRED\alfred_ai`. Restore by label and
chosen new location; do not blindly reuse absolute paths from the old manifest.

| Internal label | Original role | New example destination |
|---|---|---|
| `repository-runtime` | Source/default native data | `$SourceRoot` |
| `external-runtime-01` | Packaged/native profile | `$env:LOCALAPPDATA\ALFRED` |
| `external-runtime-02` | Historical first-start native profile with retained state | `$env:LOCALAPPDATA\ALFRED_RECOVERED_HISTORY\external-runtime-02` |
| `additional-private-00` | Historical Docker data disk | `%LOCALAPPDATA%\ALFRED_RECOVERED_DOCKER`, pending compatibility review |
| Remaining `additional-private-*` | Historical cleanup/pre-update backups, private validation inputs and earlier operator snapshots | `$env:LOCALAPPDATA\ALFRED_RECOVERED_HISTORY\<label>` |

Confirm the labels against the internal `sources` table before copying. Extra
runtime or additional-private labels require their own explicit mapping. Any
`configured-state/ALFRED_REGISTRY_PATH` or `configured-state/ALFRED_PERSONALITY_PATH`
data needs its configuration path updated privately to the selected new location.
Do not merge the two profile databases or replace one profile's key with another.
The real pre-wipe inventory found the historical first-start profile, private
cleanup/pre-update snapshots, unique validation inputs and six older operator
backup directories. Preserve their reviewed selection as well as the two main
profiles. Their detailed original paths are in the encrypted internal manifest.
Keep historical snapshots and their signing-key containers separate; do not
start them, merge their databases or automatically overwrite a current profile.

Use fresh target data locations, before bootstrap creates secret files. Refuse
to overwrite an existing private database or `config/native.env`. Copy labelled
runtime contents with directory structure preserved; `/E` below does not delete
destination files and must not be changed to `/MIR` or `/PURGE`.

```powershell
$FrozenRoot = Join-Path $env:LOCALAPPDATA 'ALFRED'
foreach ($Target in @($SourceRoot, $FrozenRoot)) {
    if ((Test-Path -LiteralPath (Join-Path $Target 'db.sqlite3')) -or
        (Test-Path -LiteralPath (Join-Path $Target 'config/native.env')) -or
        (Test-Path -LiteralPath (Join-Path $Target 'config/local.env')) -or
        (Test-Path -LiteralPath (Join-Path $Target '.env'))) {
        throw 'A target already contains private data; review it before restoring.'
    }
}
robocopy (Join-Path $PrivateCheckpoint 'repository-runtime') $SourceRoot /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /NFL /NDL /NP
if ($LASTEXITCODE -ge 8) { throw 'Source runtime copy failed.' }
robocopy (Join-Path $PrivateCheckpoint 'external-runtime-01') $FrozenRoot /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /NFL /NDL /NP
if ($LASTEXITCODE -ge 8) { throw 'Frozen runtime copy failed.' }
$Internal = Get-Content -LiteralPath (Join-Path $PrivateCheckpoint 'manifest.json') -Raw | ConvertFrom-Json
$Mappings = @{'repository-runtime'=$SourceRoot; 'external-runtime-01'=$FrozenRoot}
$HistoryRoot = Join-Path $env:LOCALAPPDATA 'ALFRED_RECOVERED_HISTORY'
New-Item -ItemType Directory -Path $HistoryRoot -ErrorAction Stop | Out-Null
Copy-Item -LiteralPath (Join-Path $PrivateCheckpoint 'manifest.json') -Destination (Join-Path $HistoryRoot 'manifest.json')
$HistoricalLabels = Get-ChildItem -LiteralPath $PrivateCheckpoint -Directory | Where-Object {
    $_.Name -match '^additional-private-(?!00$)\d+$|^external-runtime-(?!01$)\d+$'
}
foreach ($HistoricalLabel in $HistoricalLabels) {
    $HistoricalTarget = Join-Path $HistoryRoot $HistoricalLabel.Name
    robocopy $HistoricalLabel.FullName $HistoricalTarget /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /NFL /NDL /NP
    if ($LASTEXITCODE -ge 8) { throw 'Historical private recovery copy failed.' }
    $Mappings[$HistoricalLabel.Name] = $HistoricalTarget
}
foreach ($File in $Internal.files) {
    $Segments = $File.backup_path -split '/',2
    if ($Mappings.ContainsKey($Segments[0])) {
        $DestinationFile = Join-Path $Mappings[$Segments[0]] $Segments[1]
        if ((Get-FileHash -LiteralPath $DestinationFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $File.sha256) {
            throw 'Restored profile file differs from the verified snapshot.'
        }
    }
}
$BeforeMigration = Join-Path $RecoveryRoot 'before-migration'
New-Item -ItemType Directory -Path $BeforeMigration -ErrorAction Stop | Out-Null
Copy-Item -LiteralPath (Join-Path $SourceRoot 'db.sqlite3') -Destination (Join-Path $BeforeMigration 'source-db.sqlite3')
Copy-Item -LiteralPath (Join-Path $FrozenRoot 'db.sqlite3') -Destination (Join-Path $BeforeMigration 'frozen-db.sqlite3')
```

Retain the hash-verified extracted checkpoint unchanged as the full rollback
copy, including queues and configuration. Verify destination file hashes against
the corresponding manifest entries before using either profile. Review restored
configuration privately for old absolute paths. Do not copy `.venv`, build/dist,
ordinary logs, generated static output, browser profiles or IDE/tool caches.

Keep the historical VHDX offline until its contents and Docker/WSL compatibility
are understood. Do not overwrite a newly initialized Docker data disk or attach
the recovered disk read/write as a guess. Install Docker/WSL only if recovery of
the historical Compose data is actually needed; preserve the verified VHDX while
using a separate copy for inspection. It is separate from native SQLite startup.
Copy it out of the disposable extraction folder before that folder can be
cleaned up, keeping a permanent private retained copy:

```powershell
if ($Public.included.docker_vhdx) {
    $RetainedDockerRoot = Join-Path $env:LOCALAPPDATA 'ALFRED_RECOVERED_DOCKER'
    if (Test-Path -LiteralPath $RetainedDockerRoot) { throw 'Review the existing retained Docker destination.' }
    New-Item -ItemType Directory -Path $RetainedDockerRoot -ErrorAction Stop | Out-Null
    $RecoveredDisk = Join-Path $PrivateCheckpoint 'additional-private-00/ext4.vhdx'
    $RetainedDisk = Join-Path $RetainedDockerRoot 'ext4.vhdx'
    Copy-Item -LiteralPath $RecoveredDisk -Destination $RetainedDisk -ErrorAction Stop
    if ((Get-FileHash -LiteralPath $RecoveredDisk -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath $RetainedDisk -Algorithm SHA256).Hash) { throw 'Retained Docker disk hash mismatch.' }
}
```

If the disk is required to recover historical records, complete that recovery
and validate those records before declaring the recovery complete. An unread,
unclassified Docker disk is not evidence that historical data is unnecessary.

## Fresh environment, reviewed migrations and launch

Create a fresh application environment using the retained source instructions.
The setup script preserves restored configuration and refuses a retained database
without its signing-key file. **Do not use `-MigrateFresh` for a restored profile.**

```powershell
Set-Location $SourceRoot
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1 -DataDirectory $SourceRoot
if ($LASTEXITCODE -ne 0) { throw 'Restored source setup failed.' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1 -DataDirectory $FrozenRoot
if ($LASTEXITCODE -ne 0) { throw 'Restored frozen-profile setup failed.' }
```

With ALFRED stopped, inspect pending migrations for each restored profile before
first startup. This uses the same native configuration and lock helpers as the
launcher; it does not change the database.

```powershell
@'
from contextlib import ExitStack
from pathlib import Path
import sys
from alfred_native import InstanceLock, configure
data = Path(sys.argv[1]).resolve()
with ExitStack() as locks:
    locks.enter_context(InstanceLock(data, 'instance.lock'))
    locks.enter_context(InstanceLock(data, 'worker.lock'))
    configure(data)
    from django.core.management import call_command
    call_command('check')
    call_command('migrate', plan=True, interactive=False)
'@ | .\.venv\Scripts\python.exe - $SourceRoot
if ($LASTEXITCODE -ne 0) { throw 'Migration review failed.' }
```

Repeat for `$FrozenRoot`. Review the migration plan against the recorded
engineering checkpoint; retained operator databases had not yet received all
source currency migrations before reinstall preparation. Keep the pre-migration
copy and do not substitute missing data with a fresh empty database. Native
startup applies pending migrations. Launch one profile at a time and verify it
before moving to the next:

```powershell
.\.venv\Scripts\python.exe alfred_native.py start --data-dir $SourceRoot
.\.venv\Scripts\python.exe alfred_native.py status --data-dir $SourceRoot
# Verify application records locally, then stop gracefully.
.\.venv\Scripts\python.exe alfred_native.py stop --data-dir $SourceRoot
```

Check users, accounts, transactions/expenses, budgets, loans, investments,
documents, Travel plans, private media, learned state and queue/runtime health
against expected pre-wipe records. A successful process start alone does not prove
finance recovery. Keep the two profiles separate. Existing OAuth/provider
credentials may require interactive renewal even when their encrypted state was
restored; verify encrypted credentials can be read without publishing them.

## Rebuild native application and reinstall agents

Rebuild from recovered source and the fresh venv; do not reuse old build/dist
folders or an older release as the current checkpoint. Use a new output path:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller packaging/ALFRED.spec --noconfirm --distpath artifacts/releases/restored-build --workpath build
if ($LASTEXITCODE -ne 0) { throw 'Native rebuild failed.' }
.\.venv\Scripts\python.exe scripts/verify_packaged_launcher.py --bundle artifacts/releases/restored-build/ALFRED
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt native package verification failed.' }
& '.\artifacts\releases\restored-build\ALFRED\ALFRED.exe' start --data-dir $FrozenRoot
& '.\artifacts\releases\restored-build\ALFRED\ALFRED.exe' status --data-dir $FrozenRoot
# Verify the recovered profile, worker and important data, then stop gracefully.
& '.\artifacts\releases\restored-build\ALFRED\ALFRED.exe' stop --data-dir $FrozenRoot
```

Follow [Windows packaging](WINDOWS_PACKAGE.md) for additional package/release
validation and optional installer creation. Reinstall Codex, Claude Code,
Graphify, gstack, Ponytail and skills CLI using
[agent tooling recovery](../artifacts/reinstall/AGENT_TOOLS_REINSTALL.md).
Canonical project-local skills arrive with the source clone. Global caches and
old host-specific junctions are not restore dependencies.

## Historical signing-key recovery and rotation

The historical public signing key is compromised. Preserve any needed fallback
only inside the encrypted recovery archive/private configuration until every
encrypted historical value can be recovered. Do not promote it to the new active
key or leave indefinite dependence undocumented. After successful recovery,
identify every signing/encryption use, establish a new active key, decrypt with
the required old/fallback key, re-encrypt with the new key, verify records and
then retire the compromised fallback. Keep a protected rollback checkpoint
through verification. Rotate affected external credentials when applicable and
assess public Git history/older-package remediation separately. Never retire a
key destructively before proving all protected data can be read and re-encrypted.

## Delete the temporary remote repository only after verified recovery

This section applies only to the optional GitHub backup method. No temporary
GitHub repository exists for OneDrive or pendrive recovery, so there is no remote
GitHub repository to delete and no GitHub-deletion gate for those methods.

Keep the temporary GitHub repository until downloaded hashes and decryption,
SQLite integrity, application records/finance, media, source Git, rebuilt native
runtime and required tooling have all been verified. Resolve the signing-key
recovery/rotation requirements before discarding their only protected copy.
**Ask the user for explicit deletion confirmation at that time.** The pre-wipe
request does not authorize deletion before those gates or replace that later
confirmation. Deleting a local clone does not delete the GitHub repository.

After explicit confirmation, use the actual recorded temporary repository name:

```powershell
gh repo view $BackupRepository --json nameWithOwner,visibility
# Confirm this is the temporary private recovery repository, never alfred_ai.
# If the CLI needs delete_repo scope, authenticate its normal interactive flow:
# gh auth refresh --scopes delete_repo
gh repo delete $BackupRepository
if ($LASTEXITCODE -ne 0) { throw 'Remote backup repository deletion failed.' }
$AuthenticatedOwner = (gh api user --jq .login).Trim()
if ($LASTEXITCODE -ne 0 -or $AuthenticatedOwner -ne 'sourabh48') { throw 'Owner authentication must work before deletion verification.' }
gh repo view sourabh48/alfred_ai --json nameWithOwner
gh api "repos/$BackupRepository"
# Expected: HTTP 404, while authentication and permanent-source access above work.
```

Check the web interface as well if deletion/access is ambiguous. An authentication
failure is not evidence of deletion. Record successful remote deletion.

## Retain the OneDrive or pendrive backup until ALFRED recovery is verified

Keep the encrypted OneDrive folder or USB backup until SQLite integrity, finance/data records,
documents/media, Travel state, both required runtime profiles, native queue,
source Git and the rebuilt native runtime are verified after reinstall. Resolve
the compromised-key recovery/rotation requirements before discarding their only
protected copy. Obtain the user's explicit confirmation before erasing this
retained backup.

Only after recovery is proven and retained application copies verified should
reviewed local encrypted clones, extraction/staging and verification folders be
removed. For the optional GitHub method, also require confirmed remote deletion
as described above. First verify that every required historical
profile, operator backup and private validation input has a retained hash-checked
copy outside those temporary folders, along with its private original-path map.
Do not discard a historical key or snapshot merely because the main profile
starts. Resolve each absolute folder and confirm it is
the intended temporary recovery directory before recursive deletion; never run
cleanup against the source checkout, active runtime profiles or their sole
remaining private-data copy.
