<#
.SYNOPSIS
Complete native scheduled-work verification across Windows sign-ins.
.DESCRIPTION
Enable installs a separate, temporary current-user startup entry and launches
verification. Interrupted attempts are retained and replaced with fresh full
windows. A completed pass removes this startup entry. Disable cancels only
verification; ALFRED and its normal startup entry are left running.
#>
[CmdletBinding()]
param(
    [ValidateSet('Status', 'Enable', 'Run', 'Disable')]
    [string]$Action = 'Status',
    [string]$PythonExecutable
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$evidenceDirectory = Join-Path $projectDirectory 'artifacts\ops\continuous-observation'
$configPath = Join-Path $evidenceDirectory 'launcher-config.json'
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$entryName = 'ALFRED Verification'
$shell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$command = '"{0}" -NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{1}" -Action Run' -f $shell, $PSCommandPath
$existing = (Get-ItemProperty -LiteralPath $runKey -Name $entryName -ErrorAction SilentlyContinue).$entryName

if ($Action -eq 'Status') {
    $manifestPath = Join-Path $evidenceDirectory 'current.json'
    $manifest = if (Test-Path -LiteralPath $manifestPath) { Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json } else { $null }
    $status = if ($manifest) { $manifest.status } else { 'not_started' }
    $passed = $false
    if ($manifest -and $manifest.report -and (Test-Path -LiteralPath $manifest.report)) {
        $report = Get-Content -LiteralPath $manifest.report -Raw | ConvertFrom-Json
        $status, $passed = $report.status, $report.passed
        if ($status -eq 'observing' -and $report.samples.Count) {
            $age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $report.samples[-1].time
            if ($age -gt [Math]::Max(180, $report.interval_seconds * 3)) { $status = 'interrupted'; $passed = $false }
        }
    }
    [pscustomobject]@{Registered=($existing -eq $command); Status=$status; Passed=$passed; EvidenceDirectory=$evidenceDirectory; LatestAttempt=$manifest.report; ExpectedFinishUtc=$manifest.expected_finish}
    return
}

if ($existing -and $existing -ne $command) { throw 'A different verification startup entry exists; no changes made.' }

if ($Action -eq 'Disable') {
    if ($existing) { Remove-ItemProperty -LiteralPath $runKey -Name $entryName }
    New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $evidenceDirectory 'stop.requested') -Value 'User stopped verification.'
    Write-Output 'Verification will stop within one sampling interval. ALFRED remains running.'
    return
}

if ($Action -eq 'Enable') {
    if (-not $PythonExecutable -or -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) { throw 'Provide the configured project Python executable.' }
    if ($command.Length -gt 260) { throw 'Startup command exceeds the Windows Run limit.' }
    New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
    [pscustomobject]@{PythonExecutable=[IO.Path]::GetFullPath($PythonExecutable); DataDirectory=$projectDirectory; Executable=(Join-Path $projectDirectory 'dist\ALFRED\ALFRED.exe')} | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
    $stopFile = Join-Path $evidenceDirectory 'stop.requested'
    if (Test-Path -LiteralPath $stopFile) { Remove-Item -LiteralPath $stopFile }
    New-ItemProperty -LiteralPath $runKey -Name $entryName -Value $command -PropertyType String -Force | Out-Null
    Start-Process -FilePath $shell -ArgumentList ('-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -Action Run' -f $PSCommandPath) -WindowStyle Hidden | Out-Null
    Write-Output 'Verification enabled. Status and evidence are available through -Action Status.'
    return
}

$settings = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $settings.PythonExecutable -PathType Leaf)) { throw 'Configured Python is missing; update verification configuration.' }
$runLabel = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$arguments = '"{0}" --data-dir "{1}" --executable "{2}" --evidence-dir "{3}"' -f (Join-Path $PSScriptRoot 'complete_native_observation.py'), $settings.DataDirectory, $settings.Executable, $evidenceDirectory
$process = Start-Process -FilePath $settings.PythonExecutable -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $evidenceDirectory ($runLabel + '.log')) -RedirectStandardError (Join-Path $evidenceDirectory ($runLabel + '-error.log'))
# Retain the handle before waiting so Windows PowerShell preserves ExitCode.
$processHandle = $process.Handle
$process.WaitForExit()
$exitCode = $process.ExitCode
if ($null -eq $exitCode) { throw 'Verification process exited without a readable exit code; startup entry retained.' }
if ($exitCode -eq 0) {
    $current = (Get-ItemProperty -LiteralPath $runKey -Name $entryName -ErrorAction SilentlyContinue).$entryName
    if ($current -eq $command) { Remove-ItemProperty -LiteralPath $runKey -Name $entryName }
}
exit $exitCode
