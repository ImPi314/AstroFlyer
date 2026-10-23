; Inno Setup Script for AstroFlyer HEO Standalone Desktop Application
; Department of Aerospace Engineering, ACS College of Engineering

#define MyAppName "AstroFlyer HEO"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ACS College of Engineering"
#define MyAppURL "https://github.com/Harshith-Aerospace/AstroFlyer-HEO"
#define MyAppExeName "AstroFlyer.exe"

[Setup]
AppId={{E68A9F12-78A3-4158-9A8C-28D69A5D843F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist_installer
OutputBaseFilename=AstroFlyer_HEO_v1.0_Setup
SetupIconFile=..\astroflyer\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=AstroFlyer HEO - Autonomous Flight Dynamics & Mission Planning Studio

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\AstroFlyer_HEO\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Technical Handbook (PDF)"; Filename: "{app}\THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
