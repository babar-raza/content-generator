@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo   UCOP - Unified Content Operations Platform
echo   Setup Script for Windows
echo ================================================================
echo.

REM Step 1: Check Python
echo [Step 1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Found Python %PYTHON_VERSION%

REM Check Python version >= 3.8
python -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" 2>nul
if errorlevel 1 (
    echo ERROR: Python 3.8 or higher is required
    pause
    exit /b 1
)

REM Step 2: Create virtual environment
echo.
echo [Step 2/6] Creating virtual environment...
if exist venv (
    echo WARNING: Virtual environment already exists
    choice /M "Recreate it"
    if !errorlevel! == 1 (
        echo Removing old venv...
        rmdir /s /q venv
        python -m venv venv
        echo [OK] Virtual environment recreated
    ) else (
        echo [OK] Using existing virtual environment
    )
) else (
    python -m venv venv
    echo [OK] Virtual environment created
)

REM Step 3: Activate virtual environment
echo.
echo [Step 3/6] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

REM Step 4: Upgrade pip
echo.
echo [Step 4/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded

REM Step 5: Install dependencies
echo.
echo [Step 5/6] Installing dependencies...
echo This may take a few minutes...
echo.

if exist requirements.txt (
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo WARNING: Some dependencies failed ^(optional packages^)
        echo Core packages should be installed. Check requirements.txt for optional packages.
    ) else (
        echo [OK] All dependencies installed
    )
) else (
    echo ERROR: requirements.txt not found
    pause
    exit /b 1
)

REM Step 6: Create directories
echo.
echo [Step 6/6] Creating project directories...
if not exist output mkdir output
if not exist data mkdir data
if not exist logs mkdir logs
if not exist checkpoints mkdir checkpoints
if not exist test_output mkdir test_output
if not exist reports mkdir reports
echo [OK] Project directories created

REM Create .env file if needed
if not exist .env (
    echo.
    echo Creating default .env file...
    if exist .env.example (
        copy .env.example .env >nul
        echo [OK] .env file created from .env.example
    ) else (
        (
        echo # UCOP Environment Configuration
        echo.
        echo # === LLM Configuration ===
        echo # Ollama ^(Local^)
        echo OLLAMA_HOST=http://localhost:11434
        echo OLLAMA_MODEL=qwen2.5:14b
        echo.
        echo # Google Gemini ^(Optional^)
        echo # GEMINI_API_KEY=your_api_key_here
        echo.
        echo # OpenAI ^(Optional^)
        echo # OPENAI_API_KEY=your_api_key_here
        echo.
        echo # === System Configuration ===
        echo LOG_LEVEL=INFO
        echo OUTPUT_DIR=./output
        echo DATA_DIR=./data
        echo.
        echo # === Feature Flags ===
        echo ENABLE_MESH_ORCHESTRATION=true
        echo ENABLE_VISUAL_ORCHESTRATION=true
        echo ENABLE_MCP_ENDPOINTS=true
        ) > .env
        echo [OK] Default .env file created
    )
    echo.
    echo WARNING: Edit .env file to configure API keys if needed
)

REM Validation
echo.
echo ================================================================
echo   Validation
echo ================================================================
echo.

echo Testing core imports...
python -c "import sys; import importlib; modules=[('Core Config','src.core.config'),('Core Template','src.core.template_registry'),('Mesh Runtime','src.mesh.runtime_async'),('Engine','src.engine.executor'),('Orchestration','src.orchestration.enhanced_registry')]; passed=0; failed=[]; [print(f'  [OK] {n}') if (importlib.import_module(m) or True) else (print(f'  [X] {n}') or failed.append(n)) for n,m in modules]; print(f'\nResult: {len(modules)-len(failed)}/{len(modules)} modules imported successfully'); failed and print(f'Failed: {chr(44).join(failed)}'); failed and print('\nNote: Some optional dependencies may not be installed.')"

if errorlevel 1 (
    echo WARNING: Some modules failed validation ^(may need optional dependencies^)
) else (
    echo [OK] Core modules validated
)

REM Final summary
echo.
echo ================================================================
echo   Setup Complete!
echo ================================================================
echo.
echo Python: %PYTHON_VERSION%
echo Virtual Environment: %CD%\venv
echo Configuration: .env
echo.
echo To activate the environment:
echo   venv\Scripts\activate
echo.
echo To run the CLI:
echo   python ucop_cli.py --help
echo.
echo To start the web UI:
echo   python start_web.py
echo.
echo To run tests:
echo   pytest tests\test_imports_smoke.py -v
echo.
echo For more information, see README.md
echo.

pause
