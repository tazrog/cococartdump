@echo off
setlocal

cd /d "%~dp0\.."

set "DIST_EXE=%cd%\dist\ccd.exe"
set "INSTALL_DIR=%LocalAppData%\Programs\cococartdump"
set "TARGET_EXE=%INSTALL_DIR%\ccd.exe"
set "TARGET_ICON=%INSTALL_DIR%\coco.ico"
set "SHORTCUT=%AppData%\Microsoft\Windows\Start Menu\Programs\cococartdump.lnk"

if not exist "%DIST_EXE%" (
  echo Missing %DIST_EXE%
  echo Build it first with scripts\build_windows.bat
  exit /b 1
)

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /Y "%DIST_EXE%" "%TARGET_EXE%" >nul
if exist "scripts\coco.ico" copy /Y "scripts\coco.ico" "%TARGET_ICON%" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; " ^
  "$Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); " ^
  "$Shortcut.TargetPath = '%TARGET_EXE%'; " ^
  "$Shortcut.IconLocation = '%TARGET_ICON%'; " ^
  "$Shortcut.WorkingDirectory = '%USERPROFILE%'; " ^
  "$Shortcut.Save()"

if errorlevel 1 exit /b %errorlevel%

echo Installed:
echo   Executable: %TARGET_EXE%
echo   Icon: %TARGET_ICON%
echo   Start Menu shortcut: %SHORTCUT%
