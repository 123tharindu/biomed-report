import streamlit as st
import pandas as pd
import datetime
import io
import os
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

# Page Config
st.set_page_config(page_title="Biomed International - AI Report Generator", page_icon="🏥", layout="wide")

# Initialize Gemini Client
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.sidebar.warning(f"Gemini API Init Error: {e}")

st.title("🏥 BIOMED INTERNATIONAL (PVT) LTD")
st.subheader("PROFESSIONAL LAP SCAN REPORT GENERATOR (AI-POWERED)")

# Comprehensive & Complete Sri Lankan Hospitals List (Categorized)
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
    "Divisional Hospital Padukka",
    "Divisional Hospital Hanwella",
    
    "--- COLOMBO & SUBURBS (PRIVATE) ---",
    "Asiri Central Hospital (Colombo 10)",
    "Asiri Surgical Hospital (Narahenpita)",
    "Asiri Hospital Narahenpita",
    "Lanka Hospitals (Narahenpita)",
    "Nawaloka Hospital (Colombo 02)",
    "Durdans Hospital (Colombo 03)",
    "Kings Hospital (Colombo 05)",
    "Ninewells Hospital (Narahenpita)",
    "Park Hospital (Colombo 05)",
    "Hemas Hospital (Thalawathugoda)",
    "Pannipitiya Nursing Home",
    "Dr. Neville Fernando Teaching Hospital (Malabe)",
    "Western Hospital (Colombo 08)",
    "Melsta Hospital (Ragama)",

    "--- GAMPAHA DISTRICT ---",
    "District General Hospital Gampaha",
    "District General Hospital Negombo",
    "Base Hospital Wathupitiwala",
    "Base Hospital Kiribathgoda",
    "Base Hospital Mirigama",
    "Base Hospital Minuwangoda",
    "Base Hospital Radawana",
    "Hemas Hospital (Wattala)",
    "Nawaloka Hospital (Negombo)",
    "AROGYA Hospital (Gampaha)",
    "Leela Hospital (Gampaha)",

    "--- KALUTARA DISTRICT ---",
    "Queensbury Hospital (Panadura)",
    "Kethumathie Maternity Hospital (Panadura)",
    "District General Hospital Kalutara",
    "Base Hospital Panadura",
    "Base Hospital Horana",
    "Base Hospital Pimbura (Agalawatta)",
    "Divisional Hospital Bandaragama",
    "Divisional Hospital Mathugama",
    "Divisional Hospital Beruwala",
    "Divisional Hospital Ingiriya",
    "Divisional Hospital Neboda",
    "Medihelp Hospital (Panadura)",
    "Medihelp Hospital (Horana)",
    "Medihelp Hospital (Beruwala)",
    "Medihelp Hospital (Kalutara)",

    "--- KANDY & CENTRAL PROVINCE ---",
    "National Hospital Kandy",
    "Teaching Hospital Peradeniya",
    "Sirimavo Bandaranaike Specialized Children's Hospital (Peradeniya)",
    "District General Hospital Nuwara Eliya",
    "District General Hospital Matale",
    "Base Hospital Gampola",
    "Base Hospital Nawalapitiya",
    "Base Hospital Teldeniya",
    "Base Hospital Dambulla",
    "Base Hospital Rikillagaskada",
    "Asiri Hospital Kandy",
    "Suwasevana Hospital Kandy",
    "Kandy Private Hospital",
    "Seetha Hospital (Gampola)",

    "--- GALLE & SOUTHERN PROVINCE ---",
    "Queensbury Hospital (Galle)",
    "Teaching Hospital Karapitiya (Galle)",
    "Teaching Hospital Mahamodara (Maternity)",
    "District General Hospital Matara",
    "District General Hospital Hambantota",
    "Base Hospital Tangalle",
    "Base Hospital Balapitiya",
    "Base Hospital Elpitiya",
    "Base Hospital Udugama",
    "Base Hospital Deniyaya",
    "Base Hospital Kamburupitiya",
    "Base Hospital Walasmulla",
    "Ruhunu Hospital (Galle)",
    "Asiri Hospital Matara",
    "Co-operative Hospital Matara",
    "Mohotti Private Hospital (Matara)",

    "--- NORTH WESTERN (KURUNEGALA & CHILAW) ---",
    "Teaching Hospital Kurunegala",
    "District General Hospital Chilaw",
    "Base Hospital Kuliyapitiya",
    "Base Hospital Dambadeniya",
    "Base Hospital Marawila",
    "Base Hospital Nikaweratiya",
    "Base Hospital Giriulla",
    "Base Hospital Maho",
    "Co-operative Hospital Kurunegala",
    "Central Hospital Kurunegala",
    "Setmill Hospital (Kurunegala)",

    "--- NORTHERN PROVINCE ---",
    "Teaching Hospital Jaffna",
    "District General Hospital Vavuniya",
    "District General Hospital Mannar",
    "District General Hospital Kilinochchi",
    "District General Hospital Mullaaitivu",
    "Base Hospital Point Pedro",
    "Base Hospital Tellippalai",
    "Base Hospital Kayts",
    "Base Hospital Chavakachcheri",
    "Northern Central Hospital (Jaffna)",
    "Yarl Hospital (Jaffna)",

    "--- EASTERN PROVINCE ---",
    "Teaching Hospital Batticaloa",
    "District General Hospital Trincomalee",
    "District General Hospital Ampara",
    "Base Hospital Kalmunai (North & South)",
    "Base Hospital Kantale",
    "Base Hospital Muthur",
    "Base Hospital Mahaoya",
    "Base Hospital Pottuvil",
    "Base Hospital Valachchenai",

    "--- NORTH CENTRAL PROVINCE ---",
    "Teaching Hospital Anuradhapura",
    "District General Hospital Polonnaruwa",
    "Base Hospital Thambuttegama",
    "Base Hospital Kebithigollewa",
    "Base Hospital Padaviya",
    "Base Hospital Medirigiriya",
    "Base Hospital Hingurakgoda",

    "--- SABARAGAMUWA PROVINCE ---",
    "Teaching Hospital Ratnapura",
    "District General Hospital Kegalle",
    "Base Hospital Karawanella",
    "Base Hospital Mawanella",
    "Base Hospital Balangoda",
    "Base Hospital Kahawatta",
    "Base Hospital Embilipitiya",
    "Divisional Hospital Warakapola",

    "--- UVA PROVINCE ---",
    "Provincial General Hospital Badulla",
    "District General Hospital Monaragala",
    "Base Hospital Bandarawela",
    "Base Hospital Diyatalawa",
    "Base Hospital Mahiyanganaya",
    "Base Hospital Welimada",
    "Base Hospital Bibile",
    "Base Hospital Wellawaya",

    "--- TRI-FORCES & ACADEMIC HOSPITALS ---",
    "Kotelawala Defence University Hospital (KDU Werahera)",
    "Army Hospital (Colombo Narahenpita)",
    "Army Hospital (Panagoda)",
    "Navy Hospital (Colombo / Welisara)",
    "Air Force Hospital (Katunayake)",
    "Police Hospital (Narahenpita)",

    "--- OTHER / CUSTOM ---",
    "Other (Type manually)"
]

# Detailed Technical Damage Suggestions
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
    "Spring & Tension Issue: Internal handle spring mechanism is broken or lost tension. Handle fails to return to neutral open position automatically.",
    "Handle Joint Wear: Connecting linkages between handle and inner rod show excessive wear, reducing force transmission to the jaws.",
    "Distal Lens Damage: Objective lens at the distal tip is scratched/cracked. Causes blurriness, distortion, and optical artifacts in the surgical field.",
    "Internal Moisture / Fogging: Internal optical sealing compromised. Severe internal fogging and moisture droplets observed inside optical tube when heated.",
    "Fiber Optic Bundle Damage: Multiple fiber optic light fibers broken inside scope tube. Optical image shows dark spots and reduced overall light brightness.",
    "Light Cable Fiber Breakage: High percentage of internal glass fiber bundles broken (>30%). Results in poor illumination and dark surgical view.",
    "Cable Connector Discoloration: Stainless steel light post connectors burnt and discolored from excessive heat; degraded light entry coupling.",
    "Corrosion & Pitting: Severe pitting corrosion, rust stains, and surface oxidation observed near joints and laser markings due to improper chemical sterilization.",
    "General Overhaul Required: Cumulative mechanical wear and friction across all moving components. Full servicing, alignment, and seal replacement needed.",
    "Pass Inspection: Instrument in optimal condition. No physical defect, electrical leak, or optical distortion observed during inspection."
]

# Load Excel Catalog File
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

# AI Image Analysis Function
def analyze_damage_with_ai(image_file, item_name):
    if not client:
        return "API Key not configured properly.", "OK"
    try:
        compressed_img = process_and_compress_image(image_file, max_size=(800, 800))
        
        prompt = f"""
        You are an expert Biomedical Engineer inspecting a surgical instrument named '{item_name}'.
        Examine the provided image carefully and identify physical damage, cracks, dents, insulation damage, or wear and tear.

        Provide your analysis strictly in two lines:
        Line 1: Detailed technical explanation of the damage (Maximum 25 words). Include defect & clinical risk. If no damage, write "No visible defect/damage observed."
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

# Sidebar Inputs
st.sidebar.header("📋 Report Details")

selected_hospital = st.sidebar.selectbox("Customer / Hospital", options=SL_HOSPITALS, index=1)

if selected_hospital == "Other (Type manually)" or selected_hospital.startswith("---"):
    hospital_name = st.sidebar.text_input("Enter Hospital Name Manually", value="")
else:
    hospital_name = selected_hospital

selected_date = st.sidebar.date_input("Inspection Date", value=datetime.date.today())
inspection_date_str = selected_date.strftime("%d %B %Y")

engineer_name = st.sidebar.text_input("Engineer / Inspector Name", value="", placeholder="Enter Engineer Name...")
report_no = st.sidebar.text_input("Report No.", value="")
department = st.sidebar.text_input("Department", value="Theatre / Laparoscopy")

st.divider()
st.header("🔬 Instruments List")

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
    st.markdown(f"#### 🔪 Instrument Entry #{i+1}")
    col1, col2 = st.columns([1, 2])
    
    # Initialize Session State Keys for Persistence
    if f"name_{i}" not in st.session_state:
        st.session_state[f"name_{i}"] = ""
    if f"dam_{i}" not in st.session_state:
        st.session_state[f"dam_{i}"] = ""
    if f"tech_comm_{i}" not in st.session_state:
        st.session_state[f"tech_comm_{i}"] = ""
    if f"show_comm_{i}" not in st.session_state:
        st.session_state[f"show_comm_{i}"] = False

    with col1:
        uploaded_file = st.file_uploader(f"Upload Photo #{i+1}", type=["jpg", "jpeg", "png"], key=f"img_{i}")
        
    with col2:
        is_custom_art = st.checkbox("✍️ Type Custom Article No (Not in Master File)", key=f"is_custom_{i}")
        
        if is_custom_art:
            final_article_no = st.text_input(
                f"Enter Article Number #{i+1}", 
                key=f"manual_art_{i}", 
                placeholder="Type Article No manually here..."
            )
        else:
            selected_art = st.selectbox(
                f"Search & Select Article Number #{i+1}", 
                options=article_options, 
                index=None,
                placeholder="🔍 Search Article No from Master File...",
                key=f"art_{i}", 
                on_change=update_instrument_name, 
                args=(i,)
            )
            final_article_no = selected_art if selected_art else ""

        instrument_name = st.text_input(f"Instrument Name #{i+1}", key=f"name_{i}")

        if uploaded_file and GEMINI_API_KEY:
            if st.button(f"🤖 AI Auto-Detect Damage for #{i+1}", key=f"ai_btn_{i}"):
                with st.spinner("Analyzing image with Gemini AI..."):
                    ai_damage, ai_rec = analyze_damage_with_ai(uploaded_file, instrument_name)
                    st.session_state[f"dam_{i}"] = ai_damage
                    st.session_state[f"rec_{i}"] = ai_rec
                st.success("Analysis Complete!")

        st.selectbox(
            f"💡 Quick Damage Suggestions #{i+1}",
            options=DAMAGE_SUGGESTIONS,
            key=f"sug_{i}",
            on_change=update_damage_from_suggestion,
            args=(i,)
        )

        damage_details = st.text_area(
            f"Details of Damage #{i+1}", 
            key=f"dam_{i}", 
            placeholder="Select from detailed suggestions above, use AI, or type manually..."
        )

        # Optional Special Technical Comment Input
        show_comment = st.checkbox("📝 Add Special Technical Comment / Remarks", key=f"show_comm_{i}")
        tech_comment = ""
        if show_comment:
            tech_comment = st.text_area(
                f"Special Technical Comment #{i+1}", 
                key=f"tech_comm_{i}", 
                placeholder="Type special engineering comments, serial numbers, or notes here..."
            )

        # Recommendation options list with "Upgrade / New System Required"
        rec_options = ["Replace", "Service", "Repair", "Upgrade / New System Required", "OK"]
        curr_rec = st.session_state.get(f"rec_{i}", "Service")
        rec_idx = rec_options.index(curr_rec) if curr_rec in rec_options else 1
        
        recommendation = st.selectbox(f"Recommendation #{i+1}", options=rec_options, index=rec_idx, key=f"rec_{i}")

    instrument_entries.append({
        "image": uploaded_file,
        "article_no": final_article_no,
        "instrument_name": instrument_name,
        "damage": damage_details,
        "tech_comment": tech_comment if show_comment else "",
        "recommendation": recommendation
    })
    st.markdown("---")

col_add, col_remove, _ = st.columns([1.5, 1.5, 5])
with col_add:
    st.button("➕ Add Another Instrument", on_click=add_instrument, use_container_width=True)
with col_remove:
    if st.session_state.instruments_count > 1:
        st.button("🗑️ Remove Last Instrument", on_click=remove_instrument, use_container_width=True)

st.divider()

remarks = st.text_area("General Remarks", value="All above instruments require official inspection and technical servicing. Please review the recommended actions.")

# --- GENERATE PDF REPORT (A4 SIZE) ---
if st.button("📄 Generate Professional PDF Report", type="primary", use_container_width=True):
    with st.spinner("Generating PDF Report..."):
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
        
        # --- COLOR PALETTE ---
        navy_primary = colors.HexColor('#0D2A4A')
        navy_accent = colors.HexColor('#1E3A8A')
        ice_blue_bg = colors.HexColor('#F0F4F8')
        light_yellow_bg = colors.HexColor('#FEF9E7')
        border_navy = colors.HexColor('#BAC7D5')
        
        # --- PARAGRAPH STYLES ---
        company_name_style = ParagraphStyle('CompName', parent=styles['Heading1'], fontSize=15, leading=17, textColor=navy_primary, fontName='Helvetica-Bold')
        company_sub_style = ParagraphStyle('CompSub', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#475569'), fontName='Helvetica')
        
        report_title_style = ParagraphStyle('RepTitle', parent=styles['Normal'], fontSize=11, leading=13, textColor=navy_primary, fontName='Helvetica-Bold', alignment=2)
        report_sub_style = ParagraphStyle('RepSub', parent=styles['Normal'], fontSize=8, leading=10, textColor=navy_accent, fontName='Helvetica-Bold', alignment=2)

        label_style = ParagraphStyle('LabelNavy', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=navy_primary, fontName='Helvetica-Bold')
        value_style = ParagraphStyle('ValueText', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1F2937'), fontName='Helvetica')
        
        # Table Header Style
        th_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=8.0, leading=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=1)
        cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#222222'), fontName='Helvetica')
        cell_center = ParagraphStyle('TableCellCenter', parent=cell_style, alignment=1)

        # --- HEADER TABLE ---
        header_table_content = [
            [
                Paragraph("<b>BIOMED INTERNATIONAL (PVT) LTD</b>", company_name_style),
                Paragraph("TECHNICAL INSPECTION REPORT", report_title_style)
            ],
            [
                Paragraph("AESCULAP Division | No 2A Deal Place Colombo 03, Sri Lanka", company_sub_style),
                Paragraph("LAP SCAN & SERVICE DIAGNOSTICS", report_sub_style)
            ]
        ]
        
        t_custom_header = Table(header_table_content, colWidths=[315, 220])
        t_custom_header.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ice_blue_bg),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('BOX', (0,0), (-1,-1), 1, navy_primary),
            ('LINEBELOW', (0,1), (-1,1), 1.5, navy_primary)
        ]))
        
        story.append(t_custom_header)
        story.append(Spacer(1, 10))

        # --- METADATA HEADER BOX ---
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
        
        # --- INSTRUMENTS TABLE ---
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
                
                # Image Size 130x130
                img_obj = RLImage(temp_img_path, width=130, height=130)
                temp_files_to_remove.append(temp_img_path)
                
            rec = item["recommendation"]
            
            # Highlight Colors for Recommendation Status
            if rec == "Replace":
                rec_color = "#C0392B"  # Red
            elif rec in ["Service", "Repair"]:
                rec_color = "#D35400"  # Dark Orange
            elif rec == "Upgrade / New System Required":
                rec_color = "#E67E22"  # Orange
            else:
                rec_color = "#27AE60"  # Green (OK)

            rec_html = f"<b><font color='{rec_color}'>{rec.upper()}</font></b>"

            damage_text_formatted = item["damage"].replace('\n', '<br/>')
            
            # Collect Technical Comments for separate box below table
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
        
        # Table Layout
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

        # --- SPECIAL TECHNICAL COMMENTS BOX (If Any Exists) ---
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

        # --- GENERAL REMARKS BOX (FIXED TEXT OVERFLOW & PADDING) ---
        remarks_style = ParagraphStyle(
            'RemarksStyle', 
            parent=styles['Normal'], 
            fontSize=8.5, 
            leading=12,
            textColor=colors.HexColor('#222222'),
            fontName='Helvetica'
        )
        
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
        
        # Spacer for proper separation between Remarks & Signatures
        story.append(Spacer(1, 35))
        
        # --- SIGNATURE SECTION (KEEPTOGETHER FIX) ---
        sig_label_style = ParagraphStyle('SigLabel', parent=cell_style, fontSize=8.5, leading=12, textColor=navy_primary)
        t_sig = Table([[
            Paragraph(f"<b>Inspected By ({display_engineer}):</b><br/><br/><br/>__________________________________<br/>Signature & Date", sig_label_style),
            Paragraph("<b>Verified By (Hospital Authority):</b><br/><br/><br/>__________________________________<br/>Signature & Stamp", sig_label_style)
        ]], colWidths=[267, 268])
        
        story.append(KeepTogether([t_sig]))
        
        # --- WATERMARK (AESCULAP) & FOOTER FUNCTION ---
        def add_watermark_and_footer(canvas, doc):
            canvas.saveState()
            
            # Watermark (AESCULAP)
            canvas.setFont('Helvetica-Bold', 60)
            canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.25)) 
            canvas.translate(A4[0] / 2.0, A4[1] / 2.0)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, "AESCULAP")
            
            canvas.restoreState()
            
            # Footer
            canvas.saveState()
            canvas.setFont('Helvetica-BoldOblique', 8)
            canvas.setFillColor(colors.HexColor('#7F8C8D'))
            canvas.drawCentredString(A4[0] / 2.0, 15, "POWERED BY BIOMED INTERNATIONAL")
            canvas.restoreState()

        doc.build(story, onFirstPage=add_watermark_and_footer, onLaterPages=add_watermark_and_footer)
        pdf_data = buffer.getvalue()
        
        # Cleanup Temp Images
        for tf in temp_files_to_remove:
            if os.path.exists(tf):
                os.remove(tf)

    st.success("Executive A4 PDF Report Generated!")
    
    # Live Preview (If pdf2image available)
    if PDF2IMAGE_AVAILABLE:
        try:
            preview_images = convert_from_bytes(pdf_data, first_page=1, last_page=1)
            if preview_images:
                st.subheader("🖼️ PDF Live Image Preview")
                st.image(preview_images[0], caption="Generated Technical Report Page 1", use_container_width=True)
        except Exception as preview_err:
            st.info("Download PDF to view official layout.")

    st.download_button(
        label="📥 Download Professional PDF Report (A4)",
        data=pdf_data,
        file_name=f"Lap_Scan_Report_{report_no.replace('/', '_') if report_no else 'Executive'}.pdf",
        mime="application/pdf"
    )
