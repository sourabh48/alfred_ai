<# Run in a visible local console. Enter passwords only at 7-Zip's native prompts.
   Never redirect/transcribe this console or add a password to any argument.
   This script never uploads, restores operator data, or deletes files. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Encrypt','VerifyDownloaded')][string]$Mode,
    [Parameter(Mandatory=$true)][string]$RepositoryDirectory,
    [Parameter(Mandatory=$true)][string]$SevenZipExecutable,
    [Parameter(Mandatory=$true)][string]$PythonExecutable,
    [string]$BackupDirectory,
    [string]$ExtractionDirectory,
    [string]$BackupRepository = 'sourabh48/alfred-private-recovery-202610'
)
$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$repository = [IO.Path]::GetFullPath($RepositoryDirectory)
if ($BackupRepository -eq 'sourabh48/alfred_ai' -or $BackupRepository -notmatch '^sourabh48/alfred-private-recovery-[A-Za-z0-9-]+$') { throw 'Use a separate temporary private recovery repository.' }
function Test-NoReparseAncestor([string]$Path) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            if ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Recovery paths cannot contain a symbolic link or junction.' }
        }
        $parent = [IO.Directory]::GetParent($current)
        $current = if ($parent) { $parent.FullName } else { $null }
    }
}
foreach ($path in @($sourceRoot,$repository,$BackupDirectory,$ExtractionDirectory) | Where-Object { $_ }) { Test-NoReparseAncestor $path }
if ($repository.Equals($sourceRoot, [StringComparison]::OrdinalIgnoreCase) -or $repository.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Encrypted recovery repository must be outside the permanent source tree.' }
foreach ($executable in @($SevenZipExecutable,$PythonExecutable)) {
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) { throw 'Required verifier or archiver is missing.' }
}
$verifier = Join-Path $PSScriptRoot 'verify_private_recovery.py'
if (-not $ExtractionDirectory -or -not [IO.Path]::IsPathRooted($ExtractionDirectory)) { throw 'Use an explicit absolute disposable extraction directory.' }
$extraction = [IO.Path]::GetFullPath($ExtractionDirectory)
if (Test-Path -LiteralPath $extraction) { throw 'Extraction directory must be new; nothing will be overwritten.' }
$runtimeRoots = @($sourceRoot,(Join-Path $env:LOCALAPPDATA 'ALFRED'),$env:ALFRED_DATA_DIR) | Where-Object { $_ }
foreach ($protected in @($runtimeRoots) + @($repository,$BackupDirectory) | Where-Object { $_ }) {
    $protected = [IO.Path]::GetFullPath($protected)
    if ($extraction.Equals($protected, [StringComparison]::OrdinalIgnoreCase) -or $extraction.StartsWith($protected + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Verification extraction cannot be inside source, backup or encrypted repository.' }
}
foreach ($protected in $runtimeRoots) {
    $protected = [IO.Path]::GetFullPath($protected)
    if ($repository.Equals($protected, [StringComparison]::OrdinalIgnoreCase) -or $repository.StartsWith($protected + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Encrypted repository cannot be inside an operator runtime profile.' }
}
function Get-PrivateVerification([string]$Directory, [switch]$Originals, [string]$Head, [string]$ExpectedHead) {
    $arguments = @($verifier,'--backup-directory',$Directory)
    if ($Originals) { $arguments += '--check-originals' }
    if ($Head) { $arguments += @('--source-head',$Head) }
    if ($ExpectedHead) { $arguments += @('--expected-source-head',$ExpectedHead) }
    $result = & $PythonExecutable @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Private data verification failed; originals are untouched.' }
    return ($result | ConvertFrom-Json)
}
function Test-EncryptedHeaders([string]$Archive) {
    # A public, deliberately wrong probe is not the archive password. No filenames are emitted.
    & $SevenZipExecutable l -slt -p- -bso0 -bse0 -bsp0 $Archive
    if ($LASTEXITCODE -ne 2) { throw 'Encrypted filenames/header protection was not established.' }
}
if ($Mode -eq 'Encrypt') {
    if (-not $BackupDirectory -or -not (Test-Path -LiteralPath $BackupDirectory -PathType Container)) { throw 'A completed private staging backup is required.' }
    $privateRoot = [IO.Path]::GetFullPath($BackupDirectory)
    if ($repository.Equals($privateRoot, [StringComparison]::OrdinalIgnoreCase) -or $repository.StartsWith($privateRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Encrypted repository cannot be inside the private backup.' }
    if (Test-Path -LiteralPath $repository) { throw 'Use a new encrypted repository directory; nothing will be overwritten.' }
    $head = (git -C $sourceRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify source commit.' }
    if (-not [string]::IsNullOrWhiteSpace((git -C $sourceRoot status --porcelain | Out-String))) { throw 'Commit and push all intended source changes before encryption.' }
    $branch = (git -C $sourceRoot branch --show-current).Trim()
    $remote = git -C $sourceRoot ls-remote origin "refs/heads/$branch"
    if ($LASTEXITCODE -ne 0 -or -not $remote -or ($remote -split '\s+')[0] -ne $head) { throw 'Source HEAD must be pushed before encryption.' }
    $verification = Get-PrivateVerification -Directory $BackupDirectory -Originals -Head $head
    if (@($verification.included.PSObject.Properties | Where-Object { $_.Value -ne $true }).Count -ne 0) { throw 'Required private recovery coverage is incomplete.' }
    New-Item -ItemType Directory -Path $repository | Out-Null
    $archiveName = 'alfred-private-backup-' + (Get-Date -Format 'yyyyMMdd') + '.7z'
    $archive = Join-Path $repository $archiveName
    Write-Host 'Use a strong unique password recoverable OFF this PC. Type it only at the native prompt.'
    Push-Location -LiteralPath $BackupDirectory
    try { & $SevenZipExecutable a -t7z -mhe=on -mx=5 -v1500m -p -bsp0 -bb0 $archive '.\*' }
    finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw 'Encryption failed; no upload is permitted.' }
    $parts = @(Get-ChildItem -LiteralPath $repository -File | Where-Object { $_.Name -match '^alfred-private-backup-\d{8}\.7z\.\d{3}$' } | Sort-Object Name)
    if ($parts.Count -eq 0) { throw 'Encrypted archive parts are missing.' }
    if (@($parts | Where-Object { $_.Length -gt 1500MB }).Count -ne 0) { throw 'Archive volume exceeds the selected safe limit.' }
    # In 26.03, bare -p on test/extract supplies an empty password; omit it to prompt.
    & $SevenZipExecutable t -bsp0 -bb0 $parts[0].FullName
    if ($LASTEXITCODE -ne 0) { throw 'Encrypted archive integrity test failed.' }
    Test-EncryptedHeaders $parts[0].FullName
    if (-not $ExtractionDirectory -or (Test-Path -LiteralPath $ExtractionDirectory)) { throw 'Use a new disposable extraction directory.' }
    & $SevenZipExecutable x -bsp0 -bb0 $parts[0].FullName "-o$ExtractionDirectory"
    if ($LASTEXITCODE -ne 0) { throw 'Local encrypted archive extraction failed.' }
    $extracted = Get-PrivateVerification -Directory $ExtractionDirectory -ExpectedHead $head
    if ($extracted.file_count -ne $verification.file_count -or $extracted.total_bytes -ne $verification.total_bytes) { throw 'Extracted backup differs.' }
    $partRecords = @($parts | ForEach-Object { [pscustomobject]@{name=$_.Name; bytes=$_.Length; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()} })
    $public = [ordered]@{created_at_utc=[DateTime]::UtcNow.ToString('o'); source_git_head=$head; archive_part_count=$parts.Count; archive_total_bytes=($parts | Measure-Object Length -Sum).Sum; archive_filename_pattern=$archiveName+'.*'; included=[ordered]@{source_runtime=$verification.included.source_runtime; frozen_runtime=$verification.included.frozen_runtime; docker_vhdx=$verification.included.docker_vhdx}}
    $public | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $repository 'backup-manifest-public.json') -Encoding UTF8
    @($partRecords | ForEach-Object { $_.sha256 + '  ' + $_.name }) | Set-Content -LiteralPath (Join-Path $repository 'encrypted-backup-sha256.txt') -Encoding ASCII
    $readme = @'
# Temporary encrypted ALFRED recovery backup

This PRIVATE repository is temporary and separate from sourabh48/alfred_ai.
Creation date (UTC): @DATE@
Source commit: @HEAD@
Expected encrypted archive parts: @COUNT@
Encryption: 7z AES-256 with encrypted filenames/headers. No password is stored here.

After reinstall: install Git, Git LFS, Python 3.12 and 7-Zip; authenticate GitHub;
clone source and this repository; download LFS objects; verify every SHA256;
enter the password only in the local 7-Zip prompt; test/extract and verify
internal hashes and SQLite; restore both profiles; recreate the venv; preserve
a database copy before migration; start and verify finance/data, media, queues,
source Git and a rebuilt native application. Follow the exact source procedure:
https://github.com/sourabh48/alfred_ai/blob/@HEAD@/docs/WINDOWS_ENCRYPTED_RECOVERY.md

Keep the REMOTE repository until recovery is proven and the user explicitly
confirms deletion. Deleting a local clone is insufficient. Verify remote deletion
afterwards. Preserve any necessary historical signing fallback inside encrypted
recovery until protected data is re-encrypted and verified, then retire it safely.
'@
    $readme.Replace('@DATE@',$public.created_at_utc).Replace('@HEAD@',$head).Replace('@COUNT@',[string]$parts.Count) | Set-Content -LiteralPath (Join-Path $repository 'README_RECOVERY.md') -Encoding UTF8
    [pscustomobject]@{archive_test='PASS'; test_extraction='PASS'; sqlite_quick_check='PASS'; archive_part_count=$parts.Count; archive_total_bytes=($parts | Measure-Object Length -Sum).Sum; source_head=$head} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repository '..\encryption-verification.local.json') -Encoding UTF8
} else {
    $public = Get-Content -LiteralPath (Join-Path $repository 'backup-manifest-public.json') -Raw | ConvertFrom-Json
    $publicKeys = 'created_at_utc','source_git_head','archive_part_count','archive_total_bytes','archive_filename_pattern','included'
    $includedKeys = 'source_runtime','frozen_runtime','docker_vhdx'
    $timestamp = [DateTimeOffset]::MinValue
    if ((($public.PSObject.Properties.Name | Sort-Object) -join ',') -ne (($publicKeys | Sort-Object) -join ',') -or
        (($public.included.PSObject.Properties.Name | Sort-Object) -join ',') -ne (($includedKeys | Sort-Object) -join ',') -or
        @($public.included.PSObject.Properties | Where-Object { $_.Value -isnot [bool] }).Count -ne 0 -or
        $public.created_at_utc -isnot [string] -or $public.source_git_head -isnot [string] -or
        $public.archive_filename_pattern -isnot [string] -or
        -not [DateTimeOffset]::TryParse([string]$public.created_at_utc, [ref]$timestamp) -or
        $public.source_git_head -notmatch '^[a-f0-9]{40}$' -or
        $public.archive_filename_pattern -notmatch '^alfred-private-backup-\d{8}\.7z\.\*$' -or
        ($public.archive_part_count -isnot [int] -and $public.archive_part_count -isnot [long]) -or
        $public.archive_part_count -lt 1 -or $public.archive_part_count -gt 999 -or
        ($public.archive_total_bytes -isnot [int] -and $public.archive_total_bytes -isnot [long]) -or
        $public.archive_total_bytes -lt 1) { throw 'Recovery checkpoint metadata is invalid or contains unapproved fields.' }
    $allowed = @('README_RECOVERY.md','backup-manifest-public.json','encrypted-backup-sha256.txt','.gitattributes')
    foreach ($required in $allowed) { if (-not (Test-Path -LiteralPath (Join-Path $repository $required) -PathType Leaf)) { throw 'Recovery repository metadata is incomplete.' } }
    $actualHashes = @(Get-Content -LiteralPath (Join-Path $repository 'encrypted-backup-sha256.txt') | Where-Object { $_.Trim() })
    if ($actualHashes.Count -ne $public.archive_part_count) { throw 'Archive part count differs from the public manifest.' }
    $records = @()
    for ($index = 0; $index -lt $actualHashes.Count; $index++) {
        if ($actualHashes[$index] -notmatch '^([a-f0-9]{64})  (alfred-private-backup-\d{8}\.7z\.\d{3})$') { throw 'Invalid archive hash record.' }
        $hash = $Matches[1]
        $name = $Matches[2]
        $expectedName = $public.archive_filename_pattern.TrimEnd('*') + ('{0:d3}' -f ($index+1))
        if ($name -ne $expectedName) { throw 'Invalid or missing archive volume.' }
        $allowed += $name
        $path = Join-Path $repository $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-Item -LiteralPath $path).Length -lt 1 -or (Get-Item -LiteralPath $path).Length -gt 1500MB -or
            (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash) { throw 'Downloaded archive size or SHA256 differs; LFS may not have downloaded content.' }
        $records += [pscustomobject]@{name=$name; bytes=(Get-Item -LiteralPath $path).Length}
    }
    if (($records | Measure-Object bytes -Sum).Sum -ne $public.archive_total_bytes) { throw 'Downloaded encrypted total differs from the public manifest.' }
    if (@(Get-ChildItem -LiteralPath $repository -Force | Where-Object { $_.Name -ne '.git' -and ($_.PSIsContainer -or $_.Name -notin $allowed) }).Count -ne 0) { throw 'Unexpected plaintext or unlisted file in encrypted repository.' }
    & $SevenZipExecutable t -bsp0 -bb0 (Join-Path $repository $records[0].name)
    if ($LASTEXITCODE -ne 0) { throw 'Downloaded archive test failed.' }
    Test-EncryptedHeaders (Join-Path $repository $records[0].name)
    if (-not $ExtractionDirectory -or (Test-Path -LiteralPath $ExtractionDirectory)) { throw 'Use a new disposable extraction directory.' }
    & $SevenZipExecutable x -bsp0 -bb0 (Join-Path $repository $records[0].name) "-o$ExtractionDirectory"
    if ($LASTEXITCODE -ne 0) { throw 'Downloaded archive extraction failed.' }
    $verification = Get-PrivateVerification -Directory $ExtractionDirectory -ExpectedHead $public.source_git_head
    if (@($verification.included.PSObject.Properties | Where-Object { $_.Value -ne $true }).Count -ne 0 -or
        @($includedKeys | Where-Object { $verification.included.$_ -ne $public.included.$_ }).Count -ne 0) { throw 'Downloaded recovery coverage differs.' }
    [pscustomobject]@{hash_verification='PASS'; archive_test='PASS'; test_extraction='PASS'; sqlite_quick_check='PASS'; archive_part_count=$records.Count; archive_total_bytes=($records | Measure-Object bytes -Sum).Sum; source_head=$public.source_git_head} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repository '..\remote-verification.local.json') -Encoding UTF8
}
Write-Host 'Verification complete. Originals, private staging and encrypted archives are retained.'
