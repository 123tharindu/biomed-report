import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import os

# Page Config
st.set_page_config(page_title="Biomed International - Dynamic Report Generator", page_icon="🏥", layout="wide")

st.title("🏥 BIOMED INTERNATIONAL (PVT) LTD")
st.subheader("PROFESSIONAL LAP SCAN REPORT GENERATOR")

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
article_options = [""] + list(catalog_dict.keys())

# Sidebar Inputs
st.sidebar.header("📋 Report Details")
hospital_name = st.sidebar.text_input("Customer / Hospital", value="")
inspection_date = st.sidebar.text_input("Inspection Date", value="")
technician_name = st.sidebar.text_input("Technician Name", value="Biomed Technical Team")
report_no = st.sidebar.text_input("Report No.", value="")
department = st.sidebar.text_input("Department", value="Theatre / Laparoscopy")

st.divider()
st.header("🔬 Instruments List")

# Initialize Session State for Dynamic Instrument Entries
if "instruments_count" not in st.session_state:
    st.session_state.instruments_count = 1

# Functions to add or remove instrument entries
def add_instrument():
    st.session_state.instruments_count += 1

def remove_instrument():
    if st.session_state.instruments_count > 1:
        st.session_state.instruments_count -= 1

instrument_entries = []

# Loop to display Dynamic Instrument Forms
for i in range(st.session_state.instruments_count):
    st.markdown(f"#### 🔪 Instrument Entry #{i+1}")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        uploaded_file = st.file_uploader(f"Upload Photo #{i+1}", type=["jpg", "jpeg", "png"], key=f"img_{i}")
        recommendation = st.selectbox(f"Recommendation #{i+1}", options=["Replace", "Service", "Repair", "OK"], key=f"rec_{i}")
        
    with col2:
        if len(article_options) > 1:
            article_no = st.selectbox(f"Select Article Number #{i+1}", options=article_options, key=f"art_{i}", index=0)
            default_name = catalog_dict.get(article_no, "") if article_no else ""
        else:
            article_no = st.text_input(f"Article Number #{i+1}", value="", key=f"art_txt_{i}")
            default_name = ""
            
        instrument_name = st.text_input(f"Instrument Name #{i+1}", value=default_name, key=f"name_{i}")
        damage_details = st.text_area(f"Details of Damage #{i+1}", value="", key=f"dam_{i}", placeholder="Enter details of damage...")
        
    instrument_entries.append({
        "image": uploaded_file,
        "article_no": article_no,
        "instrument_name": instrument_name,
        "damage": damage_details,
        "recommendation": recommendation
    })
    st.markdown("---")

# Buttons to Dynamically Add or Remove Items
col_add, col_remove, _ = st.columns([1.5, 1.5, 5])

with col_add:
    st.button("➕ Add Another Instrument", on_click=add_instrument, use_container_width=True)

with col_remove:
    if st.session_state.instruments_count > 1:
        st.button("🗑️ Remove Last Instrument", on_click=remove_instrument, use_container_width=True)

st.divider()

remarks = st.text_area("General Remarks", value="All above instruments require official inspection and technical servicing. Please review the recommended actions.")

# Generate PDF Report Button
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
    
    # Custom Professional Styles
    navy_primary = colors.HexColor('#0A2540')
    slate_bg = colors.HexColor('#F4F6F8')
    border_color = colors.HexColor('#D0D7DE')
    
    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=18,
        textColor=navy_primary,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'HeaderSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#555555'),
        fontName='Helvetica-Bold'
    )
    
    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=1
    )
    
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#222222'),
        fontName='Helvetica'
    )
    
    cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=cell_style,
        alignment=1
    )

    # Document Header
    story.append(Paragraph("BIOMED INTERNATIONAL (PVT) LTD", title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("TECHNICAL INSPECTION & LAP SCAN REPORT", subtitle_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=navy_primary, spaceAfter=12))
    
    # Header Info Block
    header_data = [
        [
            Paragraph("<b>Customer / Hospital:</b>", cell_style), Paragraph(hospital_name, cell_style),
            Paragraph("<b>Brand:</b>", cell_style), Paragraph("Aesculap", cell_style)
        ],
        [
            Paragraph("<b>Inspection Date:</b>", cell_style), Paragraph(inspection_date, cell_style),
            Paragraph("<b>System / Set:</b>", cell_style), Paragraph("Laparoscopy", cell_style)
        ],
        [
            Paragraph("<b>Technician Name:</b>", cell_style), Paragraph(technician_name, cell_style),
            Paragraph("<b>Scope Serial No:</b>", cell_style), Paragraph("N/A", cell_style)
        ],
        [
            Paragraph("<b>Report No:</b>", cell_style), Paragraph(report_no, cell_style),
            Paragraph("<b>Camera System:</b>", cell_style), Paragraph("N/A", cell_style)
        ],
        [
            Paragraph("<b>Department:</b>", cell_style), Paragraph(department, cell_style),
            Paragraph("<b>Light Source:</b>", cell_style), Paragraph("N/A", cell_style)
        ]
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
    
    # Main Items Table
    table_data = [[
        Paragraph("#", th_style),
        Paragraph("PHOTO", th_style),
        Paragraph("ARTICLE NO", th_style),
        Paragraph("INSTRUMENT NAME", th_style),
        Paragraph("DETAILS OF DAMAGE", th_style),
        Paragraph("RECOMMENDATION", th_style)
    ]]
    
    temp_files_to_remove = []
    
    for idx, item in enumerate(instrument_entries):
        img_obj = Paragraph("No Image", cell_center)
        if item["image"] is not None:
            temp_img_path = f"temp_inst_{idx}.png"
            with open(temp_img_path, "wb") as f:
                f.write(item["image"].getbuffer())
            img_obj = RLImage(temp_img_path, width=65, height=65)
            temp_files_to_remove.append(temp_img_path)
            
        rec = item["recommendation"]
        if rec == "Replace":
            rec_color = "#D9534F"
        elif rec in ["Service", "Repair"]:
            rec_color = "#F0AD4E"
        else:
            rec_color = "#5CB85C"
            
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
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(t_main)
    story.append(Spacer(1, 15))
    
    # Remarks Block
    remarks_style = ParagraphStyle(
        'RemarksStyle',
        parent=cell_style,
        fontSize=8.5,
        leading=12
    )
    
    remarks_data = [
        [Paragraph(f"<b>General Remarks & Technical Observations:</b><br/>{remarks}", remarks_style)]
    ]
    t_remarks = Table(remarks_data, colWidths=[552])
    t_remarks.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), slate_bg),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_remarks)
    story.append(Spacer(1, 20))
    
    # Clean Signatures Block
    sig_data = [
        [
            Paragraph("<b>Inspected By (Biomed Engineer):</b><br/><br/><br/>__________________________________<br/>Signature & Date", cell_style),
            Paragraph("<b>Verified By (Hospital Authority):</b><br/><br/><br/>__________________________________<br/>Signature & Stamp", cell_style)
        ]
    ]
    t_sig = Table(sig_data, colWidths=[276, 276])
    t_sig.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    
    story.append(t_sig)
    
    doc.build(story)
    buffer.seek(0)
    
    # Cleanup temp images
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
