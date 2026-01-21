@echo off
SETLOCAL

SET REPO_DIR=%~dp0..
PUSHD %REPO_DIR%

IF EXIST "%REPO_DIR%\.venv\Scripts\activate.bat" (
    call "%REPO_DIR%\.venv\Scripts\activate.bat"
) ELSE (
    echo [WARN] .venv not found. Running without virtual environment.
)

IF NOT EXIST "%REPO_DIR%\.venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Please install web requirements:
    echo   pip install -r apps/compack/requirements-web.txt
    pause
    exit /b 1
)

python -m apps.compack.main --mode text --ui web --open-browser --resume new
IF %ERRORLEVEL% NEQ 0 (
    echo Compack web failed to start.
    pause
)

POPD
ENDLOCAL
