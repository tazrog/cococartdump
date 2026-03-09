@echo off
setlocal

cd /d "%~dp0\.."

py scripts\make_windows_icon.py
if errorlevel 1 exit /b %errorlevel%

py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --icon scripts\coco.ico ^
  --name ccd ^
  tools\capture_coco_dump.py

if errorlevel 1 exit /b %errorlevel%

echo Build complete: %cd%\dist\ccd.exe
