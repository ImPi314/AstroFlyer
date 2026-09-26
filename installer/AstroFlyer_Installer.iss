; Inno Setup Script for AstroFlyer HEO - Flight Dynamics Studio & ECR-MF Certification Suite
; ACS College of Engineering | Aerospace Engineering Major Project (2025-2026)
; Candidates: Girish Gowda S, Gowtham N, Harshith S Purohith

#define MyAppName "AstroFlyer HEO Studio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ACS College of Engineering - Aerospace Engineering"
#define MyAppExeName "AstroFlyer_HEO_Studio.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".heo"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
AppId={{C7B8329E-B76F-42E1-9871-3AC7FA7CE281}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
ChangesAssociations=yes
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist_installer
OutputBaseFilename=AstroFlyer_HEO_Studio_Setup_v1.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\AstroFlyer_HEO_Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
