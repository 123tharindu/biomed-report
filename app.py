import streamlit as st
import pandas as pd
import datetime
import io
import os
import requests
from PIL import Image, ImageOps
from google import genai
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Image preview සඳහා pdf2image import කිරීම
try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Biomed International - AI Lap Scan Portal",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

LOGO_URL = "https://i.ibb.co/68v81yM/bmi-logo.png"

# --- MODERN CUSTOM CSS STYLING ---
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

# Initialize Gemini Client
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Hospitals List
SL_HOSPITALS = [
    "Sri Jayewardenepura General Hospital (SJGH)",
    "National Hospital of Sri Lanka (NHSL Colombo)",
    "Lady Ridgeway Hospital for Children (LRH)",
    "De Soysa Hospital for Women (Maternity)",
    "Castle Street Hospital for Women",
    "Colombo South Teaching Hospital (Kalubowila)",
    "Colombo North Teaching Hospital (Ragama)",
    "Asiri Central Hospital (Colombo 10)",
    "Asiri Surgical Hospital (Narahenpita)",
    "Lanka Hospitals (Narahenpita)",
    "Nawaloka Hospital (Colombo 02)",
    "Durdans Hospital (Colombo 03)",
    "National Hospital Kandy",
    "Teaching Hospital Peradeniya",
    "Teaching Hospital Karapitiya (Galle)",
    "Teaching Hospital Kurunegala",
    "District General Hospital Chilaw",
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

def process_and_compress_image(image_file, max_size=(800, 800)):
    img = Image.open(image_file)
    img = ImageOps.exif_transpose(img)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    return img

def analyze_damage_with_ai(image_file, item_name):
    if not client: return "API Key not configured properly.", "OK"
    try:
        compressed_img = process_and_compress_image(image_file, max_size=(800, 800))
        prompt = f"Examine surgical instrument '{item_name}' for damage. Line 1: Technical damage (Max 25 words). Line 2: Recommendation (Replace/Repair/Service/OK)."
        response = client.models.generate_content(model='gemini-2.0-flash', contents=[compressed_img, prompt])
        lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        return (lines[0] if len(lines) > 0 else "Inspected"), (lines[1] if len(lines) > 1 else "Service")
    except Exception as e:
        return f"AI Error: {str(e)}", "Service"

# --- PERSISTENT SESSION STATE INITIALIZATION ---
if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "hospital": SL_HOSPITALS[0],
        "manual_hospital": "",
        "date": datetime.date.today(),
        "engineer": "",
        "report_no": "",
        "department": "Theatre / Laparoscopy",
        "remarks": "All above instruments require official inspection and technical servicing.",
        "instruments": [{
            "art": "", "is_custom": False, "custom_art": "", "name": "",
            "damage": "", "recommendation": "Service", "tech_comment": "", "show_comment": False, "image": None
        }]
    }

if "saved_reports_history" not in st.session_state:
    st.session_state.saved_reports_history = []

# --- APP TABS ---
tab1, tab2 = st.tabs(["📝 Inspection Entry & PDF Generator", "📜 Saved Reports History"])

with tab1:
    h_col1, h_col2 = st.columns([1.2, 8.8])
    with h_col1:
        if os.path.exists("bmi_logo.png"): st.image("bmi_logo.png", width=100)
        else: st.image(LOGO_URL, width=100)
    with h_col2:
        st.markdown("<div class='brand-header'><h1>BIOMED INTERNATIONAL (PVT) LTD</h1><p>AESCULAP DIVISION — TECHNICAL INSPECTION & SCAN REPORT PORTAL</p></div>", unsafe_allow_html=True)

    # META INFORMATION
    st.sidebar.markdown("### 📋 Meta Information")
    st.session_state.form_data["hospital"] = st.sidebar.selectbox("Customer / Hospital", options=SL_HOSPITALS, index=SL_HOSPITALS.index(st.session_state.form_data["hospital"]) if st.session_state.form_data["hospital"] in SL_HOSPITALS else 0)
    
    if st.session_state.form_data["hospital"] == "Other (Type manually)":
        st.session_state.form_data["manual_hospital"] = st.sidebar.text_input("Enter Hospital Name Manually", value=st.session_state.form_data["manual_hospital"])
        hospital_name = st.session_state.form_data["manual_hospital"]
    else:
        hospital_name = st.session_state.form_data["hospital"]

    st.session_state.form_data["date"] = st.sidebar.date_input("Inspection Date", value=st.session_state.form_data["date"])
    st.session_state.form_data["engineer"] = st.sidebar.text_input("Engineer / Inspector Name", value=st.session_state.form_data["engineer"])
    st.session_state.form_data["report_no"] = st.sidebar.text_input("Report Reference No.", value=st.session_state.form_data["report_no"])
    st.session_state.form_data["department"] = st.sidebar.text_input("Department", value=st.session_state.form_data["department"])
    st.session_state.form_data["remarks"] = st.sidebar.text_area("General Remarks & Inspection Notes", value=st.session_state.form_data["remarks"], height=100)

    # INSTRUMENTS INPUT SECTION
    st.markdown("<div class='section-title'>🔬 Surgical Instruments Inspection Entry</div>", unsafe_allow_html=True)

    for i, inst in enumerate(st.session_state.form_data["instruments"]):
        st.markdown(f"<div class='instrument-card'><b>🔪 Instrument Entry #{i+1}</b>", unsafe_allow_html=True)
        col1, col2 = st.columns([1.2, 2.8])
        
        with col1:
            uploaded_img = st.file_uploader(f"Upload Image #{i+1}", type=["jpg", "png", "jpeg"], key=f"uploader_{i}")
            if uploaded_img:
                inst["image"] = uploaded_img
            if inst["image"]:
                st.image(inst["image"], width=200)

        with col2:
            inst["is_custom"] = st.checkbox("✍️ Custom Article No", value=inst["is_custom"], key=f"custom_chk_{i}")
            if inst["is_custom"]:
                inst["custom_art"] = st.text_input(f"Enter Article No #{i+1}", value=inst["custom_art"], key=f"c_art_{i}")
                final_art = inst["custom_art"]
            else:
                inst["art"] = st.selectbox(f"Search Master Catalog #{i+1}", options=[""] + article_options, index=article_options.index(inst["art"])+1 if inst["art"] in article_options else 0, key=f"s_art_{i}")
                final_art = inst["art"]
                if inst["art"] and not inst["name"]:
                    inst["name"] = catalog_dict.get(inst["art"], "")

            inst["name"] = st.text_input(f"Instrument Description #{i+1}", value=inst["name"], key=f"name_{i}")
            
            if inst["image"] and GEMINI_API_KEY:
                if st.button(f"✨ AI Auto-Detect Damage #{i+1}", key=f"ai_btn_{i}"):
                    with st.spinner("Analyzing with Gemini AI..."):
                        ai_dam, ai_rec = analyze_damage_with_ai(inst["image"], inst["name"])
                        inst["damage"] = ai_dam
                        inst["recommendation"] = ai_rec
                        st.rerun()

            selected_preset = st.selectbox(f"💡 Technical Fault Presets #{i+1}", options=DAMAGE_SUGGESTIONS, key=f"preset_{i}")
            if selected_preset and not selected_preset.startswith("--"):
                if selected_preset not in inst["damage"]:
                    inst["damage"] = f"{inst['damage']}\n{selected_preset}".strip()

            inst["damage"] = st.text_area(f"Damage Details #{i+1}", value=inst["damage"], height=80, key=f"dam_{i}")
            
            inst["show_comment"] = st.checkbox("📝 Include Engineer's Special Note", value=inst["show_comment"], key=f"sh_com_{i}")
            if inst["show_comment"]:
                inst["tech_comment"] = st.text_area(f"Engineer Note #{i+1}", value=inst["tech_comment"], height=60, key=f"com_{i}")

            rec_opts = ["Replace", "Service", "Repair", "Upgrade / New System Required", "OK"]
            inst["recommendation"] = st.selectbox(f"Recommendation #{i+1}", options=rec_opts, index=rec_opts.index(inst["recommendation"]) if inst["recommendation"] in rec_opts else 1, key=f"rec_{i}")

        st.markdown("</div>", unsafe_allow_html=True)

    col_add, col_rem, _ = st.columns([2, 2, 4])
    with col_add:
        if st.button("➕ Add Instrument"):
            st.session_state.form_data["instruments"].append({"art": "", "is_custom": False, "custom_art": "", "name": "", "damage": "", "recommendation": "Service", "tech_comment": "", "show_comment": False, "image": None})
            st.rerun()
    with col_rem:
        if len(st.session_state.form_data["instruments"]) > 1:
            if st.button("🗑️ Remove Last Instrument"):
                st.session_state.form_data["instruments"].pop()
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # PDF GENERATION
    if st.button("📄 Generate & Save Official PDF Report", type="primary", use_container_width=True):
        with st.spinner("Generating PDF Report..."):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=25, bottomMargin=25)
            story, styles = [], getSampleStyleSheet()
            temp_files = []

            navy_primary, navy_accent, ice_blue_bg = colors.HexColor('#0D2A4A'), colors.HexColor('#1E3A8A'), colors.HexColor('#F0F4F8')
            border_navy = colors.HexColor('#BAC7D5')
            
            company_name_style = ParagraphStyle('CompName', parent=styles['Heading1'], fontSize=11, leading=13, textColor=navy_primary, fontName='Helvetica-Bold')
            company_sub_style = ParagraphStyle('CompSub', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'))
            label_style = ParagraphStyle('LabelNavy', parent=styles['Normal'], fontSize=8, leading=10, textColor=navy_primary, fontName='Helvetica-Bold')
            value_style = ParagraphStyle('ValueText', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#1F2937'))
            cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=11)
            cell_center = ParagraphStyle('TableCellCenter', parent=cell_style, alignment=1)
            th_style = ParagraphStyle('TH', parent=cell_style, fontSize=7.5, leading=9, textColor=colors.white, fontName='Helvetica-Bold', alignment=1)

            # 1. Header Box
            company_info = [Paragraph("BIOMED INTERNATIONAL (PVT) LTD", company_name_style), Paragraph("AESCULAP Division | Colombo 03, Sri Lanka", company_sub_style)]
            logo_img = RLImage("bmi_logo.png", width=65, height=32) if os.path.exists("bmi_logo.png") else Paragraph("<b>BMI</b>", company_name_style)
            
            t_header = Table([[logo_img, company_info, [Paragraph("TECHNICAL INSPECTION REPORT", ParagraphStyle('T', parent=company_name_style, alignment=2)), Paragraph("LAP SCAN DIAGNOSTICS", ParagraphStyle('S', parent=company_sub_style, alignment=2))]]], colWidths=[70, 260, 205])
            t_header.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), ice_blue_bg), ('BOX', (0,0), (-1,-1), 1, navy_primary), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(t_header)
            story.append(Spacer(1, 8))

            # 2. Metadata Box (ADDED BACK)
            display_engineer = st.session_state.form_data["engineer"] if st.session_state.form_data["engineer"].strip() else "Biomed Technical Team"
            rep_no = st.session_state.form_data['report_no'] if st.session_state.form_data['report_no'] else "N/A"
            date_str = st.session_state.form_data['date'].strftime("%d %B %Y")
            
            meta_data = [
                [Paragraph("Customer / Hospital:", label_style), Paragraph(hospital_name, value_style), Paragraph("Brand:", label_style), Paragraph("Aesculap", value_style)],
                [Paragraph("Inspection Date:", label_style), Paragraph(date_str, value_style), Paragraph("System / Set:", label_style), Paragraph("Laparoscopy", value_style)],
                [Paragraph("Engineer Name:", label_style), Paragraph(display_engineer, value_style), Paragraph("Report No:", label_style), Paragraph(rep_no, value_style)],
                [Paragraph("Department:", label_style), Paragraph(st.session_state.form_data["department"], value_style), Paragraph("Scope S/N:", label_style), Paragraph("N/A", value_style)]
            ]
            t_meta = Table(meta_data, colWidths=[95, 172, 95, 173])
            t_meta.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 1, border_navy),
                ('INNERGRID', (0,0), (-1,-1), 0.5, border_navy),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(t_meta)
            story.append(Spacer(1, 10))

            # 3. Main Instruments Table (Widths Adjusted: Photo=95, Recommendation=105)
            table_data = [[
                Paragraph("#", th_style), 
                Paragraph("PHOTO", th_style), 
                Paragraph("ARTICLE NO", th_style), 
                Paragraph("INSTRUMENT NAME", th_style), 
                Paragraph("DETAILS OF DAMAGE", th_style), 
                Paragraph("RECOMMENDATION", th_style)
            ]]
            
            for idx, item in enumerate(st.session_state.form_data["instruments"]):
                img_cell = Paragraph("No Image", cell_center)
                if item["image"]:
                    t_path = f"temp_p_{idx}.jpg"
                    p_img = process_and_compress_image(item["image"])
                    p_img.convert("RGB").save(t_path, "JPEG")
                    img_cell = RLImage(t_path, width=85, height=85)
                    temp_files.append(t_path)

                art_no = item["custom_art"] if item["is_custom"] else item["art"]
                rec_color = "#C0392B" if item["recommendation"] == "Replace" else "#D35400" if item["recommendation"] in ["Service", "Repair"] else "#27AE60"
                
                table_data.append([
                    Paragraph(str(idx+1), cell_center), 
                    img_cell, 
                    Paragraph(f"<b>{art_no}</b>", cell_style),
                    Paragraph(item["name"], cell_style), 
                    Paragraph(item["damage"].replace('\n', '<br/>'), cell_style),
                    Paragraph(f"<b><font color='{rec_color}'>{item['recommendation'].upper()}</font></b>", cell_center)
                ])

            t_main = Table(table_data, colWidths=[18, 95, 70, 115, 132, 105])
            t_main.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), navy_primary), 
                ('GRID', (0,0), (-1,-1), 0.5, border_navy), 
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(t_main)
            story.append(Spacer(1, 10))

            # 4. Remarks
            remarks_html = f"<b><font color='{navy_primary.hexval()}'>General Remarks:</font></b><br/>{st.session_state.form_data['remarks'].replace('\n', '<br/>')}"
            t_rem = Table([[Paragraph(remarks_html, cell_style)]], colWidths=[535])
            t_rem.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), ice_blue_bg), ('BOX', (0,0), (-1,-1), 1, navy_primary), ('PADDING', (0,0), (-1,-1), 6)]))
            story.append(t_rem)

            doc.build(story)
            pdf_bytes = buffer.getvalue()
            
            for tf in temp_files:
                if os.path.exists(tf): os.remove(tf)

            st.session_state.saved_reports_history.append({
                "Report No": rep_no,
                "Hospital": hospital_name,
                "Date": str(st.session_state.form_data['date']),
                "Engineer": st.session_state.form_data['engineer'],
                "PDF Bytes": pdf_bytes
            })

            st.success("✅ Report Generated Successfully!")
            st.download_button("📥 Download Fixed PDF Report", data=pdf_bytes, file_name=f"Lap_Report_{rep_no}.pdf", mime="application/pdf")

with tab2:
    st.markdown("### 📜 Saved Reports History")
    if len(st.session_state.saved_reports_history) > 0:
        for idx, rep in enumerate(reversed(st.session_state.saved_reports_history)):
            with st.expander(f"📄 Report: {rep['Report No']} — {rep['Hospital']} ({rep['Date']})"):
                st.write(f"**Inspector / Engineer:** {rep['Engineer']}")
                st.download_button(f"📥 Download PDF ({rep['Report No']})", data=rep["PDF Bytes"], file_name=f"Report_{rep['Report No']}.pdf", mime="application/pdf", key=f"hist_dl_{idx}")
    else:
        st.info("තවම කිසිදු Report එකක් Save කර නොමැත.")
