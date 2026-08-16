@echo off
setlocal

cd /d "%~dp0"
echo Building AI Exam Tutor installer...

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Install Python 3.12 or create .venv first.
    exit /b 1
)

%PYTHON% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller is not installed in the selected Python environment.
    echo Run: %PYTHON% -m pip install pyinstaller
    exit /b 1
)

echo [1/2] Building application with PyInstaller...
%PYTHON% -m PyInstaller --noconfirm --onedir --windowed ^
  --add-data "prompts;prompts" ^
  --add-data "app/database/schema.sql;app/database" ^
  --add-data "app/ui/views;app/ui/views" ^
  --add-data "translations;translations" ^
  --add-data "resources;resources" ^
  --collect-all PySide6 ^
  --collect-all mysql.connector ^
  --collect-all pygments ^
    --icon "resources\eduit-favicon.ico" ^
  --name "AI_Exam_Tutor" ^
  main.py
if errorlevel 1 (
    echo PyInstaller failed.
    exit /b 1
)

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
) else (
    echo Inno Setup 6 was not found.
    echo Install it from https://jrsoftware.org/isinfo.php
    exit /b 1
)

echo [2/2] Creating Windows installer...
"%ISCC%" ".\setup_script.iss"
if errorlevel 1 (
    echo Inno Setup failed.
    exit /b 1
)

echo.
echo Installer created successfully:
echo %CD%\Output_Installer\AI_Exam_Tutor_Setup.exe
exit /b 0