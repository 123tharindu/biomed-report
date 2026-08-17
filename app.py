import datetime
import io
import os
import base64
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from PIL import Image, ImageOps, ImageEnhance

from google import genai
import gspread
from google.oauth2.service_account import Credentials
import requests

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import streamlit as st

# ==========================================
# 1. PAGE CONFIGURATION & MOBILE CSS
# ==========================================
st.set_page_config(
    page_title="Biomed International - AI Lap Scan Portal",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def get_local_logo_base64(file_path="bmi_logo.png"):
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{encoded}"
        except Exception:
            pass
    return "https://via.placeholder.com/100x50.png?text=BMI+Logo"

LOGO_SRC = get_local_logo_base64("bmi_logo.png")

if os.path.exists("bmi_logo.png"):
    st.logo("bmi_logo.png", icon_image="bmi_logo.png")

# Mobile Optimization & Fixed Dropdown CSS
st.markdown(
    """
<style>
    /* Responsive Global Container */
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    
    .main { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    /* Mobile Dropdown / SelectBox UI Fix for On-Screen Keyboard */
    div[data-baseweb="popover"] {
        max-height: 220px !important;
        z-index: 999999 !important;
    }
    div[data-baseweb="popover"] > div {
        max-height: 220px !important;
        overflow-y: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
    div[role="listbox"] {
        max-height: 200px !important;
    }
    
    /* Responsive Header Area */
    .brand-header {
        background: linear-gradient(135deg, #0D2A4A 0%, #1E3A8A 100%);
        padding: 14px 16px; 
        border-radius: 12px; 
        color: white;
        box-shadow: 0 4px 15px rgba(13, 42, 74, 0.15); 
        margin-bottom: 15px;
    }
    .brand-header h1 { 
        color: #FFFFFF !important; 
        font-size: 16px !important; 
        font-weight: 800 !important; 
        margin: 0 !important; 
        line-height: 1.3; 
    }
    .brand-header p { 
        color: #93C5FD !important; 
        font-size: 10px !important; 
        margin-top: 3px !important; 
        font-weight: 600; 
    }
    .status-badge {
        background-color: rgba(255, 255, 255, 0.15); 
        color: #FFFFFF;
        padding: 4px 8px; 
        border-radius: 6px; 
        font-size: 10px;
        font-weight: 600; 
        display: inline-block;
        margin-bottom: 8px;
    }
    .header-logo-box {
        background-color: #FFFFFF;
        padding: 4px 8px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        height: 40px;
    }
    .header-logo-box img {
        max-height: 32px;
        max-width: 80px;
        object-fit: contain;
    }
    
    /* Mobile Touch-Friendly Instrument Cards */
    .instrument-card {
        background-color: #FFFFFF; 
        border: 1px solid #E2E8F0;
        border-radius: 12px; 
        padding: 12px; 
        margin-bottom: 15px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }
    .section-title { 
        font-size: 15px; 
        font-weight: 700; 
        color: #0D2A4A; 
        border-bottom: 2px solid #E2E8F0; 
        padding-bottom: 6px; 
        margin-bottom: 12px; 
    }
    
    /* Mobile Large Touch Buttons */
    .stButton>button {
        width: 100% !important;
        border-radius: 8px !important;
        min-height: 45px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0D2A4A 0%, #1E3A8A 100%) !important;
        color: white !important; 
        border: none !important;
        min-height: 50px !important;
        font-size: 15px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. GEMINI CLIENT SETUP & DATA LISTS
# ==========================================
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SL_HOSPITALS = [
    "-- Select Hospital / Institute --",
    "District General Hospital Hambantota",
    "Base Hospital Tangalle",
    "District General Hospital Matara",
    "Base Hospital Kamburupitiya",
    "National Hospital Galle (Karapitiya)",
    "Galle Mediclinic / Cardicare",
    "Ruhunu Hospital Galle",
    "Base Hospital Elpitiya",
    "Base Hospital Balapitiya",
    "Asiri Hospital Galle",
    "Teaching Hospital Kalutara",
    "Philip Hospital Kalutara",
    "Kethumathi Maternity Hospital Kalutara",
    "Colombo South Teaching Hospital (Kalubowila)",
    "National Hospital of Sri Lanka (NHSL Colombo)",
    "National Eye Hospital Colombo",
    "Lady Ridgeway Hospital for Children (LRH)",
    "Sri Jayewardenepura General Hospital (SJGH)",
    "Nawaloka Hospital Colombo",
    "Lanka Hospitals Colombo",
    "Asiri Central Hospital",
    "Castle Street Hospital for Women",
    "De Soysa Hospital for Women (DMH)",
    "Apeksha Hospital Maharagama",
    "Colombo Army Hospital",
    "Durdans Hospital Colombo",
    "General Sir John Kotelawala Defence University Hospital (KDU)",
    "Wish Fertility & Women's Hospital",
    "Asiri Surgical Hospital",
    "Kings Hospital Colombo",
    "District General Hospital Gampaha",
    "Colombo North Teaching Hospital (Ragama)",
    "Sri Lanka Navy General Hospital Welisara",
    "District General Hospital Chilaw",
    "Base Hospital Puttalam",
    "Teaching Hospital Kuliyapitiya",
    "Teaching Hospital Kurunegala",
    "Kurunegala Co-operative Hospital",
    "Base Hospital Dambadeniya",
    "Base Hospital Rikillagaskada",
    "National Hospital Kandy",
    "Asiri Hospital Kandy",
    "Teaching Hospital Peradeniya",
    "Sirimavo Bandaranaike Specialized Children's Hospital",
    "District General Hospital Matale",
    "Base Hospital Dambulla",
    "Teaching Hospital Badulla",
    "Teaching Hospital Anuradhapura",
    "District General Hospital Polonnaruwa",
    "Teaching Hospital Ratnapura",
    "Base Hospital Embilipitiya",
    "Teaching Hospital Kegalle",
    "Teaching Hospital Batticaloa",
    "Base Hospital Valaichchenai",
    "District General Hospital Trincomalee",
    "Base Hospital Akkaraipattu",
    "Teaching Hospital Jaffna",
    "Holy Cross Hospital Jaffna",
    "Northern Central Hospital Jaffna",
    "Other (Type manually)"
]

DAMAGE_SUGGESTIONS = [
    "-- Select Detailed Technical Damage --",
    "Sealing Cap Damage: Silicone sealing element is torn/damaged. High risk of pneumoperitoneum gas leakage during insufflation.",
    "Insulation Damage: Insulation layer cracked/peeled near the shaft tip. High risk of stray electrical current leaks (HF insulation failure).",
    "Shaft Insulation Micro-Cracks: Flaking detected along middle shaft. High risk of unwanted tissue burns during HF activation.",
    "Shaft Deformation: Outer shaft tube is visibly bent/misaligned, causing severe internal friction and restricting jaw movement.",
    "Jaw Alignment Failure: Working jaws are misaligned with worn-out gripping teeth. Instrument fails to hold tissue securely.",
    "Ratchet Lock Failure: Handle locking mechanism/ratchet teeth worn out. Instrument fails to hold position under tension.",
    "Scissor Blade Bluntness: Scissor blades show heavy dullness and burrs along the cutting edge. Fails clean cutting.",
    "HF Connector Damage: Monopolar/Bipolar terminal pin bent or corroded. Poor electrical contact during electrosurgery.",
    "Trocar Stopcock Leak: Gas valve/stopcock lever worn out and leaking. Cannot maintain stable intra-abdominal pressure.",
    "Corrosion & Pitting: Severe pitting corrosion and rust stains observed near joints due to chemical sterilization.",
    "Pass Inspection: Instrument in optimal condition. No physical defect or operational damage observed."
]

EXCEL_FILE = "Full Laparoscopy Articles Updated master file 07.07.2026.xlsx"

@st.cache_data
def load_catalog(file_path):
    if os.path.exists(file_path):
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            df.columns = [str(col).strip() for col in df.columns]
            art_col, desc_col = df.columns[0], df.columns[1] if len(df.columns) > 1 else df.columns[0]
            df = df.dropna(subset=[art_col])
            return dict(zip(df[art_col].astype(str).str.strip(), df[desc_col].astype(str).str.strip()))
        except Exception as e:
            st.warning(f"Excel reading note: {e}")
            
    return {
        "BB365R": "Scissors Curved 17mm",
        "BB074R": "Forceps Dissecting",
        "BC051R": "Needle Holder",
        "EK087P": "Sealing Cap"
    }

catalog_dict = load_catalog(EXCEL_FILE)
article_options = sorted(list(catalog_dict.keys()))

# 📸 Enhanced Image Processing Function (Enhances Photo Details & Sharpness)
def process_and_compress_image(image_file, max_size=(1000, 1000)):
    img = Image.open(image_file)
    img = ImageOps.exif_transpose(img)
    
    # 1. Image Resize for optimal memory and detail
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Convert to RGB if PNG/RGBA
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    # 2. Enhance Contrast (Details stand out better)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.25)
    
    # 3. Enhance Sharpness (Micro-cracks, wear & tears become clearer)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.4)
    
    # 4. Enhance Brightness slightly for phone photos
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.05)
    
    return img

def analyze_damage_with_ai(image_file, item_name):
    if not client:
        return "API Key not configured properly.", "OK"
    try:
        compressed_img = process_and_compress_image(image_file, max_size=(800, 800))
        prompt = f"Examine surgical instrument '{item_name}' for damage. Line 1: Technical damage (Max 20 words). Line 2: Recommendation (Replace/Repair/Service/OK)."
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[compressed_img, prompt]
        )
        lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        return lines[0] if len(lines) > 0 else "Inspected", lines[1] if len(lines) > 1 else "Service"
    except Exception as e:
        return f"AI Error: {str(e)}", "Service"

def sync_to_google_sheet(summary_data):
    webhook_url = st.secrets.get("WEBHOOK_URL", "")
    if webhook_url:
        try:
            requests.post(webhook_url, json=summary_data, timeout=10)
            return True
        except Exception:
            pass

    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        client_gs = gspread.authorize(creds)
        sheet = client_gs.open("Biomed Lap Inspection Summary").sheet1
        
        row = [
            summary_data.get("report_no"),
            summary_data.get("date"),
            summary_data.get("hospital"),
            summary_data.get("engineer"),
            summary_data.get("instrument_name"),
            summary_data.get("total_instruments"),
            summary_data.get("replace_count"),
            summary_data.get("service_count"),
            summary_data.get("logged_at")
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.warning(f"Google Sheet Sync Note: {e}")
        return False

def generate_professional_excel(instruments_data, hospital_name, engineer_name, report_no, date_str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inspection Summary"
    ws.views.sheetView[0].showGridLines = True

    NAVY_HEADER = "0D2A4A"
    ICE_BLUE = "F0F4F8"
    WHITE = "FFFFFF"
    BORDER_COLOR = "CBD5E1"
    TEXT_MAIN = "0F172A"

    font_title = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    font_header = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Arial", size=9, color=TEXT_MAIN)
    font_bold = Font(name="Arial", size=9, bold=True, color=TEXT_MAIN)

    fill_navy = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
    fill_zebra = PatternFill(start_color=ICE_BLUE, end_color=ICE_BLUE, fill_type="solid")
    fill_white = PatternFill(start_color=WHITE, end_color=WHITE, fill_type="solid")

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    thin_border = Side(border_style="thin", color=BORDER_COLOR)
    cell_border = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)

    ws.merge_cells("A1:F1")
    ws["A1"] = "BIOMED INTERNATIONAL (PVT) LTD — TECHNICAL INSPECTION REPORT"
    ws["A1"].font = font_title
    ws["A1"].fill = fill_navy
    ws["A1"].alignment = align_center
    ws.row_dimensions[1].height = 28

    meta_info = [
        ("Customer / Hospital:", hospital_name, "Inspection Date:", date_str),
        ("Engineer Name:", engineer_name, "Report Ref No:", report_no)
    ]

    for r_idx, row in enumerate(meta_info, start=3):
        ws.cell(row=r_idx, column=1, value=row[0]).font = font_bold
        ws.cell(row=r_idx, column=2, value=row[1]).font = font_data
        ws.cell(row=r_idx, column=4, value=row[2]).font = font_bold
        ws.cell(row=r_idx, column=5, value=row[3]).font = font_data
        ws.row_dimensions[r_idx].height = 20

    headers = ["#", "ARTICLE NO", "INSTRUMENT DESCRIPTION", "TECHNICAL DAMAGE DETAILS", "RECOMMENDATION", "STATUS"]
    header_row = 6
    ws.row_dimensions[header_row].height = 25

    for c_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=c_idx, value=header)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = cell_border

    start_data_row = 7
    for idx, item in enumerate(instruments_data):
        current_row = start_data_row + idx
        ws.row_dimensions[current_row].height = 24
        row_fill = fill_zebra if idx % 2 == 1 else fill_white
        
        rec = item.get("recommendation", "Service")
        status_text = "ACTION REQ." if rec == "Replace" else "PASSED / OK"
        rec_font = Font(name="Arial", size=9, bold=True, color="B91C1C" if rec == "Replace" else "15803D")

        row_data = [
            (idx + 1, align_center, font_data),
            (item.get("art_no", ""), align_center, font_bold),
            (item.get("name", ""), align_left, font_data),
            (item.get("damage", ""), align_left, font_data),
            (rec.upper(), align_center, rec_font),
            (status_text, align_center, font_data)
        ]

        for c_idx, (val, align, font_style) in enumerate(row_data, start=1):
            cell = ws.cell(row=current_row, column=c_idx, value=val)
            cell.font = font_style
            cell.fill = row_fill
            cell.alignment = align
            cell.border = cell_border

    col_widths = {1: 6, 2: 18, 3: 38, 4: 42, 5: 20, 6: 15}
    for col_idx, width in col_widths.items():
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

if 'num_instruments' not in st.session_state:
    st.session_state.num_instruments = 1

def update_desc_callback(idx):
    sel_art = st.session_state.get(f"s_art_{idx}")
    if sel_art and sel_art in catalog_dict:
        st.session_state[f"name_{idx}"] = catalog_dict[sel_art]

# ==========================================
# 3. UI HEADER & SIDEBAR
# ==========================================
st.markdown(f"""
    <div class="brand-header">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <div class="header-logo-box">
                <img src="{LOGO_SRC}" alt="Biomed Logo" />
            </div>
            <div class="status-badge">🟢 Active</div>
        </div>
        <div>
            <h1>BIOMED INTERNATIONAL (PVT) LTD</h1>
            <p>AESCULAP DIVISION — AI LAP SCAN PORTAL</p>
        </div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 📋 Meta Information")
hospital_sel = st.sidebar.selectbox("Customer / Hospital", options=SL_HOSPITALS)
if hospital_sel == "Other (Type manually)":
    hospital_name = st.sidebar.text_input("Enter Hospital Name Manually")
elif hospital_sel == "-- Select Hospital / Institute --":
    hospital_name = ""
else:
    hospital_name = hospital_sel

date_val = st.sidebar.date_input("Inspection Date", value=datetime.date.today())
engineer_val = st.sidebar.text_input("Engineer / Inspector Name")
report_no_val = st.sidebar.text_input("Report Reference No.")
dept_val = st.sidebar.text_input("Department", value="Theatre / Laparoscopy")
remarks_val = st.sidebar.text_area("General Remarks & Inspection Notes", value="All above instruments require official inspection and technical servicing.", height=80)

st.markdown("<div class='section-title'>🔬 Surgical Instruments Entry</div>", unsafe_allow_html=True)

instruments_data = []

# ==========================================
# 4. INSTRUMENTS INPUT LOOP (MOBILE FRIENDLY)
# ==========================================
for i in range(st.session_state.num_instruments):
    st.markdown(f"<div class='instrument-card'><b>🔪 Instrument Entry #{i+1}</b>", unsafe_allow_html=True)
    
    inst_item = {}
    inst_item["image"] = st.file_uploader(f"📷 Upload Image / Take Photo #{i+1}", type=["jpg", "png", "jpeg"], key=f"uploader_{i}")
    if inst_item["image"]:
        # Preview processed enhanced image
        enhanced_preview = process_and_compress_image(inst_item["image"])
        st.image(enhanced_preview, caption="✨ Enhanced Photo Preview", use_container_width=True)
            
    is_custom = st.checkbox("✍️ Custom Article No", key=f"custom_chk_{i}")
    if is_custom:
        art_no = st.text_input(f"Enter Article No #{i+1}", key=f"c_art_{i}")
        inst_name = st.text_input(f"Instrument Description #{i+1}", key=f"name_{i}")
    else:
        art_no = st.selectbox(f"Search Master Catalog #{i+1}", options=[""] + article_options, key=f"s_art_{i}", on_change=update_desc_callback, args=(i,))
        inst_name = st.text_input(f"Instrument Description #{i+1}", key=f"name_{i}")
        
    inst_item["art_no"] = art_no
    inst_item["name"] = inst_name
    
    if inst_item["image"] and GEMINI_API_KEY:
        if st.button(f"✨ AI Auto-Detect Damage #{i+1}", key=f"ai_btn_{i}"):
            with st.spinner("Analyzing with Gemini AI..."):
                ai_dam, ai_rec = analyze_damage_with_ai(inst_item["image"], inst_item["name"])
                st.session_state[f"dam_{i}"] = ai_dam
                st.session_state[f"rec_{i}"] = ai_rec
                st.rerun()

    selected_preset = st.selectbox(f"💡 Technical Fault Presets #{i+1}", options=DAMAGE_SUGGESTIONS, key=f"preset_{i}")
    
    if selected_preset and not selected_preset.startswith("--"):
        curr = st.session_state.get(f"dam_{i}", "")
        if selected_preset not in curr:
            st.session_state[f"dam_{i}"] = f"{curr}\n{selected_preset}".strip() if curr else selected_preset

    inst_item["damage"] = st.text_area(f"Damage Details #{i+1}", key=f"dam_{i}", height=70)
    
    rec_opts = ["Replace", "Service", "Repair", "Upgrade / New System Required", "OK"]
    inst_item["recommendation"] = st.selectbox(f"Recommendation #{i+1}", options=rec_opts, key=f"rec_{i}")
        
    instruments_data.append(inst_item)
    st.markdown("</div>", unsafe_allow_html=True)

col_add, col_rem = st.columns(2)
with col_add:
    if st.button("➕ Add Item"):
        st.session_state.num_instruments += 1
        st.rerun()
with col_rem:
    if st.session_state.num_instruments > 1:
        if st.button("🗑️ Remove Last"):
            st.session_state.num_instruments -= 1
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. GENERATE PDF & GOOGLE SHEET SYNC
# ==========================================
if st.button("📄 Generate PDF Report & Sync Summary", type="primary", use_container_width=True):
    with st.spinner("Generating PDF Report..."):
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15,
            leftMargin=15,
            topMargin=10,
            bottomMargin=10
        )
        story, styles = [], getSampleStyleSheet()
        temp_files = []

        navy_primary = colors.HexColor("#0D2A4A")
        ice_blue_bg = colors.HexColor("#F0F4F8")
        border_navy = colors.HexColor("#BAC7D5")

        company_name_style = ParagraphStyle('CompName', parent=styles['Heading1'], fontSize=10.5, leading=12, textColor=navy_primary, fontName="Helvetica-Bold")
        company_sub_style = ParagraphStyle('CompSub', parent=styles['Normal'], fontSize=7, leading=9, textColor=colors.HexColor("#475569"))
        label_style = ParagraphStyle('LabelNavy', parent=styles['Normal'], fontSize=7.5, leading=9.5, textColor=navy_primary, fontName="Helvetica-Bold")
        value_style = ParagraphStyle('ValueText', parent=styles['Normal'], fontSize=7.5, leading=9.5, textColor=colors.HexColor("#1F2937"))
        cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=7.5, leading=9.5)
        cell_center = ParagraphStyle('TableCellCenter', parent=cell_style, alignment=1)
        th_style = ParagraphStyle('TH', parent=cell_style, fontSize=7, leading=9, textColor=colors.white, fontName="Helvetica-Bold", alignment=1)

        # PDF Header Box
        company_info = [
            Paragraph("BIOMED INTERNATIONAL (PVT) LTD", company_name_style),
            Paragraph("AESCULAP Division | Colombo 03, Sri Lanka", company_sub_style)
        ]
        logo_img = RLImage("bmi_logo.png", width=60, height=28) if os.path.exists("bmi_logo.png") else Paragraph("<b>BMI</b>", company_name_style)

        t_header = Table([[
            logo_img,
            company_info,
            [Paragraph("TECHNICAL INSPECTION REPORT", ParagraphStyle('T', parent=company_name_style, alignment=2)),
             Paragraph("LAP SCAN DIAGNOSTICS", ParagraphStyle('S', parent=company_sub_style, alignment=2))]
        ]], colWidths=[65, 290, 210])
        
        t_header.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ice_blue_bg),
            ('BOX', (0,0), (-1,-1), 1, navy_primary),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 4))

        # PDF Metadata Box
        disp_hospital = hospital_name if hospital_name else "N/A"
        disp_engineer = engineer_val.strip() if engineer_val.strip() else "Biomed Technical Team"
        disp_rep_no = report_no_val.strip() if report_no_val.strip() else "N/A"
        date_str = date_val.strftime("%d %B %Y")

        meta_data = [
            [Paragraph("Customer / Hospital:", label_style), Paragraph(disp_hospital, value_style), Paragraph("Brand:", label_style), Paragraph("Aesculap", value_style)],
            [Paragraph("Inspection Date:", label_style), Paragraph(date_str, value_style), Paragraph("System / Set:", label_style), Paragraph("Laparoscopy", value_style)],
            [Paragraph("Engineer Name:", label_style), Paragraph(disp_engineer, value_style), Paragraph("Report No:", label_style), Paragraph(disp_rep_no, value_style)],
            [Paragraph("Department:", label_style), Paragraph(dept_val, value_style), Paragraph("Scope S/N:", label_style), Paragraph("N/A", value_style)],
        ]
        t_meta = Table(meta_data, colWidths=[100, 182, 100, 183])
        t_meta.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, border_navy),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_navy),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 1.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 4))

        # PDF Instruments Table - High Quality Auto-Enhanced Image Embedded
        table_data = [[
            Paragraph("#", th_style),
            Paragraph("INSPECTION PHOTO", th_style),
            Paragraph("ARTICLE NO", th_style),
            Paragraph("INSTRUMENT NAME", th_style),
            Paragraph("DETAILS OF DAMAGE", th_style),
            Paragraph("RECOMMENDATION", th_style)
        ]]

        replace_count = 0
        service_count = 0

        for idx, item in enumerate(instruments_data):
            img_cell = Paragraph("No Image Attached", cell_center)
            if item["image"]:
                t_path = f"temp_p_{idx}.jpg"
                p_img = process_and_compress_image(item["image"], max_size=(1000, 1000))
                p_img.save(t_path, "JPEG", quality=95)
                
                # Large Enhanced Photo Dimensions in PDF
                img_cell = RLImage(t_path, width=120, height=110)
                temp_files.append(t_path)

            rec_color = "#C0392B" if item["recommendation"] == "Replace" else ("#D35400" if item["recommendation"] in ["Service", "Repair"] else "#27AE60")
            if item["recommendation"] == "Replace":
                replace_count += 1
            else:
                service_count += 1

            table_data.append([
                Paragraph(str(idx + 1), cell_center),
                img_cell,
                Paragraph(f"<b>{item['art_no']}</b>", cell_style),
                Paragraph(item["name"], cell_style),
                Paragraph(item["damage"].replace("\n", "<br/>"), cell_style),
                Paragraph(f"<b><font color='{rec_color}'>{item['recommendation'].upper()}</font></b>", cell_center)
            ])

        t_main = Table(table_data, colWidths=[18, 128, 62, 105, 162, 90])
        t_main.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), navy_primary),
            ('GRID', (0,0), (-1,-1), 0.5, border_navy),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_main)
        story.append(Spacer(1, 4))

        # Remarks Box
        remarks_html = f"<b><font color='{navy_primary.hexval()}'>General Remarks:</font></b><br/>{remarks_val.replace('\n', '<br/>')}"
        t_rem = Table([[Paragraph(remarks_html, cell_style)]], colWidths=[565])
        t_rem.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ice_blue_bg),
            ('BOX', (0,0), (-1,-1), 1, navy_primary),
            ('PADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t_rem)
        story.append(Spacer(1, 6))

        # PDF Signatures Section
        sig_title_style = ParagraphStyle('SigTitle', parent=styles['Normal'], fontSize=7.5, leading=9, textColor=navy_primary, fontName="Helvetica-Bold")
        sig_text_style = ParagraphStyle('SigText', parent=styles['Normal'], fontSize=7, leading=8.5, textColor=colors.HexColor("#475569"))

        sig_data = [
            [Paragraph("<b>Inspected & Prepared By:</b>", sig_title_style), Paragraph("<b>Customer Acknowledgment / Hospital Stamp:</b>", sig_title_style)],
            [Spacer(1, 16), Spacer(1, 16)],
            [Paragraph(f"........................................................<br/><b>Service Engineer:</b> {disp_engineer}<br/>Biomed International (Pvt) Ltd", sig_text_style),
             Paragraph("........................................................<br/><b>Authorized Signature & Stamp</b><br/>Hospital / Theatre Unit", sig_text_style)]
        ]

        t_sig = Table(sig_data, colWidths=[280, 285])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]))
        story.append(t_sig)

        doc.build(story)
        pdf_bytes = buffer.getvalue()

        for tf in temp_files:
            if os.path.exists(tf):
                os.remove(tf)

        all_descriptions = ", ".join([item.get("name", "") for item in instruments_data if item.get("name")])
        
        summary_payload = {
            "report_no": disp_rep_no,
            "date": date_str,
            "hospital": disp_hospital,
            "engineer": disp_engineer,
            "instrument_name": all_descriptions,
            "total_instruments": len(instruments_data),
            "replace_count": replace_count,
            "service_count": service_count,
            "logged_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        synced = sync_to_google_sheet(summary_payload)

        st.success("✅ PDF Generated with Enhanced High-Detail Photos & Synced!")

        st.download_button(
            "📥 Download PDF Report",
            data=pdf_bytes,
            file_name=f"Lap_Report_{disp_rep_no}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
            
        excel_bytes = generate_professional_excel(
            instruments_data=instruments_data,
            hospital_name=disp_hospital,
            engineer_name=disp_engineer,
            report_no=disp_rep_no,
            date_str=date_str
        )
        st.download_button(
            label="📊 Download Excel Summary",
            data=excel_bytes,
            file_name=f"Lap_Report_Summary_{disp_rep_no}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
