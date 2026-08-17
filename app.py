import base64
import datetime
import io
import os
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from PIL import Image, ImageOps

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
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Biomed International - AI Lap Scan Portal",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    .brand-header {
        background: linear-gradient(135deg, #0D2A4A 0%, #1E3A8A 100%);
        padding: 16px 20px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(13, 42, 74, 0.15);
        margin-bottom: 25px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
    }
    
    .brand-logo-title {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        min-width: 240px;
    }

    .brand-header h1 { 
        color: #FFFFFF !important; 
        font-size: 16px !important; 
        font-weight: 800 !important; 
        margin: 0 !important; 
        line-height: 1.2; 
    }

    .brand-header p { 
        color: #93C5FD !important; 
        font-size: 10px !important; 
        margin-top: 3px !important; 
        font-weight: 600; 
        letter-spacing: 0.3px; 
    }

    .status-badge {
        background-color: #FFFFFF; 
        color: #0D2A4A;
        padding: 5px 10px; 
        border-radius: 8px; 
        font-size: 10px;
        font-weight: 700; 
        text-align: center; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        white-space: nowrap;
    }

    .header-logo-box {
        background-color: #FFFFFF;
        padding: 4px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        height: 44px;
        width: 44px;
        flex-shrink: 0;
    }

    .header-logo-box img {
        max-height: 38px;
        max-width: 38px;
        object-fit: contain;
    }

    .instrument-card {
        background-color: #FFFFFF; border: 1px solid #E2E8F0;
        border-radius: 12px; padding: 18px; margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .section-title { font-size: 16px; font-weight: 700; color: #0D2A4A; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 16px; }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0D2A4A 0%, #1E3A8A 100%) !important;
        color: white !important; border: none !important; border-radius: 8px !important;
        padding: 12px 24px !important; font-weight: 600 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


def get_local_logo_base64(file_path="bmi_logo.png"):
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{encoded}"
        except Exception:
            pass
    return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzBEMkE0QSI+PHBhdGggZD0iTTE5IDNINWMtMS4xIDAtMiAuOS0yIDJ2MTRjMCAxLjEgLjkgMiAyIDJoMTRjMS4xIDAgMi0uOSAyLTJWNWMwLTE4MS0uOS0yLTItMnptLTIgMTAgaC00djRoLTJ2LTRIN3YtMmg0VjdoMnY0aDR2MnoiLz48L3N2Zz4="


LOGO_SRC = get_local_logo_base64("bmi_logo.png")

# ==========================================
# 2. GEMINI CLIENT SETUP & DATA LISTS
# ==========================================
GEMINI_API_KEY = st.secrets.get(
    "GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", "")
)
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
    "Other (Type manually)",
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
    "Pass Inspection: Instrument in optimal condition. No physical defect or operational damage observed.",
]

EXCEL_FILE = "Full Laparoscopy Articles Updated master file 07.07.2026.xlsx"


@st.cache_data
def load_catalog(file_path):
    try:
        import pandas as pd

        df = pd.read_excel(file_path)
        df.columns = [str(col).strip() for col in df.columns]
        art_col, desc_col = (
            df.columns[0],
            df.columns[1] if len(df.columns) > 1 else df.columns[0],
        )
        df = df.dropna(subset=[art_col])
        return dict(
            zip(
                df[art_col].astype(str).str.strip(),
                df[desc_col].astype(str).str.strip(),
            )
        )
    except Exception:
        return {
            "BB365R": "Scissors Curved 17mm",
            "BB074R": "Forceps Dissecting",
            "BC051R": "Needle Holder",
            "EK087P": "Sealing Cap",
        }


catalog_dict = load_catalog(EXCEL_FILE)
article_options = sorted(list(catalog_dict.keys()))


def process_and_compress_image(image_file, max_size=(600, 600)):
    img = Image.open(image_file)
    img = ImageOps.exif_transpose(img)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    return img


def analyze_damage_with_ai(image_file, item_name):
    if not client:
        return "API Key not configured properly.", "OK"
    try:
        compressed_img = process_and_compress_image(
            image_file, max_size=(600, 600)
        )
        prompt = f"Examine surgical instrument '{item_name}' for damage. Line 1: Technical damage (Max 20 words). Line 2: Recommendation (Replace/Repair/Service/OK)."

        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=[compressed_img, prompt]
        )
        lines = [
            line.strip()
            for line in response.text.strip().split("\n")
            if line.strip()
        ]
        return (lines[0] if len(lines) > 0 else "Inspected"), (
            lines[1] if len(lines) > 1 else "Service"
        )
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
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes
            )
        else:
            creds = Credentials.from_service_account_file(
                "credentials.json", scopes=scopes
            )
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
            summary_data.get("logged_at"),
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.warning(f"Google Sheet Sync Note: {e}")
        return False


def generate_professional_excel(
    instruments_data, hospital_name, engineer_name, report_no, date_str
):
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

    fill_navy = PatternFill(
        start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid"
    )
    fill_zebra = PatternFill(
        start_color=ICE_BLUE, end_color=ICE_BLUE, fill_type="solid"
    )
    fill_white = PatternFill(
        start_color=WHITE, end_color=WHITE, fill_type="solid"
    )

    align_center = Alignment(
        horizontal="center", vertical="center", wrap_text=True
    )
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    thin_border = Side(border_style="thin", color=BORDER_COLOR)
    cell_border = Border(
        left=thin_border, right=thin_border, top=thin_border, bottom=thin_border
    )

    ws.merge_cells("A1:F1")
    ws["A1"] = (
        "BIOMED INTERNATIONAL (PVT) LTD — TECHNICAL INSPECTION REPORT"
    )
    ws["A1"].font = font_title
    ws["A1"].fill = fill_navy
    ws["A1"].alignment = align_center
    ws.row_dimensions[1].height = 28

    meta_info = [
        ("Customer / Hospital:", hospital_name, "Inspection Date:", date_str),
        ("Engineer Name:", engineer_name, "Report Ref No:", report_no),
    ]

    for r_idx, row in enumerate(meta_info, start=3):
        ws.cell(row=r_idx, column=1, value=row[0]).font = font_bold
        ws.cell(row=r_idx, column=2, value=row[1]).font = font_data
        ws.cell(row=r_idx, column=4, value=row[2]).font = font_bold
        ws.cell(row=r_idx, column=5, value=row[3]).font = font_data
        ws.row_dimensions[r_idx].height = 20

    headers = [
        "#",
        "ARTICLE NO",
        "INSTRUMENT DESCRIPTION",
        "TECHNICAL DAMAGE DETAILS",
        "RECOMMENDATION",
        "STATUS",
    ]
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
        rec_font = Font(
            name="Arial",
            size=9,
            bold=True,
            color="B91C1C" if rec == "Replace" else "15803D",
        )

        row_data = [
            (idx + 1, align_center, font_data),
            (item.get("art_no", ""), align_center, font_bold),
            (item.get("name", ""), align_left, font_data),
            (item.get("damage", ""), align_left, font_data),
            (rec.upper(), align_center, rec_font),
            (status_text, align_center, font_data),
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


if "num_instruments" not in st.session_state:
    st.session_state.num_instruments = 1


def update_desc_callback(idx):
    sel_art = st.session_state.get(f"s_art_{idx}")
    if sel_art and sel_art in catalog_dict:
        st.session_state[f"name_{idx}"] = catalog_dict[sel_art]


# ==========================================
# 3. UI HEADER (SINGLE & RESPONSIVE)
# ==========================================
st.markdown(
    f"""
    <div class="brand-header">
        <div class="brand-logo-title">
            <div class="header-logo-box">
                <img src="{LOGO_SRC}" alt="Biomed Logo" />
            </div>
            <div>
                <h1>BIOMED INTERNATIONAL (PVT) LTD</h1>
                <p>AESCULAP DIVISION — TECHNICAL INSPECTION PORTAL</p>
            </div>
        </div>
        <div class="status-badge">
            System Status:<br><span style="color:#00875A;">Active</span>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

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
remarks_val = st.sidebar.text_area(
    "General Remarks & Inspection Notes",
    value="All above instruments require official inspection and technical servicing.",
    height=100,
)

st.markdown(
    "<div class='section-title'>🔬 Surgical Instruments Inspection Entry</div>",
    unsafe_allow_html=True,
)
