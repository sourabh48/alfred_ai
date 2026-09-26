<#
.SYNOPSIS
Register or remove ALFRED startup for the current Windows user.
.DESCRIPTION
Status is read-only and is the default. Enable starts ALFRED after Windows
sign-in, using the selected data folder without opening a browser. It does not
start a service before sign-in, restart Windows, or change the running app.
#>
[CmdletBinding()]
param(
    [ValidateSet('Status', 'Enable', 'Disable')]
    [string]$Action = 'Status',
    [string]$Executable,
    [string]$DataDirectory
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This script requires Windows.' }

$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$entryName = 'ALFRED'
$existing = (Get-ItemProperty -LiteralPath $runKey -Name $entryName -ErrorAction SilentlyContinue).$entryName

if ($Action -eq 'Status') {
    [pscustomobject]@{
        Registered = -not [string]::IsNullOrEmpty($existing)
        Trigger = 'Current Windows user sign-in'
        Command = $existing
    }
    return
}

$projectDirectory = Split-Path -Parent $PSScriptRoot
if (-not $Executable) { $Executable = Join-Path $projectDirectory 'dist\ALFRED\ALFRED.exe' }
if (-not $DataDirectory) { $DataDirectory = $projectDirectory }
$Executable = [System.IO.Path]::GetFullPath($Executable)
$DataDirectory = [System.IO.Path]::GetFullPath($DataDirectory)
$shell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

# Single-quoted PowerShell literals preserve spaces and special characters.
# The packaged executable uses a console, so its parent starts hidden too.
$literalExe = $Executable.Replace("'", "''")
$literalData = $DataDirectory.Replace("'", "''")
$launch = "& '$literalExe' start --data-dir '$literalData' --no-browser; exit `$LASTEXITCODE"
$command = '"{0}" -NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -Command "{1}"' -f $shell, $launch

if ($existing -and $existing -ne $command) {
    throw 'A different ALFRED startup command already exists. Inspect it with -Action Status before changing it.'
}

if ($Action -eq 'Disable') {
    if ($existing) { Remove-ItemProperty -LiteralPath $runKey -Name $entryName }
    Write-Output 'ALFRED automatic startup is disabled. The running app is unchanged.'
    return
}

if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw "Executable missing: $Executable" }
if (-not (Test-Path -LiteralPath $DataDirectory -PathType Container)) { throw "Data folder missing: $DataDirectory" }
if ($command.Length -gt 260) { throw 'Windows Run entries are limited to 260 characters. Use shorter executable/data paths.' }
if (-not (Test-Path -LiteralPath $runKey)) { New-Item -Path $runKey -Force | Out-Null }
New-ItemProperty -LiteralPath $runKey -Name $entryName -Value $command -PropertyType String -Force | Out-Null
if ((Get-ItemProperty -LiteralPath $runKey -Name $entryName).$entryName -ne $command) {
    throw 'The startup entry could not be verified.'
}
Write-Output "ALFRED startup registered for your next Windows sign-in. Data folder: $DataDirectory"
Write-Output 'If Windows Startup apps shows ALFRED as disabled, enable it there too.'
