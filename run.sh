#!/bin/bash
# ---------------------------------------------------------------------------
# VAHAN Dashboard One-Click Launcher (macOS / Linux)
# ---------------------------------------------------------------------------

echo "=================================================="
echo " Starting VAHAN RTO Analytics Dashboard...       "
echo "=================================================="

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Launch Streamlit
streamlit run app.py
