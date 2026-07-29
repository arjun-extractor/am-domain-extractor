[11:06 PM, 7/28/2026] Arjun: import streamlit as st
import pandas as pd
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

# Page Configuration
st.set_page_config(
    page_title="AM Domain Extractor - Multi-Threaded High-Speed Edition",
    page_icon="⚡",
    layout="wide"
)

# Custom Styling to match the professional dashboard
st.markdown("""
<style>
    .main-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 0.85rem;
        color: #6B7280;
        margin-bottom: 15px;
    }
    .metric-box {
        background-color: #1E3A8A;
        color: white;
        padding: 10px;
        b…
[11:14 PM, 7/28/2026] Arjun: import streamlit as st
import pandas as pd

# Page Configuration (Dark Theme match)
st.set_page_config(
    page_title="AM Domain Extractor Pro",
    page_icon="🚀",
    layout="wide"
)

# Custom Dark Theme Styling
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    .main-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 0.8rem;
        color: #9CA3AF;
        margin-bottom: 15px;
    }
    .metric-box {
        background-color: #1F2937;
        color: white;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 10px;
        border-left: 4px solid #3B82F6;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🚀 AM Domain Extractor Pro")
    st.markdown("---")
    if st.button("📊 DASHBOARD", use_container_width=True, type="primary"):
        pass
    if st.button("📥 DOWNLOAD RESULTS", use_container_width=True):
        pass
    if st.button("✉️ COLD PITCH TEMPLATES", use_container_width=True):
        pass
    
    st.markdown("---")
    st.caption("Pro Account Status")
    st.markdown("<div class='metric-box'><b>Exhaust Progress</b><br><span style='font-size: 1.3rem; color: #60A5FA;'>100%</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-box'><b>Temp. / Current Run Domains</b><br><span style='font-size: 1.3rem; color: #60A5FA;'>30</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-box'><b>Directories Skipped</b><br><span style='font-size: 1.3rem; color: #60A5FA;'>20</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-box'><b>Total Database Domains</b><br><span style='font-size: 1.3rem; color: #60A5FA;'>544</span></div>", unsafe_allow_html=True)

# Main Header
st.markdown('<div class="main-title">🚀 AM Domain Extractor Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Clean Local Business Domain Extractor - Speed Locked (5 Threads, 1-20 Limits)</div>', unsafe_allow_html=True)

# 3-Column Inputs Layout (Matching your screenshot)
col1, col2, col3 = st.columns([1, 1.3, 1])

with col1:
    st.markdown("<b>1. Target Country:</b>", unsafe_allow_html=True)
    target_country = st.selectbox("Country", ["United States", "India", "Canada", "UK"], label_visibility="collapsed")

with col2:
    st.markdown("<b>2. Keywords (One per line):</b>", unsafe_allow_html=True)
    keywords = st.text_area(
        "Keywords", 
        value="Residential Electrical Contractor\nCommercial Electrical Repair\nElectrical Service Upgrades\nHouse Rewiring\nElectrical Panel Replacement", 
        height=100,
        label_visibility="collapsed"
    )

with col3:
    st.markdown("<b>3. Cities / States (One per line):</b>", unsafe_allow_html=True)
    cities = st.text_area(
        "Cities", 
        value="Main\nNewyork\nVirginia", 
        height=100,
        label_visibility="collapsed"
    )

# Action Buttons Bar
b_col1, b_col2, b_col3 = st.columns([1.5, 1.5, 2])
with b_col1:
    start_btn = st.button("🚀 Start Extraction Process", type="primary", use_container_width=True)
with b_col2:
    pause_btn = st.button("⏸️ Pause / Stop Extraction", use_container_width=True)
with b_col3:
    clear_btn = st.button("🧹 Clear Inputs & Reset", use_container_width=True)

st.markdown("---")
st.markdown("### Live Extracted Data Stream (Current Run Only)")

# Live Data Stream Table matching your exact columns
data = {
    "Keyword": ["Electrical Service Upgrades"] * 6,
    "Region": ["Virginia", "Virginia", "Virginia", "Virginia", "Vermont", "Vermont"],
    "Client Domain": [
        "qbaegtechris.com",
        "mjioe-electric.com",
        "universal-electric-group.com",
        "upgrade-electric.com",
        "rootetechhi.com",
        "electrical-san-gobills.com"
    ],
    "Email": [
        "info@qbaegtechris.com",
        "user@domains.com",
        "contact@universal-electric-group.com",
        "N/A",
        "N/A",
        "N/A"
    ],
    "Phone": [
        "(542) 661-8000",
        "877-343348",
        "877-558-8600",
        "N/A",
        "(572)-641-0000",
        "N/A"
    ],
    "SSL Status": ["Yes", "Yes", "Yes", "Yes", "No", "Yes"],
    "Site Speed": ["Fast", "Fast", "Fast", "Fast", "Fast", "Slow"],
    "Full URL": [
        "https://@ringtehbtn.com/service/service-upgrades",
        "https://www.mjioe-electric.com?utm_campaign=gmb",
        "https://universal-electric.group.com/services/dashboard-upgrades",
        "https://upgrade-electric.com/",
        "https://www.rootetechhi.com/upgrade-upgraded",
        "https://electrical-san-gobills.com/network"
    ]
}

df_live = pd.DataFrame(data)
st.dataframe(df_live, use_container_width=True, height=280)
