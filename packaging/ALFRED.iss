#ifndef BundleDir
  #define BundleDir "..\dist\ALFRED"
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\release"
#endif

[Setup]
AppId={{D4BFC620-610B-4AF7-81BF-215ECAC7297B}
AppName=ALFRED
AppVersion=1.0.1
AppPublisher=Life on our Trails
AppPublisherURL=https://sourabh48.github.io/alfred_ai/
AppSupportURL=https://github.com/sourabh48/alfred_ai/issues
AppCopyright=Copyright (c) 2026 Life on our Trails
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
SetupIconFile=..\static\alfred.ico
UninstallDisplayIcon={app}\ALFRED Launcher.exe
UninstallDisplayName=ALFRED
CloseApplications=no

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "windows\Uninstall ALFRED.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ALFRED"; Filename: "{app}\ALFRED Launcher.exe"; WorkingDir: "{app}"
Name: "{group}\Stop ALFRED"; Filename: "{app}\ALFRED Launcher.exe"; Parameters: "stop"; WorkingDir: "{app}"
Name: "{group}\Uninstall ALFRED"; Filename: "{uninstallexe}"; WorkingDir: "{app}"
Name: "{autodesktop}\ALFRED"; Filename: "{app}\ALFRED Launcher.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\ALFRED Launcher.exe"; Description: "Open ALFRED"; Flags: nowait postinstall skipifsilent

[Messages]
ConfirmUninstall=Remove %1 from this computer? Your saved accounts, documents and settings will be kept.
UninstalledAll=ALFRED was removed. Your saved accounts, documents and settings are still in your data folder.

[Code]
function StopAlfred: Boolean;
var ExitCode: Integer;
begin
  Result := True;
  if FileExists(ExpandConstant('{app}\ALFRED.exe')) then
    Result := Exec(ExpandConstant('{app}\ALFRED.exe'), 'stop', '', SW_HIDE,
      ewWaitUntilTerminated, ExitCode) and (ExitCode = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not StopAlfred then
    Result := 'ALFRED could not stop. Let background work finish, then retry the update.';
end;

function ContainsExecutable(Command, FileName: String): Boolean;
var FullPath, EscapedPath: String;
begin
  FullPath := ExpandConstant('{app}\') + FileName;
  EscapedPath := FullPath;
  StringChangeEx(EscapedPath, #39, #39 + #39, True);
  Result := (Pos(Lowercase(#34 + FullPath + #34), Lowercase(Command)) > 0) or
    (Pos(Lowercase(#39 + EscapedPath + #39), Lowercase(Command)) > 0);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var StartupCommand: String;
begin
  if CurUninstallStep = usUninstall then begin
    { This runs after confirmation, before any application files are removed. }
    if not StopAlfred then begin
      SuppressibleMsgBox('ALFRED could not stop. Let background work finish, then retry uninstall. No application files were removed.', mbError, MB_OK, IDOK);
      Abort;
    end;
  end;
  if CurUninstallStep = usPostUninstall then begin
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run',
      'ALFRED', StartupCommand) then
      if ContainsExecutable(StartupCommand, 'ALFRED.exe') or
        ContainsExecutable(StartupCommand, 'ALFRED Launcher.exe') then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'ALFRED');
  end;
end;
