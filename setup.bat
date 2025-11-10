@echo off
echo.
echo UCOP Setup Script
echo ====================
echo.

REM Check Python version
echo Checking Python version...
python --version 2>nul
if errorlevel 1 (
    echo Python 3.8+ required
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

REM Create necessary directories
echo.
echo Creating directories...
if not exist "reports\" mkdir reports
if not exist "output\" mkdir output
if not exist "logs\" mkdir logs

REM Create .env if it doesn't exist
if not exist ".env" (
    echo.
    echo Creating .env from example...
    if exist ".env.example" (
        copy .env.example .env
        echo WARNING: Please edit .env with your API keys
    ) else (
        (
            echo # LLM Provider API Keys
            echo GEMINI_API_KEY=your_gemini_api_key_here
            echo OPENAI_API_KEY=your_openai_api_key_here
            echo.
            echo # GitHub (for Gist uploads^)
            echo GITHUB_TOKEN=your_github_token_here
            echo.
            echo # Ollama Configuration
            echo OLLAMA_HOST=http://localhost:11434
            echo OLLAMA_MODEL=qwen2.5:14b
            echo.
            echo # System Configuration
            echo LOG_LEVEL=INFO
            echo ENABLE_GPU=auto
            echo MAX_WORKERS=5
        ) > .env
        echo Created .env file - please edit with your API keys
    )
)

REM Check Ollama installation
echo.
echo Checking Ollama...
where ollama >nul 2>nul
if %errorlevel% equ 0 (
    echo Ollama is installed
) else (
    echo WARNING: Ollama not found
    echo Install from: https://ollama.ai
)

REM Run validation
echo.
echo Running system validation...
python tools\validate_imports.py
if %errorlevel% equ 0 (
    echo Import validation passed
) else (
    echo WARNING: Some imports failed - check logs
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Edit .env with your API keys
echo   2. Start Ollama if not running: ollama serve
echo   3. Pull Ollama model: ollama pull qwen2.5:14b
echo   4. Run CLI: python ucop_cli.py --help
echo   5. Start Web UI: python start_web.py
echo.

pause
