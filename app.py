import streamlit as st
import pandas as pd
import re
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import dataframe_to_rows

# Page Configuration
st.set_page_config(
    page_title="AM Domain Extractor Pro",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Authentication state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login():
    st.title("🔐 AM Domain Extractor Pro - Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        if submit:
            if username == "admin" and password == "admin123":
                st.session_state.authenticated = True
                st.success("Successfully logged in!")
                st.rerun()
            else:
                st.error("Invalid username or password")

if not st.session_state.authenticated:
    login()
    st.stop()

# Header Section
st.markdown('<div class="main-header">🔍 AM Domain Extractor Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Extract, clean, and export domains instantly to Excel (.xlsx) or CSV</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.write("👤 Logged in as: *admin*")
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    st.markdown("---")
    st.subheader("⚙️ Settings")
    remove_duplicates = st.checkbox("Remove Duplicate Domains", value=True)
    convert_lowercase = st.checkbox("Convert to Lowercase", value=True)

# Helper function to extract domains
def extract_domains(text):
    domain_pattern = r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
    domains = re.findall(domain_pattern, text)
    if convert_lowercase:
        domains = [d.lower() for d in domains]
    if remove_duplicates:
        domains = list(dict.fromkeys(domains))
    return domains

# Helper function to generate Styled Excel File
def generate_excel(df):
    output = io.BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Extracted Domains"
    
    # Styling definitions
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=11)
    zebra_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )
    
    # Write headers
    headers = list(df.columns)
    ws.append(headers)
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Write rows
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=False), start=2):
        ws.append(row)
        for c_idx in range(1, len(row) + 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.font = data_font
            cell.border = thin_border
            if c_idx == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if r_idx % 2 == 0:
                cell.fill = zebra_fill
                
    # Auto-fit column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 5, 12)
        
    ws.freeze_panes = "A2"
    wb.save(output)
    output.seek(0)
    return output

# Main UI Tabs
tab1, tab2 = st.tabs(["📝 Text Input", "📁 File Upload"])

extracted_list = []

with tab1:
    st.markdown("### Paste Raw Text Below")
    raw_text = st.text_area("Paste text containing URLs or domains", height=200, placeholder="Paste your text here... e.g. https://example.com, test.org")
    if st.button("Extract Domains", key="btn_text"):
        if raw_text.strip():
            extracted_list = extract_domains(raw_text)
            st.session_state['last_extracted'] = extracted_list
        else:
            st.warning("Please enter some text to extract domains.")

with tab2:
    st.markdown("### Upload Text / CSV File")
    uploaded_file = st.file_uploader("Upload a .txt or .csv file", type=["txt", "csv"])
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        if st.button("Extract Domains from File", key="btn_file"):
            extracted_list = extract_domains(content)
            st.session_state['last_extracted'] = extracted_list

# Results Display and Download
if 'last_extracted' in st.session_state and st.session_state['last_extracted']:
    results = st.session_state['last_extracted']
    st.markdown("---")
    st.subheader(f"📊 Results ({len(results)} Domains Found)")
    
    df = pd.DataFrame({
        "S.No.": range(1, len(results) + 1),
        "Extracted Domain": results
    })
    
    st.dataframe(df, use_container_width=True, height=300)
    
    col1, col2 = st.columns(2)
    
    # 1. Download Excel (.xlsx)
    with col1:
        excel_data = generate_excel(df)
        st.download_button(
            label="📥 Download Excel (.xlsx)",
            data=excel_data,
            file_name="Extracted_Domains.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    # 2. Download CSV
    with col2:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Download CSV (.csv)",
            data=csv_data,
            file_name="Extracted_Domains.csv",
            mime="text/csv",
            use_container_width=True
        )
