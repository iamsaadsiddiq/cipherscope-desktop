#define MyAppName "CipherScope"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CipherScope contributors"
[Setup]
AppId={{51A83759-23C6-46F0-A39C-5D9C59E15E81}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CipherScope
DefaultGroupName=CipherScope
OutputDir=output
OutputBaseFilename=CipherScope-1.0.0-Windows-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\CipherScope.exe
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
[Files]
Source: "..\dist\CipherScope\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\CipherScope"; Filename: "{app}\CipherScope.exe"
Name: "{autodesktop}\CipherScope"; Filename: "{app}\CipherScope.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\CipherScope.exe"; Description: "Launch CipherScope"; Flags: nowait postinstall skipifsilent
