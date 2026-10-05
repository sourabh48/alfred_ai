<# Synthetic public metadata/hash checks only; no private data, archive password or Python invocation.
   Run: powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/test_encrypted_recovery_manifest.ps1 #>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root 'scripts/prepare_encrypted_recovery.ps1'
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('alfred-public-manifest-test-' + [Guid]::NewGuid().ToString('N'))
$repository = Join-Path $temporary 'encrypted-repository'
New-Item -ItemType Directory -Path $repository | Out-Null
$probe = Join-Path $temporary 'archiver-probe.cmd'
$marker = Join-Path $temporary 'archiver-called'
[IO.File]::WriteAllText($probe, '@echo off' + "`r`n" + 'echo reached>"%~dp0archiver-called"' + "`r`nexit /b 2`r`n")
$name = 'alfred-private-backup-20261006.7z.001'
$part = Join-Path $repository $name
[IO.File]::WriteAllText($part, 'synthetic archive content; never private data')
$hash = (Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash.ToLowerInvariant()
$hashRecord = $hash + '  ' + $name
$base = [ordered]@{created_at_utc='2026-10-06T00:00:00Z'; source_git_head=('a'*40); archive_part_count=1; archive_total_bytes=(Get-Item -LiteralPath $part).Length; archive_filename_pattern='alfred-private-backup-20261006.7z.*'; included=[ordered]@{source_runtime=$true; frozen_runtime=$true; docker_vhdx=$true}}
foreach ($file in @('README_RECOVERY.md','.gitattributes')) { [IO.File]::WriteAllText((Join-Path $repository $file), 'synthetic metadata') }
$checks = 0
function Check-Rejection([string]$Expected, [hashtable]$Changes=@{}, [string]$HashLine=$hashRecord, [bool]$ReachArchiver=$false) {
    $public = $base | ConvertTo-Json -Depth 4 | ConvertFrom-Json
    foreach ($key in $Changes.Keys) { $public | Add-Member -MemberType NoteProperty -Name $key -Value $Changes[$key] -Force }
    $public | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $repository 'backup-manifest-public.json') -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $repository 'encrypted-backup-sha256.txt') -Value $HashLine -Encoding ASCII
    if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Mode VerifyDownloaded `
            -RepositoryDirectory $repository -SevenZipExecutable $probe -PythonExecutable (Join-Path $PSHOME 'powershell.exe') `
            -ExtractionDirectory (Join-Path $temporary 'unused-extraction') 2>&1 | Out-String
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    if ($code -eq 0 -or $output -notlike "*$Expected*" -or (Test-Path -LiteralPath $marker) -ne $ReachArchiver) { throw 'Synthetic public manifest rejection check failed.' }
    $script:checks++
}
try {
    Check-Rejection 'Downloaded archive test failed.' -ReachArchiver $true
    Check-Rejection 'unapproved fields' @{total_plaintext_bytes=42}
    Check-Rejection 'unapproved fields' @{included=@{source_runtime=$true; frozen_runtime=$true; docker_vhdx=$true; media=$true}}
    Check-Rejection 'unapproved fields' @{archive_part_count=1.5}
    Check-Rejection 'part count differs' @{archive_part_count=2}
    Check-Rejection 'encrypted total differs' @{archive_total_bytes=999}
    Check-Rejection 'encrypted total differs' @{archive_total_bytes=[long]2147483648}
    Check-Rejection 'missing archive volume' @{} ($hash + '  alfred-private-backup-20261006.7z.002')
    Check-Rejection 'Invalid archive hash record' @{} ($hash + '  ../db.sqlite3')
    Check-Rejection 'SHA256 differs' @{} (('0'*64) + '  ' + $name)
    [IO.File]::WriteAllText((Join-Path $repository 'unexpected.txt'), 'synthetic plaintext')
    Check-Rejection 'Unexpected plaintext or unlisted file'
    Write-Host "Synthetic public manifest/hash checks: $checks PASS. Operator data accessed: NO."
} finally {
    $resolved = [IO.Path]::GetFullPath($temporary)
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetFileName($resolved) -notmatch '^alfred-public-manifest-test-[a-f0-9]{32}$') { throw 'Refusing unsafe synthetic cleanup.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
