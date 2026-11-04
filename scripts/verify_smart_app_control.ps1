<# Record what Smart App Control does to a signed ALFRED release on a CLEAN Windows 11 PC.
   Never run this on the development PC, and never turn Smart App Control off for it.
   It uses a disposable data folder inside EvidenceDirectory and only synthetic state.
   A valid signature is not proof: this writes what was observed, passed or not.

   1. -Phase Install -Installer <ALFRED-Setup.exe> [-Interactive]
   2. Restart Windows, then -Phase AfterRestart
   3. -Phase Uninstall #>
param(
    [Parameter(Mandatory=$true)][ValidateSet('Install','AfterRestart','Uninstall')][string]$Phase,
    [string]$Installer,
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'Programs\ALFRED'),
    [string]$EvidenceDirectory = (Join-Path $env:LOCALAPPDATA 'ALFRED-sac-evidence'),
    [switch]$Interactive
)
$ErrorActionPreference = 'Stop'
$started = Get-Date
$steps = [ordered]@{}
$temporary = @{}
$data = Join-Path $EvidenceDirectory 'data'
$launcher = Join-Path $InstallDir 'ALFRED Launcher.exe'
$native = Join-Path $InstallDir 'ALFRED.exe'
$uninstaller = Join-Path $InstallDir 'unins000.exe'

function Record([string]$Name, [string]$Observed, [string]$Detail = '') {
    $steps[$Name] = [ordered]@{ observed = $Observed; detail = $Detail }
    Write-Output "$Observed $Name $Detail"
}
function SignatureOf([string]$Path) {
    $s = Get-AuthenticodeSignature -LiteralPath $Path
    [ordered]@{ path = $Path; status = [string]$s.Status; signer = $(if ($s.SignerCertificate) { $s.SignerCertificate.Subject })
                timestamp_signer = $(if ($s.TimeStamperCertificate) { $s.TimeStamperCertificate.Subject }) }
}
function SnapshotTemporaryCode {
    # Inno documents signed self-copies; this records the ones really executed.
    foreach ($pattern in 'is-*.tmp', '_iu*.tmp', '_un*.tmp') {
        Get-ChildItem -Path (Join-Path $env:TEMP $pattern) -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
            if (-not $temporary.ContainsKey($_.FullName)) {
                try { $temporary[$_.FullName] = SignatureOf $_.FullName } catch { }
            }
        }
    }
}
function RunWatched([string]$Name, [string]$FilePath, [string[]]$Arguments) {
    # Windows refuses a blocked program when it is started, so this is an observation, not a script error.
    try { $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -PassThru }
    catch { Record $Name 'BLOCKED_OR_FAILED' $_.Exception.Message; return $false }
    while (-not $process.HasExited) { SnapshotTemporaryCode; Start-Sleep -Milliseconds 100 }
    if ($process.ExitCode -ne 0) { Record $Name 'FAILED' "exit code $($process.ExitCode)"; return $false }
    Record $Name 'PASSED'
    return $true
}
function ProveRuntime([string]$Prefix) {
    if (-not (RunWatched "${Prefix}_launcher_start" $launcher @('start', '--quiet', '--no-browser', '--data-dir', "`"$data`"", '--port', '8090'))) { return }
    $state = Get-Content -LiteralPath (Join-Path $data 'artifacts/native/runtime.json') -Raw | ConvertFrom-Json
    $health = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $state.port + '/health/native/')
    if ($health.status -eq 'ok') { Record "${Prefix}_health" 'PASSED' } else { Record "${Prefix}_health" 'FAILED' ([string]$health.status) }
    $alive = @($state.pid, $state.worker_pid | Where-Object { $_ } | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
    if ($alive.Count -ge 2) { Record "${Prefix}_background_processes" 'PASSED' "$($alive.Count) running" }
    else { Record "${Prefix}_background_processes" 'FAILED' "$($alive.Count) running" }
    [void](RunWatched "${Prefix}_stop" $native @('stop', '--data-dir', "`"$data`""))
}

# The kit carries the development PC's fingerprint; hashing a file keeps this usable in Constrained Language.
$manifestPath = Join-Path $PSScriptRoot 'acceptance-manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Run this from the release acceptance kit, beside acceptance-manifest.json.' }
$machineGuid = (Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid).MachineGuid
$guidFile = Join-Path $env:TEMP ('alfred-sac-' + $PID + '.txt')
Set-Content -LiteralPath $guidFile -Value $machineGuid -Encoding ASCII -NoNewline
try { $fingerprint = (Get-FileHash -LiteralPath $guidFile -Algorithm SHA256).Hash.ToLowerInvariant() }
finally { Remove-Item -LiteralPath $guidFile -Force }
if ((Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json).development_machine_fingerprint -eq $fingerprint) {
    throw 'This test requires a separate clean PC. This machine matches the development computer.'
}

$state = (Get-MpComputerStatus).SmartAppControlState
if ($state -ne 'On') { throw "Smart App Control state is '$state'. Enforcement evidence needs a clean PC where it is On; this script never changes it." }
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
$bootTime = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
$signatures = @()

if ($Phase -eq 'Install') {
    if (-not $Installer) { throw 'Install needs -Installer.' }
    $setup = (Resolve-Path -LiteralPath $Installer).Path
    $signatures += SignatureOf $setup
    $arguments = @("/LOG=`"$(Join-Path $EvidenceDirectory 'install.log')`"")
    if (-not $Interactive) { $arguments += '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS' }
    if (RunWatched 'setup_launches_and_installs' $setup $arguments) {
        foreach ($path in $launcher, $native, $uninstaller) { $signatures += SignatureOf $path }
        ProveRuntime 'first'
    }
    Set-Content -LiteralPath (Join-Path $EvidenceDirectory 'install-boot.txt') -Value $bootTime -Encoding ASCII
} elseif ($Phase -eq 'AfterRestart') {
    if ((Get-Content -LiteralPath (Join-Path $EvidenceDirectory 'install-boot.txt') -Raw).Trim() -eq $bootTime) { throw 'No Windows restart happened since Install.' }
    foreach ($path in $launcher, $native, $uninstaller) { $signatures += SignatureOf $path }
    ProveRuntime 'after_restart'
} else {
    $signatures += SignatureOf $uninstaller
    if (RunWatched 'uninstaller_launches' $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=`"$(Join-Path $EvidenceDirectory 'uninstall.log')`"")) {
        # Inno's first process exits before its temporary clone finishes.
        $deadline = (Get-Date).AddSeconds(60)
        while ((Test-Path -LiteralPath $native) -and (Get-Date) -lt $deadline) { SnapshotTemporaryCode; Start-Sleep -Milliseconds 100 }
        if (Test-Path -LiteralPath $native) { Record 'uninstall_completes' 'FAILED' 'Program files remain after 60 seconds.' } else { Record 'uninstall_completes' 'PASSED' }
    }
}

$events = @()
$eventError = $null
try {
    $events = @(Get-WinEvent -FilterHashtable @{ LogName = 'Microsoft-Windows-CodeIntegrity/Operational'; Id = 3033, 3034, 3076, 3077; StartTime = $started } -ErrorAction Stop |
        ForEach-Object { [ordered]@{ time = $_.TimeCreated.ToUniversalTime().ToString('o'); id = $_.Id; message = $_.Message } })
} catch [System.Exception] {
    if ($_.FullyQualifiedErrorId -notmatch 'NoMatchingEventsFound') { $eventError = $_.Exception.Message }
}
$failed = @($steps.Keys | Where-Object { $steps[$_].observed -ne 'PASSED' }).Count
[ordered]@{
    phase = $Phase; observed_at = (Get-Date).ToUniversalTime().ToString('o'); smart_app_control_state = $state
    windows = (Get-CimInstance Win32_OperatingSystem).Version; steps = $steps; signatures = $signatures
    temporary_code = @($temporary.Values); code_integrity_events = $events; code_integrity_read_error = $eventError
    all_steps_observed_passing = ($failed -eq 0 -and $steps.Count -gt 0)
    operator_note = 'Add screenshots of any Smart App Control or SmartScreen prompt to this folder.'
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $EvidenceDirectory ($Phase.ToLower() + '-observed.json')) -Encoding UTF8
Write-Output "Evidence written to $EvidenceDirectory. $failed step(s) did not pass; $($events.Count) CodeIntegrity event(s) recorded."
if ($failed) { exit 1 }
