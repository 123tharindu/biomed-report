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

# BMI Logo Direct Link (Or local file path)
LOGO_URL = "https://i.ibb.co/68v81yM/bmi-logo.png"

# --- MODERN CUSTOM CSS STYLING ---
st.markdown("""
<style>
    .main {
        background-color: #F8FAFC;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .brand-header {
        background: linear-gradient(135deg, #0D2A4A 0%, #1E3A8A 100%);
        padding: 16px 20px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 15px rgba(13, 42, 74, 0.15);
        margin-bottom: 20px;
    }
    .brand-header h1 {
        color: #FFFFFF !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        margin: 0 !important;
        letter-spacing: 0.5px;
    }
    .brand-header p {
        color: #93C5FD !important;
        font-size: 12px !important;
        margin-top: 3px !important;
        font-weight: 500;
    }

    .instrument-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    
    .section-title {
        font-size: 16px;
        font-weight: 700;
        color: #0D2A4A;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0D2A4A 0%, #1E3A8A 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Gemini Client
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.sidebar.warning(f"Gemini API Init Error: {e}")

# --- BRAND HEADER WITH SMALL LOGO ---
header_col1, header_col2 = st.columns([0.8, 8.2])

with header_col1:
    # Local file 'bmi_logo.png' තිබේ නම් ඒකෙන්, නැතහොත් URL එකෙන් පොඩියට පෙන්වයි
    if os.path.exists("bmi_logo.png"):
        st.image("bmi_logo.png", width=75)
    else:
        try:
            st.image(LOGO_URL, width=75)
        except:
            st.write("🏥")

with header_col2:
    st.markdown("""
    <div class="brand-header">
        <div>
            <h1>BIOMED INTERNATIONAL (PVT) LTD</h1>
            <p>AESCULAP DIVISION — TECHNICAL INSPECTION & SCAN REPORT PORTAL</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Hospitals List
SL_HOSPITALS = [
    "--- COLOMBO & SUBURBS (GOVT / SEMI-GOVT) ---",
    "Sri Jayewardenepura General Hospital (SJGH)",
    "National Hospital of Sri Lanka (NHSL Colombo)",
    "Lady Ridgeway Hospital for Children (LRH)",
    "De Soysa Hospital for Women (Maternity)",
    "Castle Street Hospital for Women",
    "Colombo South Teaching Hospital (Kalubowila)",
    "Colombo North Teaching Hospital (Ragama)",
    "Homagama Base Hospital / Teaching Hospital",
    "National Institute of Mental Health (Angoda)",
    "National Cancer Institute (Apeksha Hospital Maharagama)",
    "National Dental Hospital (Maharagama)",
    "Base Hospital Avissawella",
    "Base Hospital Mulleriyawa",
    "Base Hospital Horana",
    "Base Hospital Piliyandala",
    
    "--- COLOMBO & SUBURBS (PRIVATE) ---",
    "Asiri Central Hospital (Colombo 10)",
    "Asiri Surgical Hospital (Narahenpita)",
    "Asiri Hospital Narahenpita",
    "Lanka Hospitals (Narahenpita)",
    "Nawaloka Hospital (Colombo 02)",
    "Durdans Hospital (Colombo 03)",
    "Kings Hospital (Colombo 05)",
    "Ninewells Hospital (Narahenpita)",
    "Hemas Hospital (Thalawathugoda)",

    "--- GAMPAHA DISTRICT ---",
    "District General Hospital Gampaha",
    "District General Hospital Negombo",
    "Base Hospital Wathupitiwala",
    "Hemas Hospital (Wattala)",

    "--- KANDY & CENTRAL PROVINCE ---",
    "National Hospital Kandy",
    "Teaching Hospital Peradeniya",
    "District General Hospital Nuwara Eliya",
    "District General Hospital Matale",

    "--- GALLE & SOUTHERN PROVINCE ---",
    "Teaching Hospital Karapitiya (Galle)",
    "District General Hospital Matara",
    "District General Hospital Hambantota",

    "--- NORTH WESTERN (KURUNEGALA & CHILAW) ---",
    "Teaching Hospital Kurunegala",
    "District General Hospital Chilaw",

    "--- OTHER / CUSTOM ---",
    "Other (Type manually)"
]

DAMAGE_SUGGESTIONS = [
    "-- Select Detailed Technical Damage --",
    "Insulation Damage: Insulation layer cracked/peeled near the shaft tip. High risk of stray electrical current leaks (HF insulation failure) during diathermy.",
    "Insulation Burn: High-voltage insulation micro-cracks and surface burns detected along the shaft. Requires immediate re-insulation before clinical use.",
    "Shaft Deformation: Outer shaft tube is visibly bent/misaligned, causing severe internal friction and restricting smooth jaw articulation.",
    "Jaw Alignment Failure: Working jaws are misaligned with worn-out gripping teeth. Instrument fails to hold tissue securely during retraction.",
    "Scissor Blade Bluntness: Scissor blades show heavy dullness, notches, and burrs along the cutting edge. Tissue slipping observed; fails clean cutting.",
    "Jaw Joint Play: Excessive mechanical play and looseness at the distal joint pin. Causes uneven jaw closing force and unstable grip.",
    "Bipolar/Monopolar Tip Wear: Coagulation tips show severe thermal pitting, carbon deposits, and eroded conductive surfaces.",
    "Ratchet Lock Failure: Lock mechanism/ratchet teeth are severely worn out. Handle fails to hold locking position under tension, slipping during use.",
    "Corrosion & Pitting: Severe pitting corrosion, rust stains, and surface oxidation observed near joints due to improper chemical sterilization.",
    "General Overhaul Required: Cumulative mechanical wear and friction across all moving components. Full servicing, alignment, and seal replacement needed.",
    "Pass Inspection: Instrument in optimal condition. No physical defect, electrical leak, or optical distortion observed during inspection."
]

EXCEL_FILE = "Full Laparoscopy Articles Updated master file 07.07.2026.xlsx"

@st.cache_data
def load_catalog(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name='Master File')
        df.columns = ['Article', 'Description']
        df = df.dropna(subset=['Article', 'Description'])
        df['Article'] = df['Article'].astype(str).str.strip()
        df['Description'] = df['Description'].astype(str).str.strip()
        return dict(zip(df['Article'], df['Description']))
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
    if not client:
        return "API Key not configured properly.", "OK"
    try:
        compressed_img = process_and_compress_image(image_file, max_size=(800, 800))
        prompt = f"""
        You are an expert Biomedical Engineer inspecting a surgical instrument named '{item_name}'.
        Examine the provided image carefully and identify physical damage, cracks, dents, insulation damage, or wear and tear.

        Provide your analysis strictly in two lines:
        Line 1: Detailed technical explanation of the damage (Maximum 25 words).
        Line 2: Single-word Recommendation (Choose strictly one: Replace, Repair, Service, Upgrade / New System Required, or OK).
        """
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[compressed_img, prompt]
        )
        lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        
        damage_text = lines[0] if len(lines) > 0 else "Inspection completed."
        rec_text = "OK"
        if len(lines) > 1:
            possible_rec = lines[1].replace("Line 2:", "").strip()
            for r in ["Replace", "Repair", "Service", "Upgrade / New System Required", "OK"]:
                if r.lower() in possible_rec.lower():
                    rec_text = r
                    break
        return damage_text, rec_text
    except Exception as e:
        return f"Auto-analysis unavailable: {str(e)}", "OK"

# --- SIDEBAR DESIGN ---
st.sidebar.markdown("### 📋 Meta Information")
selected_hospital = st.sidebar.selectbox("Customer / Hospital", options=SL_HOSPITALS, index=1)

if selected_hospital == "Other (Type manually)" or selected_hospital.startswith("---"):
    hospital_name = st.sidebar.text_input("Enter Hospital Name Manually", value="")
else:
    hospital_name = selected_hospital

selected_date = st.sidebar.date_input("Inspection Date", value=datetime.date.today())
inspection_date_str = selected_date.strftime("%d %B %Y")

engineer_name = st.sidebar.text_input("Engineer / Inspector Name", value="", placeholder="e.g. Ishan / Dinushan")
report_no = st.sidebar.text_input("Report Reference No.", value="", placeholder="e.g. SJGH/LAP/2026/01")
department = st.sidebar.text_input("Department", value="Theatre / Laparoscopy")

st.sidebar.markdown("---")
remarks = st.sidebar.text_area("General Remarks & Inspection Notes", value="All above instruments require official inspection and technical servicing. Please review the recommended actions.", height=120)

# --- MAIN DASHBOARD SECTION ---
st.markdown("<div class='section-title'>🔬 Surgical Instruments Inspection Entry</div>", unsafe_allow_html=True)

if "instruments_count" not in st.session_state:
    st.session_state.instruments_count = 1

def update_instrument_name(index):
    selected_art = st.session_state.get(f"art_{index}")
    if selected_art:
        st.session_state[f"name_{index}"] = catalog_dict.get(selected_art, "")

def update_damage_from_suggestion(index):
    selected_sug = st.session_state.get(f"sug_{index}")
    if selected_sug and not selected_sug.startswith("--"):
        existing = st.session_state.get(f"dam_{index}", "")
        st.session_state[f"dam_{index}"] = selected_sug if not existing else f"{existing}\n{selected_sug}"

def add_instrument():
    st.session_state.instruments_count += 1

def remove_instrument():
    if st.session_state.instruments_count > 1:
        st.session_state.instruments_count -= 1

instrument_entries = []

for i in range(st.session_state.instruments_count):
    st.markdown(f"""
    <div class="instrument-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <span style="font-weight: 700; color: #0D2A4A; font-size: 15px;">🔪 Instrument Entry #{i+1}</span>
            <span style="font-size: 12px; color: #64748B;">Item Reference #{i+1:02d}</span>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    if f"name_{i}" not in st.session_state:
        st.session_state[f"name_{i}"] = ""
    if f"dam_{i}" not in st.session_state:
        st.session_state[f"dam_{i}"] = ""
    if f"tech_comm_{i}" not in st.session_state:
        st.session_state[f"tech_comm_{i}"] = ""
    if f"show_comm_{i}" not in st.session_state:
        st.session_state[f"show_comm_{i}"] = False

    with col1:
        uploaded_file = st.file_uploader(f"Upload Instrument Image #{i+1}", type=["jpg", "jpeg", "png"], key=f"img_{i}")
        if uploaded_file:
            st.image(uploaded_file, caption=f"Preview #{i+1}", use_container_width=True)

    with col2:
        is_custom_art = st.checkbox("✍️ Custom Article No (Not in Master List)", key=f"is_custom_{i}")
        
        if is_custom_art:
            final_article_no = st.text_input(f"Enter Article No #{i+1}", key=f"manual_art_{i}", placeholder="Type Article No...")
        else:
            selected_art = st.selectbox(
                f"Search Master Catalog Article No #{i+1}", 
                options=article_options, 
                index=None,
                placeholder="🔍 Type or Select Article Number...",
                key=f"art_{i}", 
                on_change=update_instrument_name, 
                args=(i,)
            )
            final_article_no = selected_art if selected_art else ""

        instrument_name = st.text_input(f"Instrument Description #{i+1}", key=f"name_{i}")

        if uploaded_file and GEMINI_API_KEY:
            if st.button(f"✨ AI Auto-Detect Technical Damage", key=f"ai_btn_{i}"):
                with st.spinner("AI Analysis in progress..."):
                    ai_damage, ai_rec = analyze_damage_with_ai(uploaded_file, instrument_name)
                    st.session_state[f"dam_{i}"] = ai_damage
                    st.session_state[f"rec_{i}"] = ai_rec
                st.success("Analysis Applied!")

        st.selectbox(
            f"💡 Technical Fault Presets #{i+1}",
            options=DAMAGE_SUGGESTIONS,
            key=f"sug_{i}",
            on_change=update_damage_from_suggestion,
            args=(i,)
        )

        damage_details = st.text_area(f"Technical Inspection Notes / Damage Details #{i+1}", key=f"dam_{i}", height=90)

        show_comment = st.checkbox("📝 Include Engineer's Special Note", key=f"show_comm_{i}")
        tech_comment = ""
        if show_comment:
            tech_comment = st.text_area(f"Special Technical Comment #{i+1}", key=f"tech_comm_{i}", height=70)

        rec_options = ["Replace", "Service", "Repair", "Upgrade / New System Required", "OK"]
        curr_rec = st.session_state.get(f"rec_{i}", "Service")
        rec_idx = rec_options.index(curr_rec) if curr_rec in rec_options else 1
        
        recommendation = st.selectbox(f"Engineering Recommendation #{i+1}", options=rec_options, index=rec_idx, key=f"rec_{i}")

    st.markdown("</div>", unsafe_allow_html=True)

    instrument_entries.append({
        "image": uploaded_file,
        "article_no": final_article_no,
        "instrument_name": instrument_name,
        "damage": damage_details,
        "tech_comment": tech_comment if show_comment else "",
        "recommendation": recommendation
    })

col_add, col_remove, _ = st.columns([2, 2, 4])
with col_add:
    st.button("➕ Add Instrument", on_click=add_instrument, use_container_width=True)
with col_remove:
    if st.session_state.instruments_count > 1:
        st.button("🗑️ Remove Instrument", on_click=remove_instrument, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- GENERATE PDF REPORT ACTION ---
if st.button("📄 Generate & Export Executive PDF Report (A4)", type="primary", use_container_width=True):
    with st.spinner("Compiling & Generating Official PDF Document..."):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=30, 
            leftMargin=30, 
            topMargin=25, 
            bottomMargin=25
        )
        story = []
        styles = getSampleStyleSheet()
        temp_files_to_remove = []
        
        navy_primary = colors.HexColor('#0D2A4A')
        navy_accent = colors.HexColor('#1E3A8A')
        ice_blue_bg = colors.HexColor('#F0F4F8')
        light_yellow_bg = colors.HexColor('#FEF9E7')
        border_navy = colors.HexColor('#BAC7D5')
        
        company_name_style = ParagraphStyle('CompName', parent=styles['Heading1'], fontSize=13, leading=15, textColor=navy_primary, fontName='Helvetica-Bold')
        company_sub_style = ParagraphStyle('CompSub', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), fontName='Helvetica')
        
        report_title_style = ParagraphStyle('RepTitle', parent=styles['Normal'], fontSize=10.5, leading=12, textColor=navy_primary, fontName='Helvetica-Bold', alignment=2)
        report_sub_style = ParagraphStyle('RepSub', parent=styles['Normal'], fontSize=7.5, leading=9, textColor=navy_accent, fontName='Helvetica-Bold', alignment=2)

        label_style = ParagraphStyle('LabelNavy', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=navy_primary, fontName='Helvetica-Bold')
        value_style = ParagraphStyle('ValueText', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1F2937'), fontName='Helvetica')
        
        th_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=8.0, leading=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=1)
        cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#222222'), fontName='Helvetica')
        cell_center = ParagraphStyle('TableCellCenter', parent=cell_style, alignment=1)

        company_info_block = [
            Paragraph("<b>BIOMED INTERNATIONAL (PVT) LTD</b>", company_name_style),
            Paragraph("AESCULAP Division | No 2A Deal Place Colombo 03, Sri Lanka", company_sub_style)
        ]

        # PDF Logo Handle (Small Size - Width 45, Height 22)
        logo_obj = None
        if os.path.exists("bmi_logo.png"):
            logo_obj = RLImage("bmi_logo.png", width=45, height=22)
        else:
            try:
                img_data = requests.get(LOGO_URL, timeout=3).content
                logo_io = io.BytesIO(img_data)
                logo_obj = RLImage(logo_io, width=45, height=22)
            except:
                logo_obj = Paragraph("<b>BMI</b>", company_name_style)

        header_table_content = [
            [
                logo_obj,
                company_info_block,
                [
                    Paragraph("TECHNICAL INSPECTION REPORT", report_title_style),
                    Paragraph("LAP SCAN & SERVICE DIAGNOSTICS", report_sub_style)
                ]
            ]
        ]
        
        t_custom_header = Table(header_table_content, colWidths=[50, 265, 220])
        t_custom_header.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ice_blue_bg),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 1, navy_primary),
            ('LINEBELOW', (0,-1), (-1,-1), 1.5, navy_primary)
        ]))
        
        story.append(t_custom_header)
        story.append(Spacer(1, 10))

        # Metadata Header Box
        display_engineer = engineer_name if engineer_name.strip() else "Biomed Technical Team"
        header_data = [
            [Paragraph("Customer / Hospital:", label_style), Paragraph(hospital_name, value_style), Paragraph("Brand:", label_style), Paragraph("Aesculap", value_style)],
            [Paragraph("Inspection Date:", label_style), Paragraph(inspection_date_str, value_style), Paragraph("System / Set:", label_style), Paragraph("Laparoscopy", value_style)],
            [Paragraph("Engineer Name:", label_style), Paragraph(display_engineer, value_style), Paragraph("Scope Serial No:", label_style), Paragraph("N/A", value_style)],
            [Paragraph("Report No:", label_style), Paragraph(report_no if report_no else "N/A", value_style), Paragraph("Camera System:", label_style), Paragraph("N/A", value_style)],
            [Paragraph("Department:", label_style), Paragraph(department, value_style), Paragraph("Light Source:", label_style), Paragraph("N/A", value_style)]
        ]
        
        t_header = Table(header_data, colWidths=[100, 167, 100, 168])
        t_header.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.white),
            ('BOX', (0,0), (-1,-1), 1, border_navy),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_navy),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 12))
        
        # Table Content
        table_data = [[
            Paragraph("#", th_style), 
            Paragraph("PHOTO", th_style), 
            Paragraph("ARTICLE NO", th_style),
            Paragraph("INSTRUMENT NAME", th_style), 
            Paragraph("DETAILS OF DAMAGE", th_style), 
            Paragraph("RECOMMENDATION", th_style)
        ]]
        
        tech_comments_list = []

        for idx, item in enumerate(instrument_entries):
            img_obj = Paragraph("No Image", cell_center)
            if item["image"] is not None:
                temp_img_path = f"temp_inst_{idx}.jpg"
                img = process_and_compress_image(item["image"], max_size=(800, 800))
                img = img.convert("RGB")
                img.save(temp_img_path, "JPEG", quality=90)
                
                img_obj = RLImage(temp_img_path, width=130, height=130)
                temp_files_to_remove.append(temp_img_path)
                
            rec = item["recommendation"]
            
            if rec == "Replace":
                rec_color = "#C0392B"
            elif rec in ["Service", "Repair"]:
                rec_color = "#D35400"
            elif rec == "Upgrade / New System Required":
                rec_color = "#E67E22"
            else:
                rec_color = "#27AE60"

            rec_html = f"<b><font color='{rec_color}'>{rec.upper()}</font></b>"
            damage_text_formatted = item["damage"].replace('\n', '<br/>')
            
            if item["tech_comment"].strip():
                art_str = f" ({item['article_no']})" if item['article_no'] else ""
                tech_comments_list.append(f"<b>Item #{idx+1}{art_str}:</b> {item['tech_comment'].replace('\n', '<br/>')}")

            table_data.append([
                Paragraph(f"<b>{idx + 1}</b>", cell_center),
                img_obj,
                Paragraph(f"<b>{item['article_no']}</b>", cell_style),
                Paragraph(item["instrument_name"], cell_style),
                Paragraph(damage_text_formatted, cell_style),
                Paragraph(rec_html, cell_center)
            ])
        
        t_main = Table(table_data, colWidths=[20, 135, 65, 100, 125, 90])
        t_main.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), navy_primary),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, border_navy),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        
        story.append(t_main)
        story.append(Spacer(1, 15))

        if tech_comments_list:
            tech_html = f"<b><font color='{navy_accent.hexval()}'>📝 Special Technical Comments & Observations:</font></b><br/>" + "<br/>".join(tech_comments_list)
            t_tech_comm = Table([[Paragraph(tech_html, ParagraphStyle('TechCommStyle', parent=cell_style, fontSize=8.5, leading=12))]], colWidths=[535])
            t_tech_comm.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), light_yellow_bg),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#D4AC0D')),
                ('PADDING', (0,0), (-1,-1), 8)
            ]))
            story.append(t_tech_comm)
            story.append(Spacer(1, 15))

        # General Remarks Box
        remarks_style = ParagraphStyle('RemarksStyle', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#222222'), fontName='Helvetica')
        remarks_html = f"<b><font color='{navy_primary.hexval()}'>General Remarks & Inspection Notes:</font></b><br/>{remarks.replace('\n', '<br/>')}"
        
        t_remarks = Table([[Paragraph(remarks_html, remarks_style)]], colWidths=[535])
        t_remarks.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ice_blue_bg),
            ('BOX', (0,0), (-1,-1), 1, navy_primary),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        story.append(t_remarks)
        story.append(Spacer(1, 35))
        
        # Signature Block
        sig_label_style = ParagraphStyle('SigLabel', parent=cell_style, fontSize=8.5, leading=12, textColor=navy_primary)
        t_sig = Table([[
            Paragraph(f"<b>Inspected By ({display_engineer}):</b><br/><br/><br/>__________________________________<br/>Signature & Date", sig_label_style),
            Paragraph("<b>Verified By (Hospital Authority):</b><br/><br/><br/>__________________________________<br/>Signature & Stamp", sig_label_style)
        ]], colWidths=[267, 268])
        
        story.append(KeepTogether([t_sig]))
        
        # Watermark & Footer
        def add_watermark_and_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica-Bold', 60)
            canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.25)) 
            canvas.translate(A4[0] / 2.0, A4[1] / 2.0)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, "AESCULAP")
            canvas.restoreState()
            
            canvas.saveState()
            canvas.setFont('Helvetica-BoldOblique', 8)
            canvas.setFillColor(colors.HexColor('#7F8C8D'))
            canvas.drawCentredString(A4[0] / 2.0, 15, "POWERED BY BIOMED INTERNATIONAL")
            canvas.restoreState()

        doc.build(story, onFirstPage=add_watermark_and_footer, onLaterPages=add_watermark_and_footer)
        pdf_data = buffer.getvalue()
        
        for tf in temp_files_to_remove:
            if os.path.exists(tf):
                os.remove(tf)

    st.success("Executive PDF Report Generated!")
    
    if PDF2IMAGE_AVAILABLE:
        try:
            preview_images = convert_from_bytes(pdf_data, first_page=1, last_page=1)
            if preview_images:
                st.subheader("🖼️ Live Document Preview")
                st.image(preview_images[0], caption="Generated Document Layout Preview", use_container_width=True)
        except Exception:
            pass

    st.download_button(
        label="📥 Download Official PDF Report",
        data=pdf_data,
        file_name=f"Lap_Scan_Report_{report_no.replace('/', '_') if report_no else 'Executive'}.pdf",
        mime="application/pdf"
    )
