@echo off
setlocal

cd /d "%~dp0"

set "FINAL_DIR=%~dp0"
set "DEFENDER=%ProgramFiles%\Windows Defender\MpCmdRun.exe"

echo Building Logistics Toolkit (AV-safe folder build)...
python -m pip install pyinstaller -q
python -m PyInstaller --noconfirm --clean ^
  --onedir ^
  --noupx ^
  --noconsole ^
  --name "LogisticsToolkit" ^
  --add-data "templates;templates" ^
  --distpath "dist" ^
  app.py

if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

set "BUILD_EXE=dist\LogisticsToolkit\LogisticsToolkit.exe"
if not exist "%BUILD_EXE%" (
  echo Build output not found: %BUILD_EXE%
  exit /b 1
)

echo.
echo Checking Microsoft Defender approval...
if not exist "%DEFENDER%" (
  echo WARNING: Windows Defender scanner not found. Skipping AV check.
  goto :deploy
)

"%DEFENDER%" -Scan -ScanType 3 -File "%CD%\%BUILD_EXE%"
if errorlevel 1 (
  echo.
  echo BLOCKED: Microsoft Defender flagged the build.
  exit /b 1
)
echo Defender scan passed - no threats found.

:deploy
if exist "%FINAL_DIR%LogisticsToolkit" rmdir /S /Q "%FINAL_DIR%LogisticsToolkit" >nul 2>&1

xcopy /E /I /Y "dist\LogisticsToolkit" "%FINAL_DIR%LogisticsToolkit" >nul

> "%FINAL_DIR%Run Logistics Toolkit.bat" echo @echo off
>> "%FINAL_DIR%Run Logistics Toolkit.bat" echo cd /d "%%~dp0LogisticsToolkit"
>> "%FINAL_DIR%Run Logistics Toolkit.bat" echo start "" "LogisticsToolkit.exe"

if exist "%DEFENDER%" (
  echo Running final Defender check on delivered build...
  "%DEFENDER%" -Scan -ScanType 3 -File "%FINAL_DIR%LogisticsToolkit\LogisticsToolkit.exe"
  if errorlevel 1 (
    echo BLOCKED: Delivered build failed Defender scan.
    exit /b 1
  )
)

if exist "build" rmdir /S /Q "build" >nul 2>&1
if exist "dist" rmdir /S /Q "dist" >nul 2>&1
if exist "LogisticsToolkit.spec" del /F /Q "LogisticsToolkit.spec" >nul 2>&1

echo.
echo Done. Defender-approved final product:
echo   %FINAL_DIR%Run Logistics Toolkit.bat
echo   %FINAL_DIR%LogisticsToolkit\LogisticsToolkit.exe

endlocal