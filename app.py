import streamlit as st
import pandas as pd
import datetime
import io
import os
from PIL import Image, ImageOps
from google import genai
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Page Config
st.set_page_config(page_title="Biomed International - AI Report Generator", page_icon="🏥", layout="wide")

# Initialize Gemini Client if API key is provided
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.sidebar.warning(f"Gemini API Init Error: {e}")

st.title("🏥 BIOMED INTERNATIONAL (PVT) LTD")
st.subheader("PROFESSIONAL LAP SCAN REPORT GENERATOR (AI-POWERED)")

# Comprehensive Sri Lankan Hospitals List (Government & Private)
SL_HOSPITALS = [
    "--- COLOMBO & SUBURBS ---",
    "National Hospital of Sri Lanka (NHSL Colombo)",
    "Lady Ridgeway Hospital for Children (LRH)",
    "De Soysa Hospital for Women (Maternity)",
    "Castle Street Hospital for Women",
    "Colombo South Teaching Hospital (Kalubowila)",
    "Colombo North Teaching Hospital (Ragama)",
    "National Institute of Mental Health (Angoda)",
    "National Cancer Institute (Apeksha Hospital Maharagama)",
    "National Dental Hospital (Maharagama)",
    "Base Hospital Homagama",
    "Base Hospital Avissawella",
    "Base Hospital Mulleriyawa",
    "Asiri Central Hospital (Colombo)",
    "Asiri Surgical Hospital (Colombo)",
    "Asiri Hospital Narahenpita",
    "Lanka Hospitals (Colombo)",
    "Nawaloka Hospital (Colombo)",
    "Durdans Hospital (Colombo)",
    "Kings Hospital (Colombo)",
    "Ninewells Hospital (Colombo)",
    "Park Hospital (Colombo)",
    "Hemass Hospital (Thalawathugoda)",
    "Pannipitiya Nursing Home",
    
    "--- KANDY & CENTRAL ---",
    "National Hospital Kandy",
    "Teaching Hospital Peradeniya",
    "Sirimavo Bandaranaike Specialized Children's Hospital",
    "District General Hospital Nuwara Eliya",
    "District General Hospital Matale",
    "Base Hospital Gampola",
    "Base Hospital Nawalapitiya",
    "Asiri Hospital Kandy",
    "Suwasevana Hospital Kandy",
    "Kandy Private Hospital",
    
    "--- SOUTHERN ---",
    "Teaching Hospital Karapitiya (Galle)",
    "Teaching Hospital Mahamodara (Maternity)",
    "District General Hospital Matara",
    "District General Hospital Hambantota",
    "Base Hospital Tangalle",
    "Base Hospital Balapitiya",
    "Base Hospital Elpitiya",
    "Ruhunu Hospital (Galle)",
    "Asiri Hospital Matara",
    "Co-operative Hospital Matara",
    
    "--- WESTERN (GAMPAHA & KALUTARA) ---",
    "District General Hospital Gampaha",
    "District General Hospital Negombo",
    "District General Hospital Kalutara",
    "Base Hospital Wathupitiwala",
    "Base Hospital Kiribathgoda",
    "Base Hospital Panadura",
    "Base Hospital Horana",
    "Hemas Hospital (Wattala)",
    "Nawaloka Hospital (Negombo)",
    "ArOGYA Hospital (Gampaha)",
    
    "--- NORTH WESTERN (KURUNEGALA & CHILAW) ---",
    "Teaching Hospital Kurunegala",
    "District General Hospital Chilaw",
    "Base Hospital Kuliyapitiya",
    "Base Hospital Dambadeniya",
    "Base Hospital Marawila",
    "Co-operative Hospital Kurunegala",
    "Central Hospital Kurunegala",
    
    "--- NORTHERN & EASTERN ---",
    "Teaching Hospital Jaffna",
    "Teaching Hospital Batticaloa",
    "District General Hospital Trincomalee",
    "District General Hospital Vavuniya",
    "District General Hospital Mannar",
    "District General Hospital Kilinochchi",
    "District General Hospital Mullaaitivu",
    "Base Hospital Kalmunai",
    "Northern Central Hospital (Jaffna)",
    
    "--- NORTH CENTRAL & SABARAGAMUWA ---",
    "Teaching Hospital Anuradhapura",
    "Teaching Hospital Ratnapura",
    "District General Hospital Polonnaruwa",
    "District General Hospital Kegalle",
    "Base Hospital Karawanella",
    "Base Hospital Mawanella",
    
    "--- UVA PROVINCE ---",
    "Provincial General Hospital Badulla",
    "District General Hospital Monaragala",
    "Base Hospital Bandarawela",
    "Base Hospital Diyatalawa",
    
    "--- OTHER / CUSTOM ---",
    "Other (Type manually)"
]

# Load Excel File
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
    except Exception as e:
        return {}

catalog_dict = load_catalog(EXCEL_FILE)
article_options = sorted(list(catalog_dict.keys()))

# AI Image Analysis Function using Gemini 2.5 Flash
def analyze_damage_with_ai(image_file, item_name):
    if not client:
        return "API Key not configured properly.", "OK"
    try:
        image = Image.open(image_file)
        image = ImageOps.exif_transpose(image) # Correct rotation for AI
        prompt = f"""
        You are an expert Biomedical Engineer inspecting a surgical instrument named '{item_name}'.
        Examine the provided image carefully and identify physical damage, cracks, dents, insulation damage, or wear and tear.

        Provide your analysis strictly in two lines:
        Line 1: Technical explanation of the damage (Maximum 20 words). If no damage, write "No visible defect/damage observed."
        Line 2: Single-word Recommendation (Choose strictly one: Replace, Repair, Service, or OK).
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, prompt]
        )
        lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        
        damage_text = lines[0] if len(lines) > 0 else "Inspection completed."
        rec_text = "OK"
        if len(lines) > 1:
            possible_rec = lines[1].replace("Line 2:", "").strip()
            for r in ["Replace", "Repair", "Service", "OK"]:
                if r.lower() in possible_rec.lower():
                    rec_text = r
                    break
        return damage_text, rec_text
    except Exception as e:
        return f"Auto-analysis failed: {str(e)}", "OK"

# Sidebar Inputs
st.sidebar.header("📋 Report Details")

selected_hospital = st.sidebar.selectbox("Customer / Hospital", options=SL_HOSPITALS, index=1)

if selected_hospital == "Other (Type manually)" or selected_hospital.startswith("---"):
    hospital_name = st.sidebar.text_input("Enter Hospital Name Manually", value="")
else:
    hospital_name = selected_hospital

selected_date = st.sidebar.date_input("Inspection Date", value=datetime.date.today())
inspection_date_str = selected_date.strftime("%d %B %Y")

technician_name = st.sidebar.selectbox(
    "Technician Name", 
    options=["Dinushan De Zoysa", "Ishan Kelum", "Biomed Technical Team"],
    index=0
)

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

def add_instrument():
    st.session_state.instruments_count += 1

def remove_instrument():
    if st.session_state.instruments_count > 1:
        st.session_state.instruments_count -= 1

instrument_entries = []

for i in range(st.session_state.instruments_count):
    st.markdown(f"#### 🔪 Instrument Entry #{i+1}")
    col1, col2 = st.columns([1, 2])
    
    if f"art_{i}" not in st.session_state:
        st.session_state[f"art_{i}"] = None
    if f"name_{i}" not in st.session_state:
        st.session_state[f"name_{i}"] = ""

    with col1:
        uploaded_file = st.file_uploader(f"Upload Photo #{i+1}", type=["jpg", "jpeg", "png"], key=f"img_{i}")
        
    with col2:
        if len(article_options) > 0:
            article_no = st.selectbox(
                f"Search & Select Article Number #{i+1}", 
                options=article_options, 
                index=None,
                placeholder="🔍 Type Article No here...",
                key=f"art_{i}", 
                on_change=update_instrument_name, 
                args=(i,)
            )
        else:
            article_no = st.text_input(f"Article Number #{i+1}", key=f"art_{i}")
            
        instrument_name = st.text_input(f"Instrument Name #{i+1}", key=f"name_{i}")

        # AI Auto Detect Button
        if uploaded_file and GEMINI_API_KEY:
            if st.button(f"🤖 AI Auto-Detect Damage for #{i+1}", key=f"ai_btn_{i}"):
                with st.spinner("Analyzing image with Gemini AI..."):
                    ai_damage, ai_rec = analyze_damage_with_ai(uploaded_file, instrument_name)
                    st.session_state[f"dam_{i}"] = ai_damage
                    st.session_state[f"rec_{i}"] = ai_rec
                    st.success("Analysis Complete!")

        damage_details = st.text_area(f"Details of Damage #{i+1}", key=f"dam_{i}", placeholder="Enter or AI-detect damage details...")
        
        # Recommendation Options
        rec_options = ["Replace", "Service", "Repair", "OK"]
        curr_rec = st.session_state.get(f"rec_{i}", "Service")
        rec_idx = rec_options.index(curr_rec) if curr_rec in rec_options else 1
        
        recommendation = st.selectbox(f"Recommendation #{i+1}", options=rec_options, index=rec_idx, key=f"rec_{i}")

    instrument_entries.append({
        "image": uploaded_file,
        "article_no": article_no if article_no else "",
        "instrument_name": instrument_name,
        "damage": damage_details,
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

# Generate PDF Section
if st.button("📄 Generate Professional PDF Report", type="primary", use_container_width=True):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=30, 
        leftMargin=30, 
        topMargin=30, 
        bottomMargin=30
    )
    story = []
    styles = getSampleStyleSheet()
    
    navy_primary = colors.HexColor('#0A2540')
    slate_bg = colors.HexColor('#F4F6F8')
    border_color = colors.HexColor('#D0D7DE')
    
    title_style = ParagraphStyle('HeaderTitle', parent=styles['Heading1'], fontSize=16, leading=18, textColor=navy_primary, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('HeaderSubtitle', parent=styles['Normal'], fontSize=11, leading=14, textColor=colors.HexColor('#555555'), fontName='Helvetica-Bold')
    th_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=1)
    cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#222222'), fontName='Helvetica')
    cell_center = ParagraphStyle('TableCellCenter', parent=cell_style, alignment=1)

    story.append(Paragraph("BIOMED INTERNATIONAL (PVT) LTD", title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("TECHNICAL INSPECTION & LAP SCAN REPORT", subtitle_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=navy_primary, spaceAfter=12))
    
    header_data = [
        [Paragraph("<b>Customer / Hospital:</b>", cell_style), Paragraph(hospital_name, cell_style), Paragraph("<b>Brand:</b>", cell_style), Paragraph("Aesculap", cell_style)],
        [Paragraph("<b>Inspection Date:</b>", cell_style), Paragraph(inspection_date_str, cell_style), Paragraph("<b>System / Set:</b>", cell_style), Paragraph("Laparoscopy", cell_style)],
        [Paragraph("<b>Technician Name:</b>", cell_style), Paragraph(technician_name, cell_style), Paragraph("<b>Scope Serial No:</b>", cell_style), Paragraph("N/A", cell_style)],
        [Paragraph("<b>Report No:</b>", cell_style), Paragraph(report_no, cell_style), Paragraph("<b>Camera System:</b>", cell_style), Paragraph("N/A", cell_style)],
        [Paragraph("<b>Department:</b>", cell_style), Paragraph(department, cell_style), Paragraph("<b>Light Source:</b>", cell_style), Paragraph("N/A", cell_style)]
    ]
    
    t_header = Table(header_data, colWidths=[110, 166, 110, 166])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), slate_bg),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 15))
    
    table_data = [[
        Paragraph("#", th_style), Paragraph("PHOTO", th_style), Paragraph("ARTICLE NO", th_style),
        Paragraph("INSTRUMENT NAME", th_style), Paragraph("DETAILS OF DAMAGE", th_style), Paragraph("RECOMMENDATION", th_style)
    ]]
    
    temp_files_to_remove = []
    
    for idx, item in enumerate(instrument_entries):
        img_obj = Paragraph("No Image", cell_center)
        if item["image"] is not None:
            temp_img_path = f"temp_inst_{idx}.png"
            
            # Auto-rotate photo based on EXIF metadata before embedding in PDF
            img = Image.open(item["image"])
            img = ImageOps.exif_transpose(img)
            img.save(temp_img_path)
            
            img_obj = RLImage(temp_img_path, width=65, height=65)
            temp_files_to_remove.append(temp_img_path)
            
        rec = item["recommendation"]
        rec_color = "#D9534F" if rec == "Replace" else ("#F0AD4E" if rec in ["Service", "Repair"] else "#5CB85C")
        rec_html = f"<b><font color='{rec_color}'>{rec.upper()}</font></b>"
            
        table_data.append([
            Paragraph(f"<b>{idx + 1}</b>", cell_center),
            img_obj,
            Paragraph(f"<b>{item['article_no']}</b>", cell_style),
            Paragraph(item["instrument_name"], cell_style),
            Paragraph(item["damage"].replace('\n', '<br/>'), cell_style),
            Paragraph(rec_html, cell_center)
        ])
    
    t_main = Table(table_data, colWidths=[24, 75, 95, 138, 130, 90])
    t_main.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy_primary),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    
    story.append(t_main)
    story.append(Spacer(1, 15))
    
    t_remarks = Table([[Paragraph(f"<b>General Remarks & Technical Observations:</b><br/>{remarks}", ParagraphStyle('Remarks', parent=cell_style, fontSize=8.5, leading=12))]], colWidths=[552])
    t_remarks.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), slate_bg), ('BOX', (0,0), (-1,-1), 1, border_color), ('PADDING', (0,0), (-1,-1), 8)]))
    story.append(t_remarks)
    story.append(Spacer(1, 20))
    
    t_sig = Table([[
        Paragraph(f"<b>Inspected By ({technician_name}):</b><br/><br/><br/>__________________________________<br/>Signature & Date", cell_style),
        Paragraph("<b>Verified By (Hospital Authority):</b><br/><br/><br/>__________________________________<br/>Signature & Stamp", cell_style)
    ]], colWidths=[276, 276])
    story.append(t_sig)
    
    doc.build(story)
    buffer.seek(0)
    
    for tf in temp_files_to_remove:
        if os.path.exists(tf):
            os.remove(tf)
        
    st.success("Executive PDF Report Generated!")
    st.download_button(
        label="📥 Download Professional PDF Report",
        data=buffer,
        file_name=f"Lap_Scan_Report_{report_no.replace('/', '_') if report_no else 'Executive'}.pdf",
        mime="application/pdf"
    )
