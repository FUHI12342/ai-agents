@echo off
SETLOCAL

SET REPO_DIR=%~dp0..
PUSHD %REPO_DIR%

IF EXIST "%REPO_DIR%\.venv\Scripts\activate.bat" (
    call "%REPO_DIR%\.venv\Scripts\activate.bat"
) ELSE (
    echo [WARN] .venv not found. Running without virtual environment.
)

python -m apps.compack.main --mode text --resume new
IF %ERRORLEVEL% NEQ 0 (
    echo Compack failed to start.
    pause
)

POPD
ENDLOCAL
