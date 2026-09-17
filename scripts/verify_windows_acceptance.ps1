<# Run on a separate Windows x64 PC with the portable bundle or installed app.
   Fresh creates a disposable synthetic account. Reboot requires a real reboot.
   No Python, Docker, Administrator access or external API keys are used. #>
param(
    [Parameter(Mandatory=$true)][string]$Executable,
    [ValidateSet('Fresh','Reboot')][string]$Phase = 'Fresh',
    [string]$EvidenceDirectory = (Join-Path $env:LOCALAPPDATA 'ALFRED-acceptance')
)
$ErrorActionPreference = 'Stop'
$exePath = (Resolve-Path -LiteralPath $Executable).Path
$evidence = [IO.Path]::GetFullPath($EvidenceDirectory)
$data = Join-Path $evidence 'data'
$baselinePath = Join-Path $evidence 'baseline.json'
$boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')

function Invoke-Alfred([string]$Action) {
    $process = Start-Process -FilePath $exePath -ArgumentList ($Action + ' --data-dir "' + $data + '" --port 8080 --no-browser') -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(240000)) { throw 'ALFRED command timed out; inspect data/artifacts/native logs.' }
    if ($process.ExitCode -ne 0) { throw "ALFRED $Action failed with exit code $($process.ExitCode)." }
}

if ($Phase -eq 'Fresh') {
    if (Test-Path -LiteralPath $evidence) { throw 'Choose a new empty EvidenceDirectory; existing data will not be overwritten.' }
    New-Item -ItemType Directory -Path $evidence | Out-Null
    $baseline = [ordered]@{
        username = ('windows_proof_' + [guid]::NewGuid().ToString('N').Substring(0,8))
        password = 'AcceptanceOnly936!'
        boot = $boot
        executable_sha256 = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash
        host_context = 'Operator must separately confirm this is a clean second PC'
    }
} else {
    $baseline = Get-Content -LiteralPath $baselinePath -Raw | ConvertFrom-Json
    if ($baseline.boot -eq $boot) { throw 'No Windows reboot occurred since Fresh. Process restart is not reboot proof.' }
    if ($baseline.executable_sha256 -ne (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash) { throw 'Use the same executable for both phases.' }
}

try {
    Invoke-Alfred 'start'
    $state = Get-Content -LiteralPath (Join-Path $data 'artifacts/native/runtime.json') -Raw | ConvertFrom-Json
    $base = 'http://127.0.0.1:' + $state.port
    $health = Invoke-RestMethod -Uri ($base + '/health/native/')
    if ($health.status -ne 'ok' -or $health.instance -ne $state.instance) { throw 'Native health check failed.' }
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $entry = if ($Phase -eq 'Fresh') { '/signup/' } else { '/login/' }
    Invoke-WebRequest -Uri ($base + $entry) -WebSession $session -UseBasicParsing | Out-Null
    $csrf = $session.Cookies.GetCookies([uri]$base)['csrftoken'].Value
    $body = @{username=$baseline.username; csrfmiddlewaretoken=$csrf}
    if ($Phase -eq 'Fresh') {
        $body.password1=$baseline.password; $body.password2=$baseline.password
        $body.email=($baseline.username + '@example.test'); $body.first_name='Windows'; $body.last_name='Proof'
        $body.city='Test City'; $body.country='India'; $body.monthly_income='0'; $body.variable_income='0'; $body.rent_or_emi='0'
    } else { $body.password=$baseline.password }
    Invoke-WebRequest -Uri ($base + $entry) -Method Post -Body $body -WebSession $session -UseBasicParsing | Out-Null
    # Sign-up redirects to login in some versions; always establish an explicit session.
    $csrf = $session.Cookies.GetCookies([uri]$base)['csrftoken'].Value
    Invoke-WebRequest -Uri ($base + '/login/') -Method Post -Body @{username=$baseline.username; password=$baseline.password; csrfmiddlewaretoken=$csrf} -WebSession $session -UseBasicParsing | Out-Null
    if ($Phase -eq 'Fresh') {
        $headers = @{'X-CSRFToken'=$session.Cookies.GetCookies([uri]$base)['csrftoken'].Value}
        foreach ($transaction in @(
            @{amount=42000; category='income'; classification='other'; direction='credit'; description='Synthetic salary'},
            @{amount=1200; category='groceries'; classification='expense'; direction='debit'; description='Synthetic groceries'}
        )) {
            $transaction.transaction_date = (Get-Date -Format 'yyyy-MM-dd')
            Invoke-RestMethod -Uri ($base + '/api/expenses/') -Method Post -Body ($transaction | ConvertTo-Json) -ContentType 'application/json' -Headers $headers -WebSession $session | Out-Null
        }
        $baseline | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $baselinePath -Encoding UTF8
    }
    $summary = (Invoke-RestMethod -Uri ($base + '/api/expenses/dashboard/') -WebSession $session).summary
    if ([decimal]$summary.current_month_income -ne 42000 -or [decimal]$summary.current_month_expense -ne 1200 -or [decimal]$summary.current_month_net -ne 40800) { throw 'Saved financial totals do not match the entered data (run both phases in the same calendar month).' }
    $page = Invoke-WebRequest -Uri ($base + '/settings/') -WebSession $session -UseBasicParsing
    if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'Remove My Data') { throw 'Settings did not render as expected.' }
    [ordered]@{passed=$true; phase=$Phase; tested_at=(Get-Date).ToUniversalTime().ToString('o'); boot=$boot; previous_boot=$baseline.boot; executable_sha256=$baseline.executable_sha256; income=42000; expense=1200; remaining=40800; data_directory=$data; host_context=$baseline.host_context} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $evidence ($Phase.ToLower() + '-proof.json')) -Encoding UTF8
    Write-Output "PASS $Phase. Evidence: $evidence. Synthetic data retained for the reboot phase."
} finally {
    if (Test-Path -LiteralPath (Join-Path $data 'artifacts/native/runtime.json')) { Invoke-Alfred 'stop' }
}
