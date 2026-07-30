import streamlit as st
import google.generativeai as genai
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# Page Config
st.set_page_config(page_title="Biomedical Report Generator", page_icon="🏥", layout="wide")

st.title("🏥 Biomedical Instrument Report Generator")
st.write("Generate official inspection and calibration reports with automated catalog lookup.")

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

st.sidebar.header("📝 Instrument Details")

# Article Number Input (Selectbox with search support)
article_options = list(catalog_dict.keys())

if article_options:
    article_no_1 = st.sidebar.selectbox("Select Article Number #1", options=article_options)
    default_name_1 = catalog_dict.get(article_no_1, "")
else:
    article_no_1 = st.sidebar.text_input("Article Number #1", value="PL718SU* / PL738SU**")
    default_name_1 = "Catalog not found / Custom Item"

instrument_name_1 = st.sidebar.text_input("Instrument Name #1", value=default_name_1)

hospital_name = st.sidebar.text_input("Hospital / Institution", value="Teaching Hospital")
technician_name = st.sidebar.text_input("Checked By (Technician)", value="BioVisionLK Engineer")

if st.button("Generate PDF Report"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#003366'),
        spaceAfter=15
    )
    
    story.append(Paragraph("<b>BIOVISIONLK (PVT) LTD</b>", title_style))
    story.append(Paragraph("<b>Official Biomedical Equipment Inspection Report</b>", styles['Normal']))
    story.append(Spacer(1, 15))
    
    data = [
        ["Hospital:", hospital_name],
        ["Article Number #1:", article_no_1],
        ["Instrument Name #1:", instrument_name_1],
        ["Inspected By:", technician_name]
    ]
    
    t = Table(data, colWidths=[150, 350])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f4f8')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#333333')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd'))
    ]))
    
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    
    st.success("Report Generated Successfully!")
    st.download_button(
        label="📥 Download PDF Report",
        data=buffer,
        file_name="biomedical_report.pdf",
        mime="application/pdf"
    )
