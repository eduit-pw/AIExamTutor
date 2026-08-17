; AI Exam Tutor — Inno Setup Script
; Builds a Windows installer (.exe) for the AI Exam Tutor application.
;
; Requirements:
;   - Inno Setup 6.2+
;   - Run from GitHub Actions (windows-latest) after PyInstaller produces dist/AI_Exam_Tutor
;   - Produces Output_Installer/AI_Exam_Tutor_Setup.exe
;
; Usage (local):
;   iscc setup_script.iss

#define AppName "AI Exam Tutor"
#define AppVersion "1.2.0"
#define AppPublisher "Pawel"
#define AppExeName "AI_Exam_Tutor.exe"
#define AppDirName "AIExamTutor"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
SetupIconFile=resources\eduit-favicon.ico
DefaultDirName={autopf}\{#AppDirName}
DefaultGroupName={#AppName}
OutputDir=Output_Installer
OutputBaseFilename=AI_Exam_Tutor_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Main executable and dependencies (produced by PyInstaller --onedir)
Source: "dist\AI_Exam_Tutor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; License notice (bundled in resources)
Source: "resources\exam_sheets\LICENSE_NOTICE.md"; DestDir: "{app}\resources\exam_sheets"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Registry]
; Associate .sql, .php, .html files with the app (optional)
; Root: HKCU; Subkey: "Software\Classes\.sql"; ValueType: string; ValueData: "AIExamTutor.sql"; Flags: uninsdeletekey
; Root: HKCU; Subkey: "Software\Classes\AIExamTutor.sql"; ValueType: string; ValueData: "SQL File"; Flags: uninsdeletekey
; Root: HKCU; Subkey: "Software\Classes\AIExamTutor.sql\DefaultIcon"; ValueType: string; ValueData: "{app}\icon.ico,0"; Flags: uninsdeletekey
; Root: HKCU; Subkey: "Software\Classes\AIExamTutor.sql\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey

[CustomMessages]
polish.InstallingFiles=Instalowanie plików...
polish.CreatingIcons=Tworzenie skrótów...
polish.FinishingInstallation=Zakończenie instalacji...
english.InstallingFiles=Installing files...
english.CreatingIcons=Creating shortcuts...
english.FinishingInstallation=Finishing installation...