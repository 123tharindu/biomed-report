import streamlit as st
import google.generativeai as genai
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import os

# Page Config
st.set_page_config(page_title="Biomed International - Lap Scan Report", page_icon="🏥", layout="wide")

st.title("🏥 BIOMED INTERNATIONAL (PVT) LTD")
st.subheader("LAP SCAN REPORT GENERATOR")

# Gemini API Configuration
GEMINI_API_KEY = "AQ.Ab8RN6JbpzCThvBcn30TyWb0CWus4Mofw5cdCbRq1NNI_fGyAQ"
genai.configure(api_key=GEMINI_API_KEY)

# Load Excel File Automatically from GitHub Repository
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

# Sidebar Inputs for Report Header Details
st.sidebar.header("📋 Report Header Details")
hospital_name = st.sidebar.text_input("Customer / Hospital", value="BH Dambadeniya")
inspection_date = st.sidebar.text_input("Inspection Date", value="22 July 2026")
technician_name = st.sidebar.text_input("Technician Name", value="Biomed Technical Team")
report_no = st.sidebar.text_input("Report No.", value="BMI/LAP/2026/0527")
department = st.sidebar.text_input("Department", value="Theatre / Laparoscopy")

st.divider()
st.header("🔬 Add Instrument Entry")

# Instrument Entry Inputs
uploaded_file = st.file_uploader("Upload Instrument Photo", type=["jpg", "jpeg", "png"])

article_options = list(catalog_dict.keys())
if article_options:
    article_no = st.selectbox("Select Article Number", options=article_options)
    default_name = catalog_dict.get(article_no, "")
else:
    article_no = st.text_input("Article Number", value="PL718SU* / PL738SU**")
    default_name = "Custom Instrument Name"

instrument_name = st.text_input("Instrument Name (Auto-filled)", value=default_name)
damage_details = st.text_area("Details of Damage", value="• One jaw tip is bent.\n• Misalignment observed at the distal end.")
recommendation = st.selectbox("Recommendation", options=["Replace", "Service", "Repair", "OK"])

remarks = st.text_area("Remarks", value="All above instruments need service and functionality check. Please refer to the details and process the repairs.")

if st.button("📄 Generate Lap Scan Report (PDF)"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Title Header Style
    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#002060'),
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("<b>BIOMED INTERNATIONAL (PVT) LTD.</b>", title_style))
    story.append(Paragraph("<b>LAP SCAN REPORT</b>", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#002060'))))
    story.append(Spacer(1, 10))
    
    # Header Info Table
    header_data = [
        [Paragraph("<b>Customer / Hospital :</b>", styles['Normal']), Paragraph(hospital_name, styles['Normal']), Paragraph("<b>Brand :</b>", styles['Normal']), Paragraph("Aesculap", styles['Normal'])],
        [Paragraph("<b>Inspection Date :</b>", styles['Normal']), Paragraph(inspection_date, styles['Normal']), Paragraph("<b>System / Set :</b>", styles['Normal']), Paragraph("Laparoscopy", styles['Normal'])],
        [Paragraph("<b>Technician Name :</b>", styles['Normal']), Paragraph(technician_name, styles['Normal']), Paragraph("<b>Scope Serial No. :</b>", styles['Normal']), Paragraph("N/A", styles['Normal'])],
        [Paragraph("<b>Report No. :</b>", styles['Normal']), Paragraph(report_no, styles['Normal']), Paragraph("<b>Camera System :</b>", styles['Normal']), Paragraph("N/A", styles['Normal'])],
        [Paragraph("<b>Department :</b>", styles['Normal']), Paragraph(department, styles['Normal']), Paragraph("<b>Light Source :</b>", styles['Normal']), Paragraph("N/A", styles['Normal'])]
    ]
    
    t_header = Table(header_data, colWidths=[110, 160, 110, 190])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F2F5F8')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#002060')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    
    story.append(t_header)
    story.append(Spacer(1, 15))
    
    # Main Items Table Header
    table_data = [[
        Paragraph("<b>#</b>", styles['Normal']),
        Paragraph("<b>PHOTO</b>", styles['Normal']),
        Paragraph("<b>AESCULAP ARTICLE NUMBER</b>", styles['Normal']),
        Paragraph("<b>INSTRUMENT NAME</b>", styles['Normal']),
        Paragraph("<b>DETAILS OF DAMAGE</b>", styles['Normal']),
        Paragraph("<b>RECOMMENDATION</b>", styles['Normal'])
    ]]
    
    # Handle Image for PDF if uploaded
    img_obj = Paragraph("No Image", styles['Normal'])
    if uploaded_file is not None:
        temp_img_path = "temp_inst.png"
        with open(temp_img_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        img_obj = RLImage(temp_img_path, width=70, height=70)
    
    table_data.append([
        Paragraph("1", styles['Normal']),
        img_obj,
        Paragraph(article_no, styles['Normal']),
        Paragraph(instrument_name, styles['Normal']),
        Paragraph(damage_details.replace('\n', '<br/>'), styles['Normal']),
        Paragraph(recommendation, styles['Normal'])
    ])
    
    t_main = Table(table_data, colWidths=[25, 80, 110, 110, 130, 91])
    t_main.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#002060')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#002060')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    
    story.append(t_main)
    story.append(Spacer(1, 15))
    
    # Remarks and Signatures Box
    remarks_data = [
        [Paragraph(f"<b>Remarks:</b><br/>{remarks}", styles['Normal'])],
        [Paragraph("<b>Checked By (Customers):</b><br/><br/>___________________________<br/>Date: _______________", styles['Normal'])]
    ]
    t_remarks = Table(remarks_data, colWidths=[546])
    t_remarks.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#002060')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    
    story.append(t_remarks)
    
    doc.build(story)
    buffer.seek(0)
    
    # Clean up temp image
    if uploaded_file is not None and os.path.exists("temp_inst.png"):
        os.remove("temp_inst.png")
        
    st.success("Lap Scan Report Generated Successfully!")
    st.download_button(
        label="📥 Download Lap Scan PDF Report",
        data=buffer,
        file_name=f"Lap_Scan_Report_{report_no.replace('/', '_')}.pdf",
        mime="application/pdf"
    )
