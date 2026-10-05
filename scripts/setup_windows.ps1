#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PythonExecutable,
    [string]$DataDirectory,
    [switch]$MigrateFresh
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
if (-not $DataDirectory) { $DataDirectory = $RepositoryRoot }
$RuntimeRoot = [IO.Path]::GetFullPath($DataDirectory)
$DatabasePath = Join-Path $RuntimeRoot 'db.sqlite3'
$NativeConfig = Join-Path $RuntimeRoot 'config/native.env'
$VenvPython = Join-Path $RepositoryRoot '.venv/Scripts/python.exe'

function Invoke-Python {
    param([string]$Executable, [string[]]$Arguments, [string]$InputCode)
    if ($InputCode) { $InputCode | & $Executable @Arguments } else { & $Executable @Arguments }
    if ($LASTEXITCODE -ne 0) { throw "Python command failed (exit $LASTEXITCODE). Setup stopped." }
}

# Refuse to replace a missing recovery key or migrate a retained database.
if ((Test-Path -LiteralPath $DatabasePath) -and -not (Test-Path -LiteralPath $NativeConfig -PathType Leaf)) {
    throw 'Existing database has no config/native.env. Restore its private configuration before setup.'
}
if ($MigrateFresh -and (Test-Path -LiteralPath $DatabasePath)) {
    throw '-MigrateFresh requires a data directory without db.sqlite3. Back up and review retained data separately.'
}

Push-Location $RepositoryRoot
try {
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        if (Test-Path -LiteralPath (Join-Path $RepositoryRoot '.venv')) {
            throw '.venv exists but its interpreter is missing. Review it before creating a replacement.'
        }
        if (-not $PythonExecutable) {
            $Launcher = Get-Command py.exe -ErrorAction SilentlyContinue
            if ($Launcher) {
                $PythonExecutable = Invoke-Python $Launcher.Source @('-3.12', '-') 'import sys; print(sys.executable)'
            } else {
                $Command = Get-Command python.exe -ErrorAction SilentlyContinue
                if (-not $Command) { throw 'Install 64-bit Python 3.12, or pass -PythonExecutable with its absolute path.' }
                $PythonExecutable = $Command.Source
            }
        }
        Invoke-Python $PythonExecutable @('-') 'import struct, sys; assert sys.version_info[:2] == (3, 12) and struct.calcsize("P") == 8, "ALFRED requires tested 64-bit Python 3.12"'
        Invoke-Python $PythonExecutable @('-m', 'venv', '.venv')
    }
    Invoke-Python $VenvPython @('-') 'import struct, sys; assert sys.version_info[:2] == (3, 12) and struct.calcsize("P") == 8, "Existing venv must use 64-bit Python 3.12"'
    foreach ($RelativePath in @('config', 'media', 'ml_models/alfred/model_registry', 'artifacts/native')) {
        New-Item -ItemType Directory -Path (Join-Path $RuntimeRoot $RelativePath) -Force | Out-Null
    }
    $SetupNative = @'
from contextlib import ExitStack
import subprocess
import sys
from pathlib import Path
from alfred_native import InstanceLock, configure

data = Path(sys.argv[1])
migrate = sys.argv[2] == "True"
repo = Path(sys.argv[3])

def guard_retained_data():
    if (data / "db.sqlite3").exists():
        if not (data / "config/native.env").is_file():
            raise SystemExit("Restore the retained database's private configuration before setup.")
        if migrate:
            raise SystemExit("Refusing fresh migration: db.sqlite3 now exists.")

with ExitStack() as locks:
    try:
        locks.enter_context(InstanceLock(data, "instance.lock"))
        locks.enter_context(InstanceLock(data, "worker.lock"))
    except OSError:
        raise SystemExit("Stop ALFRED and let its worker finish before installing dependencies.")
    guard_retained_data()
    for arguments in (("install", "--upgrade", "pip"),
                      ("install", "-r", str(repo / "requirements.txt")), ("check",)):
        subprocess.run([sys.executable, "-m", "pip", *arguments], check=True)
    local_config = data / "config/local.env"
    if not local_config.exists():
        example = (repo / "config/native.local.env.example").read_bytes()
        with local_config.open("xb") as target:
            target.write(example)
    guard_retained_data()
    configure(data)
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "check"])
    if migrate:
        execute_from_command_line(["manage.py", "migrate", "--noinput"])
'@
    Invoke-Python $VenvPython @('-', $RuntimeRoot, $MigrateFresh.IsPresent.ToString(), $RepositoryRoot) $SetupNative
    Write-Host 'Setup validated. Existing environment files were preserved; native.env is created only when absent.'
    if (-not $MigrateFresh) { Write-Host 'No migrations were requested. Native startup applies migrations; review/backup retained data before launch.' }
    $QuotedData = $RuntimeRoot.Replace("'", "''")
    Write-Host "Launch from the repository: .\.venv\Scripts\python.exe alfred_native.py start --data-dir '$QuotedData'"
} finally {
    Pop-Location
}
