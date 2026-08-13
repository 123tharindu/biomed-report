import streamlit as st
import pandas as pd
import datetime
import io
import os
import requests
from PIL import Image, ImageOps
from google import genai
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Biomed International - AI Lap Scan Portal",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

LOGO_URL = "https://i.ibb.co/68v81yM/bmi-logo.png"

st.markdown("""
<style>
    .main { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    .brand-header {
        background: linear-gradient(135deg, #0D2A4A 0%, #1E3A8A 100%);
        padding: 16px 20px; border-radius: 10px; color: white;
        box-shadow: 0 4px 15px rgba(13, 42, 74, 0.15); margin-bottom: 20px;
    }
    .brand-header h1 { color: #FFFFFF !important; font-size: 22px !important; font-weight: 700 !important; margin: 0 !important; }
    .brand-header p { color: #93C5FD !important; font-size: 12px !important; margin-top: 3px !important; }
    .instrument-card {
        background-color: #FFFFFF; border: 1px solid #E2E8F0;
        border-radius: 12px; padding: 20px; margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .section-title { font-size: 16px; font-weight: 700; color: #0D2A4A; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 16px; }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0D2A4A 0%, #1E3A8A 100%) !important;
        color: white !important; border: none !important; border-radius: 8px !important;
        padding: 12px 24px !important; font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GEMINI CLIENT SETUP & DATA LISTS
# ==========================================
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SL_HOSPITALS = [
    "-- Select Hospital / Institute --",
    "National Hospital of Sri Lanka (NHSL Colombo)",
    "National Hospital Kandy",
    "Sri Jayewardenepura General Hospital (SJGH)",
    "Lady Ridgeway Hospital for Children (LRH)",
    "De Soysa Hospital for Women (Maternity)",
    "Castle Street Hospital for Women",
    "Apeksha Hospital Maharagama (National Cancer Institute)",
    "National Institute of Mental Health (Angoda)",
    "National Eye Hospital Colombo",
    "Chest Hospital Welisara",
    "Colombo South Teaching Hospital (Kalubowila)",
    "Colombo North Teaching Hospital (Ragama)",
    "Teaching Hospital Peradeniya",
    "Teaching Hospital Karapitiya (Galle)",
    "Teaching Hospital Kurunegala",
    "Teaching Hospital Jaffna",
    "Teaching Hospital Batticaloa",
    "Teaching Hospital Anuradhapura",
    "Teaching Hospital Kuliyapitiya",
    "Teaching Hospital Ratnapura",
    "Teaching Hospital Gampaha",
    "Teaching Hospital Kalutara",
    "District General Hospital Chilaw",
    "District General Hospital Negombo",
    "District General Hospital Matara",
    "District General Hospital Kegalle",
    "District General Hospital Avissawella",
    "District General Hospital Nuwara Eliya",
    "District General Hospital Hambantota",
    "District General Hospital Polonnaruwa",
    "District General Hospital Trincomalee",
    "District General Hospital Vavuniya",
    "District General Hospital Mannar",
    "District General Hospital Kilinochchi",
    "District General Hospital Mullaaitivu",
    "District General Hospital Monaragala",
    "District General Hospital Badulla",
    "District General Hospital Ampara",
    "District General Hospital Matale",
    "District General Hospital Gampaha",
    "District General Hospital Nawalapitiya",
    "Base Hospital Horana",
    "Base Hospital Panadura",
    "Base Hospital Homagama",
    "Base Hospital Wathupitiwala",
    "Base Hospital Kiribathgoda",
    "Base Hospital Mirigama",
    "Base Hospital Tangalle",
    "Base Hospital Elpitiya",
    "Base Hospital Balapitiya",
    "Base Hospital Puttalam",
    "Base Hospital Marawila",
    "Base Hospital Kuliyapitiya",
    "Base Hospital Dambulla",
    "Base Hospital Point Pedro",
    "Base Hospital Kantale",
    "Army Hospital Colombo (Narahenpita)",
    "Navy Hospital Welisara",
    "Air Force Hospital Katunayake",
    "Police Hospital Narahenpita",
    "Asiri Central Hospital (Colombo 10)",
    "Asiri Surgical Hospital (Narahenpita)",
    "Asiri Hospital Matara",
    "Asiri Hospital Kandy",
    "Lanka Hospitals (Narahenpita)",
    "Nawaloka Hospital (Colombo 02)",
    "Nawaloka Hospital Negombo",
    "Durdans Hospital (Colombo 03)",
    "Hemas Hospital Thalawathugoda",
    "Hemas Hospital Wattala",
    "Kings Hospital Colombo",
    "Ninewells Hospital Colombo",
    "Dr. Neville Fernando Teaching Hospital",
    "Joseph Fraser Memorial Hospital",
    "Pannipitiya Nursing Home",
    "Melsta Hospital Ragama",
    "Other (Type manually)"
]

DAMAGE_SUGGESTIONS = [
    "-- Select Detailed Technical Damage --",
    "Insulation Damage: Insulation layer cracked/peeled near the shaft tip. High risk of stray electrical current leaks (HF insulation failure).",
    "Shaft Deformation: Outer shaft tube is visibly bent/misaligned, causing severe internal friction and restricting jaw movement.",
    "Jaw Alignment Failure: Working jaws are misaligned with worn-out gripping teeth. Instrument fails to hold tissue securely.",
    "Scissor Blade Bluntness: Scissor blades show heavy dullness and burrs along the cutting edge. Fails clean cutting.",
    "Corrosion & Pitting: Severe pitting corrosion and rust stains observed near joints due to chemical sterilization.",
    "Pass Inspection: Instrument in optimal condition. No physical defect or operational damage observed."
]

EXCEL_FILE = "Full Laparoscopy Articles Updated master file 07.07.2026.xlsx"

@st.cache_data
def load_catalog(file_path):
    try:
        df = pd.read_excel(file_path)
        df.columns = [str(col).strip() for col in df.columns]
        art_col, desc_col = df.columns[0], df.columns[1] if len(df.columns) > 1 else df.columns[0]
        df = df.dropna(subset=[art_col])
        return dict(zip(df[art_col].astype(str).str.strip(), df[desc_col].astype(str).str.strip()))
    except Exception:
        return {}

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
        compressed_img = process_and_compress_image(image_file, max_size=(600, 600))
        prompt = f"Examine surgical instrument '{item_name}' for damage. Line 1: Technical damage (Max 20 words). Line 2: Recommendation (Replace/Repair/Service/OK)."
        
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=[compressed_img, prompt]
        )
        lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        return (lines[0] if len(lines) > 0 else "Inspected"), (lines[1] if len(lines) > 1 else "Service")
    except Exception as e:
        return f"AI Error: {str(e)}", "Service"

def sync_to_google_sheet(summary_data):
    webhook_url = st.secrets.get("WEBHOOK_URL", "")
    if webhook_url:
        try:
            requests.post(webhook_url, json=summary_data, timeout=10)
            return True
        except Exception as e:
            st.warning(f"Google Sheet Sync Warning: {e}")
            return False
    return False

if "num_instruments" not in st.session_state:
    st.session_state.num_instruments = 1

# Callback to Auto-update Description on Select
def update_desc_callback(idx):
    sel_art = st.session_state.get(f"s_art_{idx}")
    if sel_art and sel_art in catalog_dict:
        st.session_state[f"name_{idx}"] = catalog_dict[sel_art]

# ==========================================
# 3. UI HEADER & SIDEBAR
# ==========================================
h_col1, h_col2 = st.columns([1.2, 8.8])
with h_col1:
    if os.path.exists("bmi_logo.png"): 
        st.image("bmi_logo.png", width=100)
    else: 
        st.image(LOGO_URL, width=100)

with h_col2:
    st.markdown("<div class='brand-header'><h1>BIOMED INTERNATIONAL (PVT) LTD</h1><p>AESCULAP DIVISION — TECHNICAL INSPECTION REPORT PORTAL</p></div>", unsafe_allow_html=True)

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
remarks_val = st.sidebar.text_area("General Remarks & Inspection Notes", value="All above instruments require official inspection and technical servicing.", height=100)

st.markdown("<div class='section-title'>🔬 Surgical Instruments Inspection Entry</div>", unsafe_allow_html=True)

instruments_data = []

# ==========================================
# 4. INSTRUMENTS INPUT LOOP
# ==========================================
for i in range(st.session_state.num_instruments):
    st.markdown(f"<div class='instrument-card'><b>🔪 Instrument Entry #{i+1}</b>", unsafe_allow_html=True)
    col1, col2 = st.columns([1.2, 2.8])
    
    inst_item = {}
    with col1:
        inst_item["image"] = st.file_uploader(f"Upload Image #{i+1}", type=["jpg", "png", "jpeg"], key=f"uploader_{i}")
        if inst_item["image"]:
            st.image(inst_item["image"], width=180)

    with col2:
        is_custom = st.checkbox("✍️ Custom Article No", key=f"custom_chk_{i}")
        if is_custom:
            art_no = st.text_input(f"Enter Article No #{i+1}", key=f"c_art_{i}")
            inst_name = st.text_input(f"Instrument Description #{i+1}", key=f"name_{i}")
        else:
            art_no = st.selectbox(
                f"Search Master Catalog #{i+1}", 
                options=[""] + article_options, 
                key=f"s_art_{i}",
                on_change=update_desc_callback,
                args=(i,)
            )
            # Text input uses session_state value automatically
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

        inst_item["damage"] = st.text_area(f"Damage Details #{i+1}", key=f"dam_{i}", height=80)
        
        rec_opts = ["Replace", "Service", "Repair", "Upgrade / New System Required", "OK"]
        inst_item["recommendation"] = st.selectbox(f"Recommendation #{i+1}", options=rec_opts, key=f"rec_{i}")

    instruments_data.append(inst_item)
    st.markdown("</div>", unsafe_allow_html=True)

col_add, col_rem, _ = st.columns([2, 2, 4])
with col_add:
    if st.button("➕ Add Instrument"):
        st.session_state.num_instruments += 1
        st.rerun()
with col_rem:
    if st.session_state.num_instruments > 1:
        if st.button("🗑️ Remove Last Instrument"):
            st.session_state.num_instruments -= 1
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. GENERATE PDF & GOOGLE SHEET SYNC
# ==========================================
if st.button("📄 Generate PDF Report & Sync Summary", type="primary", use_container_width=True):
    with st.spinner("Generating PDF Report & Syncing to Google Sheet..."):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        story, styles = [], getSampleStyleSheet()
        temp_files = []

        navy_primary = colors.HexColor('#0D2A4A')
        ice_blue_bg = colors.HexColor('#F0F4F8')
        border_navy = colors.HexColor('#BAC7D5')
        
        company_name_style = ParagraphStyle('CompName', parent=styles['Heading1'], fontSize=11, leading=13, textColor=navy_primary, fontName='Helvetica-Bold')
        company_sub_style = ParagraphStyle('CompSub', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'))
        label_style = ParagraphStyle('LabelNavy', parent=styles['Normal'], fontSize=8, leading=10, textColor=navy_primary, fontName='Helvetica-Bold')
        value_style = ParagraphStyle('ValueText', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#1F2937'))
        cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=7.5, leading=10)
        cell_center = ParagraphStyle('TableCellCenter', parent=cell_style, alignment=1)
        th_style = ParagraphStyle('TH', parent=cell_style, fontSize=7, leading=9, textColor=colors.white, fontName='Helvetica-Bold', alignment=1)

        # PDF Header Box
        company_info = [Paragraph("BIOMED INTERNATIONAL (PVT) LTD", company_name_style), Paragraph("AESCULAP Division | Colombo 03, Sri Lanka", company_sub_style)]
        logo_img = RLImage("bmi_logo.png", width=65, height=32) if os.path.exists("bmi_logo.png") else Paragraph("<b>BMI</b>", company_name_style)
        
        t_header = Table([[logo_img, company_info, [Paragraph("TECHNICAL INSPECTION REPORT", ParagraphStyle('T', parent=company_name_style, alignment=2)), Paragraph("LAP SCAN DIAGNOSTICS", ParagraphStyle('S', parent=company_sub_style, alignment=2))]]], colWidths=[70, 285, 200])
        t_header.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), ice_blue_bg), ('BOX', (0,0), (-1,-1), 1, navy_primary), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        story.append(t_header)
        story.append(Spacer(1, 6))

        # PDF Metadata Box
        disp_hospital = hospital_name if hospital_name else "N/A"
        disp_engineer = engineer_val.strip() if engineer_val.strip() else "Biomed Technical Team"
        disp_rep_no = report_no_val.strip() if report_no_val.strip() else "N/A"
        date_str = date_val.strftime("%d %B %Y")
        
        meta_data = [
            [Paragraph("Customer / Hospital:", label_style), Paragraph(disp_hospital, value_style), Paragraph("Brand:", label_style), Paragraph("Aesculap", value_style)],
            [Paragraph("Inspection Date:", label_style), Paragraph(date_str, value_style), Paragraph("System / Set:", label_style), Paragraph("Laparoscopy", value_style)],
            [Paragraph("Engineer Name:", label_style), Paragraph(disp_engineer, value_style), Paragraph("Report No:", label_style), Paragraph(disp_rep_no, value_style)],
            [Paragraph("Department:", label_style), Paragraph(dept_val, value_style), Paragraph("Scope S/N:", label_style), Paragraph("N/A", value_style)]
        ]
        t_meta = Table(meta_data, colWidths=[100, 177, 100, 178])
        t_meta.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, border_navy),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_navy),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 8))

        # PDF Instruments Table
        table_data = [[
            Paragraph("#", th_style), 
            Paragraph("PHOTO", th_style), 
            Paragraph("ARTICLE NO", th_style), 
            Paragraph("INSTRUMENT NAME", th_style), 
            Paragraph("DETAILS OF DAMAGE", th_style), 
            Paragraph("RECOMMENDATION", th_style)
        ]]
        
        replace_count = 0
        service_count = 0

        for idx, item in enumerate(instruments_data):
            img_cell = Paragraph("No Image", cell_center)
            if item["image"]:
                t_path = f"temp_p_{idx}.jpg"
                p_img = process_and_compress_image(item["image"])
                p_img.convert("RGB").save(t_path, "JPEG")
                img_cell = RLImage(t_path, width=65, height=65)
                temp_files.append(t_path)

            rec_color = "#C0392B" if item["recommendation"] == "Replace" else "#D35400" if item["recommendation"] in ["Service", "Repair"] else "#27AE60"
            if item["recommendation"] == "Replace": replace_count += 1
            else: service_count += 1

            table_data.append([
                Paragraph(str(idx+1), cell_center), 
                img_cell, 
                Paragraph(f"<b>{item['art_no']}</b>", cell_style),
                Paragraph(item["name"], cell_style), 
                Paragraph(item["damage"].replace('\n', '<br/>'), cell_style),
                Paragraph(f"<b><font color='{rec_color}'>{item['recommendation'].upper()}</font></b>", cell_center)
            ])

        t_main = Table(table_data, colWidths=[20, 75, 70, 120, 170, 100])
        t_main.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), navy_primary), 
            ('GRID', (0,0), (-1,-1), 0.5, border_navy), 
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_main)
        story.append(Spacer(1, 8))

        # Remarks Box
        remarks_html = f"<b><font color='{navy_primary.hexval()}'>General Remarks:</font></b><br/>{remarks_val.replace('\n', '<br/>')}"
        t_rem = Table([[Paragraph(remarks_html, cell_style)]], colWidths=[555])
        t_rem.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), ice_blue_bg), ('BOX', (0,0), (-1,-1), 1, navy_primary), ('PADDING', (0,0), (-1,-1), 5)]))
        story.append(t_rem)
        story.append(Spacer(1, 15))

        # PDF Signatures Section (NEW ADDITION)
        sig_title_style = ParagraphStyle('SigTitle', parent=styles['Normal'], fontSize=8, leading=10, textColor=navy_primary, fontName='Helvetica-Bold')
        sig_text_style = ParagraphStyle('SigText', parent=styles['Normal'], fontSize=7.5, leading=9, textColor=colors.HexColor('#475569'))
        
        sig_data = [
            [
                Paragraph("<b>Inspected & Prepared By:</b>", sig_title_style),
                Paragraph("<b>Customer Acknowledgment / Hospital Stamp:</b>", sig_title_style)
            ],
            [
                Spacer(1, 30), # Space for physical signature
                Spacer(1, 30)
            ],
            [
                Paragraph(f"........................................................<br/><b>Service Engineer:</b> {disp_engineer}<br/>Biomed International (Pvt) Ltd", sig_text_style),
                Paragraph("........................................................<br/><b>Authorized Signature & Stamp</b><br/>Hospital / Theatre Unit", sig_text_style)
            ]
        ]
        
        t_sig = Table(sig_data, colWidths=[270, 285])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_sig)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        
        for tf in temp_files:
            if os.path.exists(tf): os.remove(tf)

        summary_payload = {
            "report_no": disp_rep_no,
            "date": date_str,
            "hospital": disp_hospital,
            "engineer": disp_engineer,
            "total_instruments": len(instruments_data),
            "replace_count": replace_count,
            "service_count": service_count,
            "logged_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        synced = sync_to_google_sheet(summary_payload)
        
        st.success("✅ PDF Report Generated & Summary Synced to Google Sheet!")
        st.download_button("📥 Download PDF Report", data=pdf_bytes, file_name=f"Lap_Report_{disp_rep_no}.pdf", mime="application/pdf")
