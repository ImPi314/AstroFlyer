; Inno Setup Script for AstroFlyer HEO Standalone Desktop Application
; Department of Aerospace Engineering, ACS College of Engineering

#define MyAppName "AstroFlyer HEO"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ACS College of Engineering"
#define MyAppURL "https://github.com/ImPi314/AstroFlyer"
#define MyAppExeName "AstroFlyer.exe"

[Setup]
AppId={{E68A9F12-78A3-4158-9A8C-28D69A5D843F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Per-user install (PrivilegesRequired=lowest): {autopf} resolves to %LOCALAPPDATA%\Programs, no admin prompt
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
; Optional offline WebView2 runtime (put Microsoft's Evergreen Standalone x64 installer in installer\redist\)
Source: "redist\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist; Check: not IsWebView2Installed

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2 Runtime..."; Flags: skipifdoesntexist; Check: not IsWebView2Installed
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2ClientKey = 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasWebView2Version(RootKey: Integer; SubKey: String): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(RootKey, SubKey, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
end;

// WebView2 ships with Windows 11 and current Windows 10; this catches older or stripped-down installs
function IsWebView2Installed: Boolean;
begin
  Result := HasWebView2Version(HKLM, 'SOFTWARE\WOW6432Node\' + WebView2ClientKey) or
            HasWebView2Version(HKLM, 'SOFTWARE\' + WebView2ClientKey) or
            HasWebView2Version(HKCU, 'Software\' + WebView2ClientKey);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and not IsWebView2Installed then
    SuppressibleMsgBox('AstroFlyer needs the Microsoft Edge WebView2 Runtime, which was not found on this PC.' + #13#10 +
           'Install it from Microsoft (Evergreen Standalone Installer, x64), then start AstroFlyer.' + #13#10 +
           'Until then AstroFlyer opens in your web browser instead.', mbInformation, MB_OK, IDOK);
end;
