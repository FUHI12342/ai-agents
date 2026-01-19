@echo off
SETLOCAL
SET REPO_DIR=%~dp0\..\..\..\..
PUSHD %REPO_DIR%

IF EXIST "%REPO_DIR%\.venv\Scripts\activate.bat" (
    call "%REPO_DIR%\.venv\Scripts\activate.bat"
) ELSE (
    echo [WARN] .venv not found. Run setup_windows.ps1 if you need audio/web features.
)

python -m apps.compack.main --ui web --open-browser
IF %ERRORLEVEL% NEQ 0 (
    echo Compack failed to start.
    pause
)

POPD
ENDLOCAL
