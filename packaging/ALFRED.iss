#ifndef BundleDir
  #define BundleDir "..\dist\ALFRED"
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\dist"
#endif

[Setup]
AppId={{D4BFC620-610B-4AF7-81BF-215ECAC7297B}
AppName=ALFRED
AppVersion=1.0.0
AppPublisher=ALFRED
DefaultDirName={localappdata}\Programs\ALFRED
DefaultGroupName=ALFRED
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#ReleaseDir}
OutputBaseFilename=ALFRED-Setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\ALFRED Launcher.exe
CloseApplications=no

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ALFRED"; Filename: "{app}\ALFRED Launcher.exe"; WorkingDir: "{app}"
Name: "{group}\Stop ALFRED"; Filename: "{app}\ALFRED Launcher.exe"; Parameters: "stop"; WorkingDir: "{app}"
Name: "{autodesktop}\ALFRED"; Filename: "{app}\ALFRED Launcher.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\ALFRED Launcher.exe"; Description: "Open ALFRED"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\ALFRED.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopAlfred"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var ExitCode: Integer;
begin
  Result := '';
  if FileExists(ExpandConstant('{app}\ALFRED.exe')) then
    if not Exec(ExpandConstant('{app}\ALFRED.exe'), 'stop', '', SW_HIDE,
      ewWaitUntilTerminated, ExitCode) or (ExitCode <> 0) then
      Result := 'ALFRED is finishing a background job. Let it finish, then retry the update.';
end;
