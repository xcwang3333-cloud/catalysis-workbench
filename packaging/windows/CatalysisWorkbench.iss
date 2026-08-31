#ifndef AppVersion
  #error AppVersion must be defined
#endif
#ifndef AppSource
  #error AppSource must be defined
#endif
#ifndef OutputDir
  #error OutputDir must be defined
#endif
#ifndef LicenseFile
  #error LicenseFile must be defined
#endif
#ifndef NoticesFile
  #error NoticesFile must be defined
#endif
#ifndef BuildProvenance
  #error BuildProvenance must be defined
#endif

#define AppName "CatalysisWorkbench"
#define AppExeName "CatalysisWorkbench.exe"

[Setup]
AppId={{0B3D9286-B8C8-4A66-9758-110C872B64FC}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=CatalysisWorkbench
DefaultDirName={localappdata}\Programs\CatalysisWorkbench
DefaultGroupName=CatalysisWorkbench
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=CatalysisWorkbench-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile={#LicenseFile}
UninstallDisplayName=CatalysisWorkbench {#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#LicenseFile}"; DestDir: "{app}"; DestName: "LICENSE"; Flags: ignoreversion
Source: "{#NoticesFile}"; DestDir: "{app}"; DestName: "THIRD_PARTY_NOTICES.txt"; Flags: ignoreversion
Source: "{#BuildProvenance}"; DestDir: "{app}"; DestName: "BUILD_PROVENANCE.json"; Flags: ignoreversion

[Icons]
Name: "{group}\CatalysisWorkbench"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall CatalysisWorkbench"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CatalysisWorkbench"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch CatalysisWorkbench"; Flags: nowait postinstall skipifsilent
