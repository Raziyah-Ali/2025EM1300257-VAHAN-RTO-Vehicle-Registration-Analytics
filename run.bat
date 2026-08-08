@echo off
REM ---------------------------------------------------------------------------
REM VAHAN Dashboard One-Click Launcher (Windows)
REM ---------------------------------------------------------------------------

echo ==================================================
echo  Starting VAHAN RTO Analytics Dashboard...
echo ==================================================

IF NOT EXIST "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

streamlit run app.py
pause
