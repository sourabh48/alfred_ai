# Clean-PC and reboot acceptance

Use a separate Windows x64 computer with no project checkout, Python or Docker.
Extract `ALFRED-Windows-x64.zip` or install `ALFRED-Setup.exe` from the
release folder first.
An isolated folder on the development PC does not establish clean-PC acceptance.

The release folder contains the installer, both phase launchers, instructions
and an acceptance manifest. Copy the complete folder. Its manifest rejects
the development PC and an executable
whose hash differs from the supplied release. Reboot proof also records the
machine fingerprint and rejects a different PC from the Fresh phase.

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
Use [Human acceptance checks](MANUAL_ACCEPTANCE.md) to record Windows sign-in,
screen-reader, keyboard and document observations.

The local synthetic baseline contains a test password only. Do not use this
script against an existing account or production data folder.
