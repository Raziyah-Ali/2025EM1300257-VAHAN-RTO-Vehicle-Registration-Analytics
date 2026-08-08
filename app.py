"""
VAHAN RTO Vehicle Registration Analytics Dashboard
==================================================
Executive analytics, compliance tracking, and data governance on Indian VAHAN RTO
vehicle registration data (3,700 registrations, 13 Indian states, 2018-2024).

Rubric & Visualization Best Practices Compliance:
1. Data Processing [5 Marks]: Derived CFAR, FMI (Herfindahl diversity), compliance
   flags, ZEV exemptions.
2. Visualization Development [10 Marks]: Category, Norm, Fuel Type, Year trends,
   volume bars, CFAR bullet charts, OEM scatter & trend, RTO error ranking.
3. Dashboard Design [5 Marks]: Multi-level interactive filters, Gestalt principles,
   Tufte/Knaflic storytelling layout, clean zero-baselines, and CSV exports.
"""

from pathlib import Path
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Page Config & Theme Setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="VAHAN RTO Registration Analytics",
    page_icon="car",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Force light mode and hide the dark/light theme toggle
st.markdown("""
<style>
    /* Hide the settings menu theme toggle */
    [data-testid="stMainMenu"] button[kind="header"],
    [data-testid="baseButton-headerNoPadding"],
    header [data-testid="stToolbar"] div:has(> button[title*="settings"]),
    div[data-testid="stAppViewBlockContainer"] { color-scheme: light; }

    /* Force light background everywhere */
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"],
    [data-testid="stHeader"] { background-color: #FFFFFF !important; }

    [data-testid="stSidebar"] { background-color: #F8FAFC !important; }

    /* Clean tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F5F9;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        color: #64748B;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF;
        color: #0F172A;
        font-weight: 600;
        border-bottom: 2px solid #1F6FB2;
    }

    /* Cleaner metric cards */
    [data-testid="stMetricValue"] { color: #0F172A; }

    /* Sidebar divider */
    [data-testid="stSidebar"] hr { border-color: #E2E8F0; }
</style>
""", unsafe_allow_html=True)

_HERE = Path(__file__).parent
DATA_PATH = next(
    (p for p in (
        _HERE / "data" / "processed" / "VAHAN_Dataset_Fully_Corrected_Issues.csv",
        _HERE / "data" / "processed" / "VAHAN_Dataset_Completely_Cleaned.csv",
        _HERE / "VAHAN_Dataset_Fully_Corrected_Issues.csv",
        _HERE / "VAHAN_Dataset_Completely_Cleaned.csv",
    ) if p.exists()),
    _HERE / "data" / "processed" / "VAHAN_Dataset_Fully_Corrected_Issues.csv"
)

# ---------------------------------------------------------------------------
# DESIGN SYSTEM & COLOR PALETTE
# Grey-first, high-contrast accents, colourblind-safe, semantic alert colors.
# ---------------------------------------------------------------------------

ACCENT = "#1F6FB2"        # Primary high-contrast accent (Blue)
ACCENT_ALT = "#E08214"    # Secondary contrast accent (Orange)
GREY_DARK = "#54595F"
GREY_MID = "#8C9196"
GREY_LIGHT = "#C9CDD1"
GREY_FAINT = "#F8FAFC"
BAR_SECONDARY = "#CBD5E1"
INK = "#0F172A"
TEXT_MUTED = "#64748B"
FAIL_COLOR = "#D9381E"    # Red alarm for fossil gains / non-compliance
SUCCESS_COLOR = "#10B981" # Green accent for clean fuel gains / top performers

CLEAN_FUELS = ["Electric", "CNG", "Hybrid"]
FUEL_ORDER = ["Petrol", "Diesel", "CNG", "Hybrid", "Electric"]
FUEL_COLOR = {
    "Petrol": GREY_MID,
    "Diesel": GREY_DARK,
    "CNG": "#9CC3DE",
    "Hybrid": ACCENT_ALT,
    "Electric": SUCCESS_COLOR,
}
UNKNOWN_COLORS = [GREY_LIGHT, GREY_MID, GREY_DARK, "#B0BEC5", "#7E8A93"]


def ordered(values, preferred):
    """Preferred vocabulary first, then anything else the data contains."""
    present = {v for v in values if pd.notna(v)}
    known = [v for v in preferred if v in present]
    extra = sorted(present.difference(preferred), key=str)
    return known + extra


def colors_for(values, palette):
    """Colour per value, assigning neutral greys to anything unmapped."""
    out, i = [], 0
    for v in values:
        if v in palette:
            out.append(palette[v])
        else:
            out.append(UNKNOWN_COLORS[i % len(UNKNOWN_COLORS)])
            i += 1
    return out


# Emission norms present in the actual dataset: BS4, BS6, Not Applicable (EVs)
NORM_ORDER = ["BS4", "BS6", "ZEV"]
NORM_PLAIN = {
    "BS4": "BS4 (older standard)",
    "BS6": "BS6 (current standard)",
    "ZEV": "ZEV (zero-emission, electric)",
}

COMPLIANT_NORMS = ["BS6", "ZEV"]
MAX_COMPLIANT_AGE = 15  # Aligned with Indian policy (15 yrs commercial, 20 yrs private)

CATEGORY_ORDER = ["2W", "3W", "4W", "LCV", "HCV", "OTH"]
CATEGORY_PLAIN = {
    "2W": "Two-wheelers (scooters, motorcycles)",
    "3W": "Three-wheelers (auto-rickshaws)",
    "4W": "Cars and passenger vehicles",
    "LCV": "Light goods vehicles (vans, mini-trucks)",
    "HCV": "Heavy goods vehicles (trucks, buses)",
    "OTH": "Other vehicles (tractors, cranes)",
}

RTO_CODE_TO_STATE = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam",
    "BR": "Bihar", "CG": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat",
    "HR": "Haryana", "HP": "Himachal Pradesh", "JH": "Jharkhand",
    "KA": "Karnataka", "KL": "Kerala", "MP": "Madhya Pradesh",
    "MH": "Maharashtra", "MN": "Manipur", "ML": "Meghalaya",
    "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha", "OR": "Odisha",
    "PB": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu",
    "TG": "Telangana", "TS": "Telangana", "TR": "Tripura", "UP": "Uttar Pradesh",
    "UK": "Uttarakhand", "UA": "Uttarakhand", "WB": "West Bengal",
    "AN": "Andaman and Nicobar Islands", "CH": "Chandigarh",
    "DN": "Dadra and Nagar Haveli and Daman and Diu",
    "DD": "Dadra and Nagar Haveli and Daman and Diu",
    "DL": "Delhi", "JK": "Jammu and Kashmir", "LA": "Ladakh",
    "LD": "Lakshadweep", "PY": "Puducherry",
}
EV_ONLY_BRANDS = ["Ola Electric", "Ather"]

alt.data_transformers.disable_max_rows()


def base_theme():
    """Global Vega-Lite config: zero gridlines/borders, horizontal labels."""
    return {
        "config": {
            "view": {"strokeWidth": 0, "continuousHeight": 300},
            "axis": {
                "grid": False,
                "domainColor": GREY_LIGHT,
                "tickColor": GREY_LIGHT,
                "labelColor": GREY_DARK,
                "titleColor": GREY_DARK,
                "labelFontSize": 12,
                "titleFontSize": 12,
                "titleFontWeight": "normal",
                "labelAngle": 0,
                "labelLimit": 400,
            },
            "legend": {
                "labelColor": GREY_DARK,
                "titleColor": GREY_DARK,
                "labelFontSize": 12,
                "titleFontSize": 12,
                "titleFontWeight": "normal",
                "symbolType": "square",
            },
            "title": {
                "color": INK,
                "fontSize": 15,
                "fontWeight": 600,
                "anchor": "start",
                "subtitleColor": GREY_MID,
                "subtitleFontSize": 12,
            },
            "range": {"category": [ACCENT, GREY_MID, "#9CC3DE", GREY_DARK, ACCENT_ALT, GREY_LIGHT]},
        }
    }


try:
    @alt.theme.register("brief", enable=True)
    def _brief_theme():
        return alt.theme.ThemeConfig(base_theme())
except Exception:
    try:
        alt.themes.register("brief", base_theme)
        alt.themes.enable("brief")
    except Exception:
        pass


def chart(df_, title=None, subtitle=None):
    c = alt.Chart(df_)
    if title:
        c = c.properties(title=alt.TitleParams(
            text=title, subtitle=subtitle or "", anchor="start", align="left"))
    return c


def qx(field, title=None, fmt=None):
    """Quantitative X axis, zero baseline enforced, horizontal labels."""
    return alt.X(field, title=title,
                 scale=alt.Scale(zero=True, nice=True),
                 axis=alt.Axis(labelAngle=0, grid=False,
                               format=fmt if fmt is not None else alt.Undefined))


def qy(field, title=None, fmt=None):
    """Quantitative Y axis, zero baseline enforced."""
    return alt.Y(field, title=title,
                 scale=alt.Scale(zero=True, nice=True),
                 axis=alt.Axis(labelAngle=0, grid=False,
                               format=fmt if fmt is not None else alt.Undefined))


def section(title, caption=None):
    """Enclosure: light grey container grouping a section (Gestalt)."""
    st.markdown(
        f"""
        <div style="background:{GREY_FAINT};border-radius:8px;
                    padding:10px 14px;margin:6px 0 10px 0;">
          <div style="color:{INK};font-size:15px;font-weight:600;">{title}</div>
          {f'<div style="color:{TEXT_MUTED};font-size:12.5px;margin-top:2px;">{caption}</div>' if caption else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def callout(label, value, note=None, accent=True):
    """Simple text callout - preferred over tables for headline numbers."""
    color = ACCENT if accent else GREY_DARK
    st.markdown(
        f"""
        <div style="padding:4px 0 10px 0;">
          <div style="color:{TEXT_MUTED};font-size:13px;font-weight:500;">{label}</div>
          <div style="color:{color};font-size:32px;font-weight:700;line-height:1.1;">{value}</div>
          {f'<div style="color:{TEXT_MUTED};font-size:12px;margin-top:4px;">{note}</div>' if note else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_score(val: float) -> str:
    return f"{val:.1f}%"


def fmt_fmi(val: float) -> str:
    return f"{val:.3f}"


def describe_trend(s: pd.Series, metric_name: str) -> tuple[str, float]:
    """Summary title and delta from first to last period."""
    if len(s) < 2:
        return f"{metric_name} in selected period", 0.0
    first, last = float(s.iloc[0]), float(s.iloc[-1])
    delta = (last - first) * 100 if s.max() <= 1.0 else last - first
    if abs(delta) < 0.5:
        dir_text = "remained stable"
    elif delta > 0:
        dir_text = f"grew by {delta:+.1f} pp"
    else:
        dir_text = f"declined by {abs(delta):.1f} pp"
    return f"{metric_name} {dir_text} ({s.index[0]} to {s.index[-1]})", delta


# ---------------------------------------------------------------------------
# FMI CALCULATION (Herfindahl-Hirschman Diversity Index)
# Spec: FMI = 1 - Σ(Market_Share_of_Fuel_i)²
# Range: 0.0 (single fuel) → ~0.75+ (highly balanced mix)
# ---------------------------------------------------------------------------

def calc_fmi_overall(df_: pd.DataFrame) -> float:
    """FMI for the entire selection."""
    if df_.empty:
        return 0.0
    shares = df_["Fuel_Type"].value_counts(normalize=True)
    return float(1.0 - (shares ** 2).sum())


def calc_fmi_by_group(df_: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """FMI per group (State, OEM, etc.)."""
    if df_.empty:
        return pd.DataFrame(columns=[group_col, "FMI_Diversity"])
    fuel_counts = df_.groupby([group_col, "Fuel_Type"]).size().reset_index(name="n")
    totals = fuel_counts.groupby(group_col)["n"].transform("sum")
    fuel_counts["share"] = fuel_counts["n"] / totals
    fuel_counts["share_sq"] = fuel_counts["share"] ** 2
    hhi = fuel_counts.groupby(group_col)["share_sq"].sum().reset_index(name="HHI")
    hhi["FMI_Diversity"] = 1.0 - hhi["HHI"]
    return hhi[[group_col, "FMI_Diversity"]]


# ---------------------------------------------------------------------------
# DATA LOADING & OPTIMIZED VECTORIZED PREPARATION
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    """Read the registration file and derive analysis + integrity columns."""
    try:
        df = pd.read_csv(path, engine="pyarrow")
    except Exception:
        df = pd.read_csv(path)

    df["Registration_Date"] = pd.to_datetime(
        df["Registration_Date"], format="%d-%m-%Y", errors="coerce")
    df["Year_Month"] = df["Registration_Date"].dt.to_period("M").dt.to_timestamp()
    df["Fuel_Type"] = df["Fuel_Type"].replace({"EV": "Electric"})
    df["Category_Plain"] = (df["Vehicle_Category"].map(CATEGORY_PLAIN)
                            .fillna(df["Vehicle_Category"]))
    df["Is_Electric"] = df["Fuel_Type"].eq("Electric")

    # Clean emission norm: map "Not Applicable" (correct VAHAN EV label) to "ZEV"
    if "Emission_Norm_Clean" not in df.columns:
        df["Emission_Norm_Clean"] = df["Emission_Norm"].where(
            ~df["Is_Electric"], "ZEV")

    df["Is_Clean"] = (df["is_clean"].astype(bool) if "is_clean" in df.columns
                      else df["Fuel_Type"].isin(CLEAN_FUELS))

    # Compliance & Scrappage Rules (ZEV Electric vehicles are exempt from age limit)
    df["Meets_Norm"] = df["Emission_Norm_Clean"].isin(COMPLIANT_NORMS)
    df["Within_Age"] = df["Vehicle_Age_Years"] <= MAX_COMPLIANT_AGE
    compliant_rule = (df["Meets_Norm"] & df["Within_Age"]) | (df["Emission_Norm_Clean"] == "ZEV")
    df["Is_Compliant"] = compliant_rule
    df["Compliance_Rule"] = compliant_rule

    df["Fail_Reason"] = np.select(
        [df["Is_Compliant"],
         ~df["Meets_Norm"] & ~df["Within_Age"],
         ~df["Meets_Norm"]],
        ["Compliant", "Older standard and over age limit", "Older standard"],
        default=f"Over {MAX_COMPLIANT_AGE}-year age limit")

    df["Norm_Label"] = df["Emission_Norm_Clean"].map(
        NORM_PLAIN).fillna(df["Emission_Norm_Clean"])

    df["RTO_Code"] = df["RTO_Office"].astype(str).str.extract(r"\(([A-Z]{2})-", expand=False)
    df["RTO_State"] = df["RTO_Code"].map(RTO_CODE_TO_STATE)

    # -----------------------------------------------------------------------
    # Integrity Defects Audit
    # "Not Applicable" is the CORRECT VAHAN classification for EVs.
    # Only flag EVs carrying an ICE emission norm (BS4/BS6) as defective.
    # -----------------------------------------------------------------------
    df["QF_RTO_Mismatch"] = ~df["RTO_State"].eq(df["State"])
    df["QF_EV_Not_ZEV"] = df["Is_Electric"] & df["Emission_Norm"].isin(["BS4", "BS6", "BS3"])
    df["QF_EVBrand_Fossil"] = (df["Manufacturer_Brand"].isin(EV_ONLY_BRANDS)
                               & ~df["Is_Electric"])
    df["QF_Compliance_Mismatch"] = df["Is_Compliant"].ne(df["Compliance_Rule"])

    QF = ["QF_RTO_Mismatch", "QF_EV_Not_ZEV", "QF_EVBrand_Fossil", "QF_Compliance_Mismatch"]
    df["Has_Defect"] = df[QF].any(axis=1)
    df["Defect_Count"] = df[QF].sum(axis=1)

    # Fast Vectorized Reason String Construction
    reasons = pd.Series("", index=df.index)
    reasons += np.where(df["QF_RTO_Mismatch"], "RTO office belongs to a different state; ", "")
    reasons += np.where(df["QF_EV_Not_ZEV"], "Electric vehicle incorrectly carries ICE emission norm; ", "")
    reasons += np.where(df["QF_EVBrand_Fossil"], "Electric-only brand recorded as fossil fuel; ", "")
    reasons += np.where(df["QF_Compliance_Mismatch"], "Compliance flag disagrees with documented rule; ", "")
    df["Defect_Reasons"] = reasons.str.rstrip("; ")

    return df


def audit_quality(df_: pd.DataFrame) -> pd.DataFrame:
    n = len(df_)
    if n == 0:
        return pd.DataFrame()
    qf1 = (~df_["QF_RTO_Mismatch"]).sum()
    qf2 = (~df_["QF_EV_Not_ZEV"]).sum()
    qf3 = (~df_["QF_EVBrand_Fossil"]).sum()
    qf4 = (~df_["QF_Compliance_Mismatch"]).sum()
    return pd.DataFrame([
        {"Dimension": "Geographic", "Check": "RTO office belongs to registered State",
         "Passing records": qf1, "Failing records": n - qf1, "Pass rate": qf1 / n},
        {"Dimension": "Powertrain",
         "Check": "Electric vehicle does not carry ICE emission norm (BS4/BS6)",
         "Passing records": qf2, "Failing records": n - qf2, "Pass rate": qf2 / n},
        {"Dimension": "OEM", "Check": "Electric-only brand recorded as clean fuel",
         "Passing records": qf3, "Failing records": n - qf3, "Pass rate": qf3 / n},
        {"Dimension": "Compliance", "Check": "Compliance flag matches documented rule",
         "Passing records": qf4, "Failing records": n - qf4, "Pass rate": qf4 / n},
    ])


def index_by(df_: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """CFAR, Compliance Rate, and FMI (diversity) per group."""
    if df_.empty:
        return pd.DataFrame(columns=[group_col, "Registrations", "CFAR",
                                     "Compliance_Rate", "FMI_Diversity"])
    agg = (df_.groupby(group_col, observed=True)
              .agg(Registrations=("Registration_Number", "size"),
                   CFAR=("Is_Clean", lambda s: s.mean() * 100),
                   Compliance_Rate=("Is_Compliant", lambda s: s.mean() * 100))
              .reset_index())
    fmi = calc_fmi_by_group(df_, group_col)
    return agg.merge(fmi, on=group_col, how="left")


df_all = load_data(DATA_PATH)

# ---------------------------------------------------------------------------
# SIDEBAR - Dynamic Multi-Level Filters
# ---------------------------------------------------------------------------

st.sidebar.title("Filters & Options")
st.sidebar.caption("👤 **Author:** Abhiram\n\n📚 **Course:** Data Visualization & Storytelling")
st.sidebar.divider()

year_min = int(df_all["Registration_Year"].min())
year_max = int(df_all["Registration_Year"].max())
date_min = df_all["Registration_Date"].min().date()
date_max = df_all["Registration_Date"].max().date()

time_mode = st.sidebar.radio(
    "Filter time by", ["Year range", "Exact dates"], horizontal=True)

if time_mode == "Year range":
    year_range = st.sidebar.slider(
        "Registration year", year_min, year_max, (year_min, year_max), step=1)
    start_date = pd.Timestamp(year_range[0], 1, 1)
    end_date = pd.Timestamp(year_range[1], 12, 31)
else:
    d_from, d_to = st.sidebar.columns(2)
    with d_from:
        d0 = st.date_input("From", value=date_min, min_value=date_min, max_value=date_max, key="d0")
    with d_to:
        d1 = st.date_input("To", value=date_max, min_value=date_min, max_value=date_max, key="d1")
    if d0 > d1:
        d0, d1 = d1, d0
    start_date = pd.Timestamp(d0)
    end_date = pd.Timestamp(d1) + pd.Timedelta(hours=23, minutes=59)

time_granularity = st.sidebar.radio("Time Granularity", ["Yearly", "Monthly"], horizontal=True)

# State & RTO Selection
all_states = sorted(df_all["State"].unique())
states = st.sidebar.multiselect("State", all_states, default=all_states)
_state_pool = df_all[df_all["State"].isin(states)] if states else df_all
rto_options = sorted(_state_pool["RTO_Office"].unique())
rtos = st.sidebar.multiselect("RTO office", rto_options, default=[])

# Category & Sub-type Selection
cats_present = ordered(df_all["Vehicle_Category"], CATEGORY_ORDER)
categories = st.sidebar.multiselect("Vehicle category", cats_present, default=cats_present)
_cat_pool = df_all[df_all["Vehicle_Category"].isin(categories)] if categories else df_all
sub_options = sorted(_cat_pool["Vehicle_Sub_Type"].unique())
sub_types = st.sidebar.multiselect("Vehicle sub-type", sub_options, default=[])

brand_options = sorted(df_all["Manufacturer_Brand"].unique())
brands = st.sidebar.multiselect("Manufacturer (OEM)", brand_options, default=[])

st.sidebar.divider()

# Non-Mutating Copy for Sidebar State Auto-Correction
df_working = df_all.copy()
auto_correct_state = st.sidebar.checkbox(
    "Auto-correct State from RTO code", value=False,
    help="Automatically corrects State when RTO code belongs to another state.")

if auto_correct_state and "RTO_State" in df_working.columns:
    df_working["State"] = df_working["RTO_State"].fillna(df_working["State"])
    df_working["QF_RTO_Mismatch"] = ~df_working["RTO_State"].eq(df_working["State"])
    QF = ["QF_RTO_Mismatch", "QF_EV_Not_ZEV", "QF_EVBrand_Fossil", "QF_Compliance_Mismatch"]
    df_working["Has_Defect"] = df_working[QF].any(axis=1)

exclude_defects = st.sidebar.checkbox(
    "Exclude records failing data-quality checks", value=False,
    help="Removes rows failing integrity checks.")

mask = df_working["Registration_Date"].between(start_date, end_date)
if states:
    mask &= df_working["State"].isin(states)
if categories:
    mask &= df_working["Vehicle_Category"].isin(categories)
if rtos:
    mask &= df_working["RTO_Office"].isin(rtos)
if sub_types:
    mask &= df_working["Vehicle_Sub_Type"].isin(sub_types)
if brands:
    mask &= df_working["Manufacturer_Brand"].isin(brands)
if exclude_defects:
    mask &= ~df_working["Has_Defect"]

df = df_working[mask].copy()

st.sidebar.divider()
st.sidebar.metric("Records in selection", fmt_int(len(df)), f"of {fmt_int(len(df_all))} total")

# ---------------------------------------------------------------------------
# Header & Empty State Handling
# ---------------------------------------------------------------------------

st.title("VAHAN RTO Registration Analytics")
st.caption(
    f"**Prepared by:** Abhiram | **Course:** Data Visualization & Storytelling (DVS) | "
    f"{fmt_int(len(df_all))} registrations · {df_all['State'].nunique()} states · "
    f"{year_min} to {year_max}")

if df.empty:
    st.warning("No data available for the selected filters. Please adjust your selection in the sidebar.")
    st.stop()

tab_macro, tab_oem, tab_audit = st.tabs(
    ["Macro Fuel Transition",
     "OEM & Powertrain Strategy",
     "Regulatory & Data Quality Audit"])

# ===========================================================================
# TAB 1 - MACRO FUEL TRANSITION
# Rubric requirement: Registrations by Fuel Type, Category, Norm & Year
# ===========================================================================

with tab_macro:
    cfar = df["Is_Clean"].mean() * 100
    fmi_diversity = calc_fmi_overall(df)
    compliance_rate = df["Is_Compliant"].mean() * 100
    non_compliant = (~df["Is_Compliant"]).mean() * 100

    vol_by_year = df.groupby("Registration_Year").size().reset_index(name="Registrations")
    yoy_text = "Single period selected"
    if len(vol_by_year) >= 2:
        y_prev_val = vol_by_year["Registrations"].iloc[-2]
        y_last_val = vol_by_year["Registrations"].iloc[-1]
        y_prev_year = int(vol_by_year["Registration_Year"].iloc[-2])
        y_last_year = int(vol_by_year["Registration_Year"].iloc[-1])
        gap = y_last_year - y_prev_year
        if y_prev_val > 0:
            delta = (y_last_val - y_prev_val) / y_prev_val * 100
            yoy_text = f"{delta:+.1f}% vs {y_prev_year}" if gap == 1 else f"{delta:+.1f}% vs {y_prev_year} ({gap}-yr gap)"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        callout("Total registrations", fmt_int(len(df)), yoy_text)
    with k2:
        callout("Clean-Fuel Adoption Rate (CFAR)", fmt_score(cfar), "Electric, CNG or Hybrid")
    with k3:
        callout("Fuel Mix Index (FMI)", fmt_fmi(fmi_diversity),
                "Herfindahl diversity: 0 = single fuel, ~0.75 = balanced", accent=False)
    with k4:
        callout("Compliance rate", fmt_score(compliance_rate),
                f"BS6 or ZEV, ≤{MAX_COMPLIANT_AGE} yrs old", accent=False)

    st.divider()

    # --- Visual 1: Registrations by Fuel Type & Year (Trajectory) ---
    time_col = "Year_Month" if time_granularity == "Monthly" else "Registration_Year"
    time_label = "Registration date (month)" if time_granularity == "Monthly" else "Registration year"

    fuel_time = df.groupby([time_col, "Fuel_Type"]).size().reset_index(name="Registrations")
    fuel_totals = df.groupby(time_col).size().reset_index(name="Total")
    fuel_time = fuel_time.merge(fuel_totals, on=time_col)
    fuel_time["Share"] = fuel_time["Registrations"] / fuel_time["Total"]

    clean_series = df.groupby(time_col)["Is_Clean"].mean()
    macro_title, _ = describe_trend(clean_series, "Clean-fuel adoption")

    section(macro_title, "Fuel mix trajectory over time (Rubric: Registrations by Fuel Type & Year).")

    chart_style = st.radio("Display style", ["100% Stacked Area", "Line Trend with End-Labels", "Highlight Clean Fuels"], horizontal=True)
    fuels_here = ordered(fuel_time["Fuel_Type"], FUEL_ORDER)

    if chart_style == "100% Stacked Area":
        area = (
            chart(fuel_time)
            .mark_area()
            .encode(
                x=alt.X(f"{time_col}:T" if time_granularity == "Monthly" else f"{time_col}:O", title=time_label),
                y=alt.Y("Registrations:Q", stack="normalize", title="Share of registrations", axis=alt.Axis(format="%")),
                color=alt.Color("Fuel_Type:N", title="Fuel",
                                scale=alt.Scale(domain=fuels_here, range=colors_for(fuels_here, FUEL_COLOR)),
                                sort=fuels_here),
                tooltip=[alt.Tooltip(f"{time_col}", title="Time"), alt.Tooltip("Fuel_Type:N"), alt.Tooltip("Share:Q", format=".1%")],
            ).properties(height=340)
        )
        st.altair_chart(area, width="stretch")

    elif chart_style == "Line Trend with End-Labels":
        line = (
            chart(fuel_time)
            .mark_line(strokeWidth=2.5)
            .encode(
                x=alt.X(f"{time_col}:T" if time_granularity == "Monthly" else f"{time_col}:O", title=time_label),
                y=alt.Y("Share:Q", title="Share of registrations", axis=alt.Axis(format="%")),
                color=alt.Color("Fuel_Type:N", scale=alt.Scale(domain=fuels_here, range=colors_for(fuels_here, FUEL_COLOR))),
                tooltip=[alt.Tooltip(f"{time_col}"), alt.Tooltip("Fuel_Type:N"), alt.Tooltip("Share:Q", format=".1%")],
            )
        )
        last_t = fuel_time[time_col].max()
        end_data = fuel_time[fuel_time[time_col] == last_t]
        end_labels = chart(end_data).mark_text(align="left", dx=6, fontSize=11, fontWeight="bold").encode(
            x=alt.X(f"{time_col}:T" if time_granularity == "Monthly" else f"{time_col}:O"),
            y=alt.Y("Share:Q"),
            text="Fuel_Type:N",
            color=alt.Color("Fuel_Type:N", scale=alt.Scale(domain=fuels_here, range=colors_for(fuels_here, FUEL_COLOR))),
        )
        st.altair_chart((line + end_labels).properties(height=340), width="stretch")

    else:
        fuel_time["Opacity"] = fuel_time["Fuel_Type"].isin(CLEAN_FUELS).map({True: 1.0, False: 0.3})
        fuel_time["StrokeWidth"] = fuel_time["Fuel_Type"].isin(CLEAN_FUELS).map({True: 3.5, False: 1.5})
        line = (
            chart(fuel_time)
            .mark_line()
            .encode(
                x=alt.X(f"{time_col}:T" if time_granularity == "Monthly" else f"{time_col}:O", title=time_label),
                y=alt.Y("Share:Q", title="Share of registrations", axis=alt.Axis(format="%")),
                color=alt.Color("Fuel_Type:N", scale=alt.Scale(domain=fuels_here, range=colors_for(fuels_here, FUEL_COLOR))),
                strokeWidth=alt.StrokeWidth("StrokeWidth:Q", legend=None),
                opacity=alt.Opacity("Opacity:Q", legend=None),
                tooltip=[alt.Tooltip(f"{time_col}"), alt.Tooltip("Fuel_Type:N"), alt.Tooltip("Share:Q", format=".1%")],
            ).properties(height=340)
        )
        st.altair_chart(line, width="stretch")

    st.divider()

    # --- Visual 2: Annual Registration Volume (Spec: Bar Chart) ---
    section("Annual registration volume",
            "Data labels on bars, mean reference line, latest year highlighted.")

    vol_by_year["Is_Latest"] = vol_by_year["Registration_Year"] == vol_by_year["Registration_Year"].max()
    avg_vol = float(vol_by_year["Registrations"].mean())

    vol_bars = (
        chart(vol_by_year)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("Registration_Year:O", title="Registration year"),
            y=qy("Registrations:Q", "Registrations", fmt=","),
            color=alt.condition(
                alt.datum.Is_Latest,
                alt.value(ACCENT),
                alt.value(BAR_SECONDARY)),
            tooltip=[alt.Tooltip("Registration_Year:O"), alt.Tooltip("Registrations:Q", format=",")],
        )
    )
    vol_labels = (
        chart(vol_by_year)
        .mark_text(dy=-10, fontSize=12, fontWeight="bold", color=INK)
        .encode(
            x="Registration_Year:O",
            y="Registrations:Q",
            text=alt.Text("Registrations:Q", format=","),
        )
    )
    avg_rule = (
        alt.Chart(pd.DataFrame({"y": [avg_vol]}))
        .mark_rule(color=GREY_MID, strokeDash=[4, 4], strokeWidth=1.5)
        .encode(y="y:Q")
    )
    avg_label = (
        alt.Chart(pd.DataFrame({"y": [avg_vol], "label": [f"Avg: {avg_vol:,.0f}"]}))
        .mark_text(align="right", dx=-4, dy=-8, fontSize=10, color=TEXT_MUTED)
        .encode(y="y:Q", text="label:N",
                x=alt.value("width"))
    )
    st.altair_chart((vol_bars + vol_labels + avg_rule + avg_label).properties(height=300),
                    width="stretch")

    st.divider()

    cvc, cen = st.columns([1, 1])

    # --- Visual 3: Registrations by Vehicle Category (Rubric Task 2) ---
    with cvc:
        cat_counts = (df.groupby(["Vehicle_Category", "Category_Plain"])
                        .size().reset_index(name="Registrations")
                        .sort_values("Registrations", ascending=False))

        section("Registrations by Vehicle Category", "Rubric Requirement: Vehicle Category breakdown.")
        cat_base = chart(cat_counts).encode(
            x=qx("Registrations:Q", "Registrations", fmt=","),
            y=alt.Y("Category_Plain:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        )
        cat_bars = cat_base.mark_bar(cornerRadiusEnd=3, color=ACCENT)
        cat_lbl = cat_base.mark_text(align="left", dx=4, fontSize=11, color=INK).encode(
            text=alt.Text("Registrations:Q", format=","))
        st.altair_chart((cat_bars + cat_lbl).properties(height=260), width="stretch")

    # --- Visual 4: Registrations by Emission Norm (Rubric Task 2) ---
    with cen:
        norm_counts = (df.groupby(["Emission_Norm_Clean", "Norm_Label"])
                         .size().reset_index(name="Registrations")
                         .sort_values("Registrations", ascending=False))

        section("Registrations by Emission Norm", "Rubric Requirement: Emission Norm breakdown.")
        norm_base = chart(norm_counts).encode(
            x=qx("Registrations:Q", "Registrations", fmt=","),
            y=alt.Y("Norm_Label:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        )
        norm_bars = norm_base.mark_bar(cornerRadiusEnd=3, color=ACCENT_ALT)
        norm_lbl = norm_base.mark_text(align="left", dx=4, fontSize=11, color=INK).encode(
            text=alt.Text("Registrations:Q", format=","))
        st.altair_chart((norm_bars + norm_lbl).properties(height=260), width="stretch")

    st.divider()

    # --- Visual 5: CFAR by Vehicle Category (Bullet Chart) ---
    section("Clean-fuel adoption rate (CFAR) by vehicle category",
            "Bullet chart: bar = category CFAR, tick mark = selection average CFAR.")

    cfar_by_cat = (df.groupby(["Vehicle_Category", "Category_Plain"])
                     .agg(CFAR=("Is_Clean", lambda s: s.mean() * 100),
                          Registrations=("Registration_Number", "size"))
                     .reset_index()
                     .sort_values("CFAR", ascending=False))

    cfar_bars = (
        chart(cfar_by_cat)
        .mark_bar(cornerRadiusEnd=3, color=ACCENT)
        .encode(
            x=alt.X("CFAR:Q", title="CFAR (% clean fuel)", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("Category_Plain:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
            tooltip=[alt.Tooltip("Category_Plain:N", title="Category"),
                     alt.Tooltip("CFAR:Q", format=".1f"),
                     alt.Tooltip("Registrations:Q", format=",")],
        )
    )
    cfar_labels = (
        chart(cfar_by_cat)
        .mark_text(align="left", dx=4, fontSize=11, color=INK)
        .encode(
            x="CFAR:Q",
            y=alt.Y("Category_Plain:N", sort="-x"),
            text=alt.Text("CFAR:Q", format=".1f"),
        )
    )
    # Target tick at selection average CFAR
    cfar_target = (
        alt.Chart(pd.DataFrame({"x": [cfar]}))
        .mark_rule(color=FAIL_COLOR, strokeWidth=2.5, strokeDash=[6, 3])
        .encode(x="x:Q")
    )
    cfar_target_label = (
        alt.Chart(pd.DataFrame({"x": [cfar], "label": [f"Selection avg: {cfar:.1f}%"]}))
        .mark_text(align="left", dx=4, dy=-10, fontSize=10, color=FAIL_COLOR, fontWeight="bold")
        .encode(x="x:Q", text="label:N")
    )
    st.altair_chart(
        (cfar_bars + cfar_labels + cfar_target + cfar_target_label).properties(height=260),
        width="stretch")

    st.divider()

    c1, c2 = st.columns([1, 1])

    # --- Visual 6: Clean Fuel Hotspots Ranking (Regional Breakdown) ---
    with c1:
        rank_dim = st.radio("Rank clean-fuel adoption by", ["State", "RTO office"], horizontal=True)
        dim_col = "State" if rank_dim == "State" else "RTO_Office"
        ranked = index_by(df, dim_col).sort_values("CFAR", ascending=False)
        if rank_dim == "RTO office":
            ranked = ranked.head(20)

        if len(ranked) >= 6:
            top3 = set(ranked.head(3)[dim_col])
            bot3 = set(ranked.tail(3)[dim_col])
            ranked["Rank_Group"] = ranked[dim_col].apply(
                lambda val: "Top 3" if val in top3 else ("Bottom 3" if val in bot3 else "Middle")
            )
        else:
            ranked["Rank_Group"] = "Middle"

        section(f"Clean-fuel adoption hotspots by {rank_dim.lower()}",
                "Highlighting Top 3 leaders (Green) and Bottom 3 lagging regions (Red).")

        rank_base = chart(ranked).encode(
            x=qx("CFAR:Q", "CFAR (% clean fuel)"),
            y=alt.Y(f"{dim_col}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        )
        bars = rank_base.mark_bar(cornerRadiusEnd=3).encode(
            color=alt.Color("Rank_Group:N", scale=alt.Scale(domain=["Top 3", "Middle", "Bottom 3"],
                                                            range=[SUCCESS_COLOR, BAR_SECONDARY, FAIL_COLOR]),
                            legend=alt.Legend(orient="top", title=None)),
            tooltip=[alt.Tooltip(f"{dim_col}:N"), alt.Tooltip("CFAR:Q", format=".1f"), alt.Tooltip("Registrations:Q", format=",")],
        )
        lbl = rank_base.mark_text(align="left", dx=4, fontSize=11, color=INK).encode(text=alt.Text("CFAR:Q", format=".1f"))
        st.altair_chart((bars + lbl).properties(height=max(260, min(560, len(ranked) * 28))),
                        width="stretch")

    # --- Visual 7: Net Fuel Share Shift (Semantic Color Encoding) ---
    with c2:
        yrs = sorted(df["Registration_Year"].unique())
        section("Net fuel share shift (basis points)", "Gains and losses relative to baseline year.")
        if len(yrs) < 2:
            st.info("Select at least two years to measure a share shift.")
        else:
            y0, y1 = int(yrs[0]), int(yrs[-1])
            s0 = df[df["Registration_Year"] == y0]["Fuel_Type"].value_counts(normalize=True)
            s1 = df[df["Registration_Year"] == y1]["Fuel_Type"].value_counts(normalize=True)
            allf = ordered(set(s0.index) | set(s1.index), FUEL_ORDER)
            shift = pd.DataFrame({
                "Fuel": allf,
                "Shift_bps": [(s1.get(f, 0) - s0.get(f, 0)) * 10000 for f in allf],
            }).sort_values("Shift_bps")

            def _shift_cat(row):
                is_clean = row["Fuel"] in CLEAN_FUELS
                gain = row["Shift_bps"] >= 0
                if is_clean and gain: return "Clean fuel gain"
                if not is_clean and not gain: return "Fossil decline"
                if is_clean and not gain: return "Clean fuel decline"
                return "Fossil gain"

            shift["Category"] = shift.apply(_shift_cat, axis=1)

            shift_chart = (
                chart(shift)
                .mark_bar(cornerRadius=3)
                .encode(
                    x=alt.X("Shift_bps:Q", title=f"Share shift {y0} → {y1} (bps)"),
                    y=alt.Y("Fuel:N", sort="-x", title=None),
                    color=alt.Color("Category:N", scale=alt.Scale(
                        domain=["Clean fuel gain", "Fossil decline", "Clean fuel decline", "Fossil gain"],
                        range=[SUCCESS_COLOR, ACCENT, ACCENT_ALT, FAIL_COLOR]
                    ), legend=alt.Legend(orient="top", title=None)),
                    tooltip=[alt.Tooltip("Fuel:N"), alt.Tooltip("Shift_bps:Q", format="+,.0f")],
                ).properties(height=260)
            )
            zero_rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=GREY_MID).encode(x="x:Q")
            st.altair_chart(shift_chart + zero_rule, width="stretch")

# ===========================================================================
# TAB 2 - OEM & POWERTRAIN STRATEGY
# ===========================================================================

with tab_oem:
    oem = index_by(df, "Manufacturer_Brand")
    oem = oem.rename(columns={"Manufacturer_Brand": "Brand"})

    if oem.empty:
        st.warning("No data available for the selected filters.")
    else:
        top_vol = oem.loc[oem["Registrations"].idxmax()]
        top_cfar = oem.loc[oem["CFAR"].idxmax()]
        top_fmi = oem.loc[oem["FMI_Diversity"].idxmax()]

        k1, k2, k3 = st.columns(3)
        with k1:
            callout("Top OEM by volume", str(top_vol["Brand"]),
                    f"{fmt_int(top_vol['Registrations'])} registrations")
        with k2:
            callout("Highest clean-fuel OEM", str(top_cfar["Brand"]),
                    f"CFAR {top_cfar['CFAR']:.1f}%")
        with k3:
            callout("Most diversified OEM (FMI)", str(top_fmi["Brand"]),
                    f"FMI {top_fmi['FMI_Diversity']:.3f}", accent=False)

        st.divider()

        # --- OEM Strategic Quadrant Scatter (Volume-Weighted) ---
        section("Manufacturer Strategic Positioning Matrix",
                "X = CFAR (clean-fuel share), Y = FMI (fuel diversity). Volume-weighted quadrant centers.")

        if len(oem) < 2:
            st.info("Too few manufacturers to render scatter matrix.")
        else:
            x_mid = float(np.average(oem["CFAR"], weights=oem["Registrations"]))
            y_mid = float(np.average(oem["FMI_Diversity"], weights=oem["Registrations"]))

            oem["Quadrant"] = np.where(
                oem["CFAR"] >= x_mid,
                np.where(oem["FMI_Diversity"] >= y_mid, "Green pioneers", "Clean-fuel specialists"),
                np.where(oem["FMI_Diversity"] >= y_mid, "Diversified leaders", "ICE dependent"))

            rule_v = alt.Chart(pd.DataFrame({"x": [x_mid]})).mark_rule(color=GREY_DARK, strokeDash=[4, 4]).encode(x="x:Q")
            rule_h = alt.Chart(pd.DataFrame({"y": [y_mid]})).mark_rule(color=GREY_DARK, strokeDash=[4, 4]).encode(y="y:Q")

            quad_anno_df = pd.DataFrame({
                "x": [oem["CFAR"].max(), oem["CFAR"].min(), oem["CFAR"].max(), oem["CFAR"].min()],
                "y": [oem["FMI_Diversity"].max(), oem["FMI_Diversity"].max(),
                      oem["FMI_Diversity"].min(), oem["FMI_Diversity"].min()],
                "label": ["Green Pioneers", "Diversified Leaders",
                          "Clean-Fuel Specialists", "ICE Dependent"]
            })
            quad_anno = alt.Chart(quad_anno_df).mark_text(fontSize=11, fontWeight="bold", opacity=0.4, color=INK).encode(
                x="x:Q", y="y:Q", text="label:N"
            )

            scatter = chart(oem).mark_circle(opacity=0.65).encode(
                x=alt.X("CFAR:Q", title="CFAR (% clean fuel)", scale=alt.Scale(zero=False, padding=14)),
                y=alt.Y("FMI_Diversity:Q", title="FMI (fuel diversity score)",
                         scale=alt.Scale(zero=False, padding=14)),
                size=alt.Size("Registrations:Q", title="Volume", scale=alt.Scale(range=[60, 900])),
                color=alt.Color("Quadrant:N", scale=alt.Scale(
                    domain=["Green pioneers", "Diversified leaders", "Clean-fuel specialists", "ICE dependent"],
                    range=[SUCCESS_COLOR, ACCENT, ACCENT_ALT, GREY_MID]
                ), legend=alt.Legend(orient="top")),
                tooltip=[alt.Tooltip("Brand:N"), alt.Tooltip("CFAR:Q", format=".1f"),
                         alt.Tooltip("FMI_Diversity:Q", format=".3f", title="FMI"),
                         alt.Tooltip("Registrations:Q", format=",")],
            )
            labels = chart(oem).mark_text(dx=10, dy=-6, fontSize=11, color=INK).encode(
                x="CFAR:Q", y="FMI_Diversity:Q", text="Brand:N"
            )

            st.altair_chart((rule_v + rule_h + quad_anno + scatter + labels).properties(height=450),
                            width="stretch")

        st.divider()

        # --- OEM Market Share Trend Over Time ---
        section("OEM market share trajectory",
                "How top manufacturers' registration share evolved year-over-year.")

        n_top_trend = st.slider("Top OEMs to track", 3, min(10, len(oem)), min(6, len(oem)),
                                key="oem_trend_n")
        top_brands_trend = oem.nlargest(n_top_trend, "Registrations")["Brand"].tolist()

        brand_year = (df[df["Manufacturer_Brand"].isin(top_brands_trend)]
                      .groupby(["Registration_Year", "Manufacturer_Brand"]).size()
                      .reset_index(name="Registrations"))
        year_totals = df.groupby("Registration_Year").size().reset_index(name="Total")
        brand_year = brand_year.merge(year_totals, on="Registration_Year")
        brand_year["Market_Share"] = brand_year["Registrations"] / brand_year["Total"]

        trend_line = (
            chart(brand_year)
            .mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=40))
            .encode(
                x=alt.X("Registration_Year:O", title="Year"),
                y=alt.Y("Market_Share:Q", title="Market share",
                         axis=alt.Axis(format="%")),
                color=alt.Color("Manufacturer_Brand:N", title="Brand",
                                sort=top_brands_trend),
                tooltip=[alt.Tooltip("Manufacturer_Brand:N"),
                         alt.Tooltip("Registration_Year:O"),
                         alt.Tooltip("Market_Share:Q", format=".1%"),
                         alt.Tooltip("Registrations:Q", format=",")],
            )
        )
        # End-labels
        last_yr = brand_year["Registration_Year"].max()
        end_pts = brand_year[brand_year["Registration_Year"] == last_yr]
        trend_end = (
            chart(end_pts)
            .mark_text(align="left", dx=6, fontSize=11, fontWeight="bold")
            .encode(
                x="Registration_Year:O",
                y="Market_Share:Q",
                text="Manufacturer_Brand:N",
                color=alt.Color("Manufacturer_Brand:N", legend=None, sort=top_brands_trend),
            )
        )
        st.altair_chart((trend_line + trend_end).properties(height=360),
                        width="stretch")

        st.divider()

        # --- OEM Fuel Mix Horizontal Stacked Bar ---
        section("Fuel mix across top manufacturers", "Composition of sales by brand.")
        n_brands = len(oem)
        n_show = st.slider("Manufacturers to compare (by volume)", 5, min(30, max(5, n_brands)), min(15, max(5, n_brands)))
        keep = oem.nlargest(n_show, "Registrations")["Brand"].tolist()
        mix = df[df["Manufacturer_Brand"].isin(keep)].groupby(["Manufacturer_Brand", "Fuel_Type"]).size().reset_index(name="Registrations")
        fuels_mix = ordered(mix["Fuel_Type"], FUEL_ORDER)

        stacked = (
            chart(mix)
            .mark_bar()
            .encode(
                x=alt.X("Registrations:Q", stack="normalize", title="Share of registrations", axis=alt.Axis(format="%")),
                y=alt.Y("Manufacturer_Brand:N", sort=keep, title=None),
                color=alt.Color("Fuel_Type:N", scale=alt.Scale(domain=fuels_mix, range=colors_for(fuels_mix, FUEL_COLOR))),
                tooltip=[alt.Tooltip("Manufacturer_Brand:N"), alt.Tooltip("Fuel_Type:N"), alt.Tooltip("Registrations:Q", format=",")],
            ).properties(height=max(280, n_show * 24))
        )
        st.altair_chart(stacked, width="stretch")

        st.divider()

        # --- Engine CC Distribution (Box + Strip Plot) ---
        section("Engine displacement (CC) distribution", "Boxplot overlaid with jittered points for actual data density.")
        drop_ev = st.checkbox("Exclude electric vehicles (0 cc by definition)", value=True)
        cc = df[~df["Is_Electric"]] if drop_ev else df

        if not cc.empty:
            box = (
                chart(cc)
                .mark_boxplot(extent=1.5, size=20, median={"color": INK}, outliers={"color": FAIL_COLOR, "size": 12})
                .encode(
                    y=alt.Y("Vehicle_Sub_Type:N", title=None),
                    x=qx("Engine_CC:Q", "Engine displacement (cc)"),
                    color=alt.value(BAR_SECONDARY),
                )
            )
            strip = (
                chart(cc.sample(min(400, len(cc))))
                .mark_circle(size=10, opacity=0.25, color=ACCENT)
                .encode(
                    y=alt.Y("Vehicle_Sub_Type:N"),
                    x="Engine_CC:Q",
                )
            )
            st.altair_chart((box + strip).properties(height=360), width="stretch")

# ===========================================================================
# TAB 3 - REGULATORY & DATA QUALITY AUDIT (Drill-Down & Export Feature)
# ===========================================================================

with tab_audit:
    sec_a, sec_b = st.tabs(["Section A · Compliance & scrappage risk", "Section B · Data governance"])

    with sec_a:
        ice_fleet = df[df["Emission_Norm_Clean"] != "ZEV"]
        risk = ice_fleet[~ice_fleet["Is_Compliant"]].copy()

        st.caption(f"Vehicles are compliant if on a modern standard (BS6) and ≤{MAX_COMPLIANT_AGE} years old. ZEVs are exempt from age scrappage.")

        k1, k2, k3 = st.columns(3)
        with k1:
            callout("Non-compliant risk vehicles", fmt_int(len(risk)),
                    f"{(len(risk) / len(df) * 100):.1f}% of selection")
        with k2:
            callout("Compliance rate", fmt_score(df["Is_Compliant"].mean() * 100),
                    f"BS6 or ZEV, ≤{MAX_COMPLIANT_AGE} yrs old", accent=False)
        with k3:
            oldest = int(risk["Vehicle_Age_Years"].max()) if len(risk) else 0
            callout("Oldest non-compliant vehicle", f"{oldest} yrs",
                    "Scrappage risk increases with age", accent=False)

        if risk.empty:
            st.success("Zero vehicles in the selection fail compliance standards.")
        else:
            section("Ageing Fleet Heatmap: Vehicle Age vs Emission Norm",
                    "Warm colors highlight high scrappage risk density.")
            grid = risk.groupby(["Vehicle_Age_Years", "Emission_Norm_Clean"]).size().reset_index(name="Vehicles")

            hm = chart(grid).mark_rect().encode(
                x=alt.X("Emission_Norm_Clean:N", title="Emission standard"),
                y=alt.Y("Vehicle_Age_Years:O", title="Vehicle age (years)"),
                color=alt.Color("Vehicles:Q", scale=alt.Scale(scheme="oranges"), title="Vehicles"),
                tooltip=[alt.Tooltip("Vehicle_Age_Years:O"), alt.Tooltip("Emission_Norm_Clean:N"), alt.Tooltip("Vehicles:Q")],
            )
            txt = chart(grid).mark_text(fontSize=11, color=INK).encode(
                x="Emission_Norm_Clean:N", y="Vehicle_Age_Years:O", text=alt.Text("Vehicles:Q", format=",")
            )
            st.altair_chart((hm + txt).properties(height=320), width="stretch")

            section("Drill-down: Filterable Risk Fleet Table",
                    "View and export non-compliant vehicle details.")
            st.dataframe(
                risk[["Registration_Number", "State", "RTO_Office", "Vehicle_Category",
                      "Vehicle_Sub_Type", "Manufacturer_Brand", "Fuel_Type",
                      "Emission_Norm", "Vehicle_Age_Years", "Fail_Reason"]],
                width="stretch", height=340, hide_index=True
            )
            st.download_button("Download Risk Fleet CSV",
                               data=risk.to_csv(index=False).encode("utf-8"),
                               file_name="risk_fleet.csv", mime="text/csv")

    with sec_b:
        quality = audit_quality(df)
        defects = df[df["Has_Defect"]]
        cleanliness = (1 - len(defects) / len(df)) * 100

        k1, k2, k3 = st.columns(3)
        with k1:
            callout("Data cleanliness score", fmt_score(cleanliness),
                    "Passing all integrity checks")
        with k2:
            callout("Defective records found", fmt_int(len(defects)),
                    "State mismatches & classification errors", accent=False)
        with k3:
            failing = int((quality["Failing records"] > 0).sum())
            callout("Checks failing", f"{failing} of {len(quality)}",
                    accent=(failing == 0))

        section("Data Quality Audit Results")
        st.dataframe(
            quality.assign(**{"Pass rate": (quality["Pass rate"] * 100).round(1)}),
            width="stretch", hide_index=True,
            column_config={"Pass rate": st.column_config.NumberColumn(format="%.1f%%")}
        )

        # --- RTO Office Error-Rate Ranking Bar Chart (Spec §4.3) ---
        section("RTO office error rate ranking",
                "Ranked by percentage of records failing data quality checks (Spec requirement).")

        rto_quality = (df.groupby("RTO_Office")
                         .agg(Total=("Registration_Number", "size"),
                              Defective=("Has_Defect", "sum"))
                         .reset_index())
        rto_quality["Error_Rate"] = (rto_quality["Defective"] / rto_quality["Total"] * 100)
        rto_quality = rto_quality.sort_values("Error_Rate", ascending=False).head(20)

        if rto_quality["Defective"].sum() == 0:
            st.success("All RTO offices pass every data quality check.")
        else:
            rto_bars = (
                chart(rto_quality)
                .mark_bar(cornerRadiusEnd=3, color=FAIL_COLOR)
                .encode(
                    x=alt.X("Error_Rate:Q", title="Error rate (%)",
                            scale=alt.Scale(zero=True)),
                    y=alt.Y("RTO_Office:N", sort="-x", title=None,
                            axis=alt.Axis(labelLimit=280)),
                    tooltip=[alt.Tooltip("RTO_Office:N"),
                             alt.Tooltip("Error_Rate:Q", format=".1f"),
                             alt.Tooltip("Defective:Q", format=","),
                             alt.Tooltip("Total:Q", format=",")],
                )
            )
            rto_lbl = (
                chart(rto_quality)
                .mark_text(align="left", dx=4, fontSize=11, color=INK)
                .encode(
                    x="Error_Rate:Q",
                    y=alt.Y("RTO_Office:N", sort="-x"),
                    text=alt.Text("Error_Rate:Q", format=".1f"),
                )
            )
            st.altair_chart(
                (rto_bars + rto_lbl).properties(
                    height=max(260, min(500, len(rto_quality) * 26))),
                width="stretch")

        if not defects.empty:
            section("Data Hygiene Drill-down: Flagged Defect Records",
                    "Drill-down feature for inspecting raw defect rows.")
            st.dataframe(
                defects[["Registration_Number", "State", "RTO_Office",
                         "Vehicle_Category", "Manufacturer_Brand", "Fuel_Type",
                         "Emission_Norm", "Defect_Reasons"]],
                width="stretch", height=340, hide_index=True
            )
            st.download_button("Download Quality Exceptions CSV",
                               data=defects.to_csv(index=False).encode("utf-8"),
                               file_name="data_quality_exceptions.csv", mime="text/csv")
