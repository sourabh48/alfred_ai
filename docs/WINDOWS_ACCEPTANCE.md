# Clean-PC and reboot acceptance

Use a separate Windows x64 computer with no project checkout, Python or Docker.
Copy the complete portable `dist/ALFRED` folder and
`scripts/verify_windows_acceptance.ps1`, or install `dist/ALFRED-Setup.exe` first.
An isolated folder on the development PC does not establish clean-PC acceptance.

Run in PowerShell, adjusting the executable path:

```powershell
.\verify_windows_acceptance.ps1 -Executable 'C:\ALFRED\ALFRED.exe' -Phase Fresh
```

This creates a separate synthetic account, inserts income of 42,000 and an
expense of 1,200, verifies 40,800 remaining through HTTP, and checks Settings.
It stops the test app and retains its data in `%LOCALAPPDATA%\ALFRED-acceptance`.
Choose `-EvidenceDirectory` with a new path for a repeat run.

Restart Windows normally after saving your other work. Then run:

```powershell
.\verify_windows_acceptance.ps1 -Executable 'C:\ALFRED\ALFRED.exe' -Phase Reboot
```

The second phase requires a changed Windows boot time and the same executable
hash. It signs back into the synthetic account and checks the same stored totals.
Perform both phases in the same calendar month. Neither phase restarts Windows
automatically. The app must be started after login; automatic startup is not
configured by this test.

Retain `fresh-proof.json` and `reboot-proof.json`, and record the Windows version,
whether Python/Docker were absent, installer versus portable use, and any prompts.
Also open the app with its test data folder and review the dashboard, upload an
anonymized checked document, use Settings, and test uninstall retention. Those
manual observations and a genuinely separate PC are needed to complete acceptance.

The local synthetic baseline contains a test password only. Do not use this
script against an existing account or production data folder.
