# VAHAN RTO Vehicle Registration Analytics

**Author:** Raziyah Ali  
**Repository:** [https://github.com/Raziyah-Ali/2025EM1300257-VAHAN-RTO-Vehicle-Registration-Analytics](https://github.com/Raziyah-Ali/2025EM1300257-VAHAN-RTO-Vehicle-Registration-Analytics)

An interactive, executive-level Streamlit analytics dashboard and data pipeline built for Indian VAHAN RTO vehicle registration data (2018–2024).

---


## Quick Start

Run the dashboard from the project directory:

### Option A: Launcher Scripts (Recommended)
* **macOS / Linux:**
  ```bash
  ./run.sh
  ```
* **Windows:**
  ```cmd
  run.bat
  ```

### Option B: Manual Setup
```bash
# 1. Activate environment
source venv/bin/activate    # macOS / Linux
# venv\Scripts\activate     # Windows

# 2. Install dependencies (if needed)
pip install -r requirements.txt

# 3. Launch dashboard
streamlit run app.py
```

The interactive dashboard opens automatically at **`http://localhost:8501`**.

---

## Repository Structure

```text
DVS/
├── README.md                              # Project documentation & run guide
├── run.sh                                 # Launcher script for macOS/Linux
├── run.bat                                # Launcher script for Windows
├── requirements.txt                        # Python dependencies
├── pyproject.toml                          # Project configuration
├── app.py                                 # Main Streamlit Dashboard Application
├── data/
│   ├── VAHAN_Dataset.xlsx                 # Consolidated Excel workbook (cleansed + raw)
│   ├── raw/
│   │   └── India_VAHAN_Dataset.csv        # Original raw dataset
│   └── processed/
│       ├── VAHAN_Dataset_Completely_Cleaned.csv     # Cleaned dataset
│       └── VAHAN_Dataset_Fully_Corrected_Issues.csv # Main dataset powering dashboard
└── notebooks/
    ├── 01_Data_Cleaning_Exploration.ipynb  # Data exploration & cleaning routines
    └── 02_Metrics_Calculation.ipynb       # CFAR & Herfindahl FMI calculation routines
```

---

## Core Business Metrics & Architecture

### Key Metrics
1. **Clean Fuel Adoption Rate (CFAR %):** Share of registered vehicles using clean powertrains (**Electric**, **CNG**, **Hybrid**).
2. **Fuel Mix Index (FMI):** Herfindahl-Hirschman Diversity score ($1 - \sum s_i^2$) measuring powertrain diversification (0.0 to ~0.75+).
3. **Fleet Compliance Share (%):** Share of vehicles satisfying compound compliance rules (**BS6/ZEV** emission norm AND vehicle age $\le$ 15 years).

### Dashboard Layout
- **Tab 1: Macro Fuel Transition:** Macro adoption trends, CFAR regional rankings, fuel market share trajectory, annual volume, and net basis-point shifts.
- **Tab 2: OEM & Powertrain Strategy:** OEM performance metrics, 4-quadrant scatter matrix (CFAR × Herfindahl FMI diversity), year-over-year OEM market share trends, stacked OEM fuel mix, and engine capacity (CC) distribution.
- **Tab 3: Regulatory & Data Quality Audit:** Fleet scrappage risk heatmap, non-compliant vehicle risk table with CSV export, data hygiene score %, and RTO error rate ranking.
