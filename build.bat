@echo off
setlocal EnableExtensions

cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Failed to change directory to the project root.
    exit /b 1
)

set "SPEC_FILE=MarketplaceBot.spec"
set "BUILD_REQUIREMENTS=requirements-build.txt"
set "OUTPUT_EXE=dist\MarketplaceBot\MarketplaceBot.exe"
set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
    goto :python_ready
)

if defined VIRTUAL_ENV (
    if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
        set "PYTHON_EXE=%VIRTUAL_ENV%\Scripts\python.exe"
        goto :python_ready
    )
)

for %%I in (py.exe) do if not "%%~$PATH:I"=="" (
    set "PYTHON_EXE=%%~$PATH:I"
    set "PYTHON_ARGS=-3"
    goto :python_ready
)

for %%I in (python.exe) do if not "%%~$PATH:I"=="" (
    set "PYTHON_EXE=%%~$PATH:I"
    goto :python_ready
)

echo [ERROR] Python 3 was not found.
echo Activate a virtual environment or install Python, then try again.
exit /b 1

:python_ready
if not exist "%SPEC_FILE%" (
    echo [ERROR] Spec file not found: %SPEC_FILE%
    exit /b 1
)

if not exist "%BUILD_REQUIREMENTS%" (
    echo [ERROR] Build requirements file not found: %BUILD_REQUIREMENTS%
    exit /b 1
)

"%PYTHON_EXE%" %PYTHON_ARGS% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not available in the selected environment.
    echo Install build dependencies with:
    echo   "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r %BUILD_REQUIREMENTS%
    exit /b 1
)

echo ========================================
echo Building MarketplaceBot
echo ========================================
echo Python : %PYTHON_EXE% %PYTHON_ARGS%
echo Spec   : %SPEC_FILE%
echo.

if exist "build" (
    rmdir /s /q "build"
)

if exist "dist\MarketplaceBot" (
    rmdir /s /q "dist\MarketplaceBot"
)

"%PYTHON_EXE%" %PYTHON_ARGS% -m PyInstaller --clean --noconfirm "%SPEC_FILE%"
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed.
    exit /b 1
)

if not exist "%OUTPUT_EXE%" (
    echo.
    echo [ERROR] Build finished without the expected file:
    echo         %OUTPUT_EXE%
    exit /b 1
)

echo.
echo [OK] Build completed successfully.
echo Output: %OUTPUT_EXE%
exit /b 0
