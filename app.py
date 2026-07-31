import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import google.generativeai as genai
from PIL import Image as PILImage

st.set_page_config(page_title="Lap Scan Report Generator", layout="wide")

# --- UI Header ---
st.title("🩺 Lap Scan Report Generator - Biomed")
st.write("Fill in the details below to generate a professional PDF report.")

# --- Form Layout ---
col1, col2 = st.columns(2)

with col1:
    hospital = st.text_input("Customer / Hospital", "National Hospital Sri Lanka")
    technician = st.text_input("Technician Name", "Dinushan De Zoysa")
    department = st.text_input("Department", "Theatre / Laparoscopy")
    report_no = st.text_input("Report No", "REP-2026-001")

with col2:
    brand = st.text_input("Brand", "Aesculap")
    system_set = st.text_input("System / Set", "Laparoscopy")
    inspection_date = st.date_input("Inspection Date", date.today())
    scope_serial = st.text_input("Scope Serial No", "N/A")
    camera_system = st.text_input("Camera System", "N/A")
    light_source = st.text_input("Light Source", "N/A")

st.markdown("---")
st.subheader("🛠️ Instrument Status & Remarks")

# --- Table Input Setup ---
if 'instruments' not in st.session_state:
    st.session_state.instruments = [{'article_no': '', 'name': '', 'damage': '', 'recommendation': 'REPAIR', 'image': None}]

def add_instrument():
    st.session_state.instruments.append({'article_no': '', 'name': '', 'damage': '', 'recommendation': 'REPAIR', 'image': None})

# Generate dynamic rows
for i, inst in enumerate(st.session_state.instruments):
    st.write(f"**Instrument {i+1}**")
    c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 1, 2])
    
    with c1:
        inst['article_no'] = st.text_input(f"Article No {i+1}", inst['article_no'], key=f"art_{i}")
    with c2:
        inst['name'] = st.text_input(f"Instrument Name {i+1}", inst['name'], key=f"name_{i}")
    with c3:
        inst['damage'] = st.text_input(f"Details of Damage {i+1}", inst['damage'], key=f"dam_{i}")
    with c4:
        inst['recommendation'] = st.selectbox(f"Action {i+1}", ["REPAIR", "REPLACE", "GOOD"], key=f"rec_{i}")
    with c5:
        inst['image'] = st.file_uploader(f"Upload Image {i+1} (Optional)", type=["png", "jpg", "jpeg"], key=f"img_{i}")

st.button("➕ Add Another Instrument", on_click=add_instrument)

general_remarks = st.text_area("General Remarks & Technical Observations", 
                               "All above instruments require official inspection and technical servicing. Please review the recommended actions.")

st.markdown("---")

# --- PDF Generation Function ---
def create_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=25, bottomMargin=25)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom Colors
    navy_primary = colors.HexColor('#0D2A4A')
    ice_blue_bg = colors.HexColor('#F0F4F8')
    border_navy = colors.HexColor('#BAC7D5')
    gold_accent = colors.HexColor('#D4AF37')
    
    # Custom Styles
    company_name_style = ParagraphStyle('CompName', parent=styles['Heading1'], fontSize=15, leading=17, textColor=colors.white, fontName='Helvetica-Bold')
    company_sub_style = ParagraphStyle('CompSub', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#CBD5E1'), fontName='Helvetica')
    report_title_style = ParagraphStyle('RepTitle', parent=styles['Normal'], fontSize=11, leading=13, textColor=colors.white, fontName='Helvetica-Bold', alignment=2)
    report_sub_style = ParagraphStyle('RepSub', parent=styles['Normal'], fontSize=8, leading=10, textColor=gold_accent, fontName='Helvetica-Bold', alignment=2)
    
    label_style = ParagraphStyle('LabelNavy', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=navy_primary, fontName='Helvetica-Bold')
    value_style = ParagraphStyle('ValueText', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#1F2937'), fontName='Helvetica')
    
    th_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.white, fontName='Helvetica-Bold', alignment=1)
    cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#222222'), fontName='Helvetica')
    cell_center = ParagraphStyle('TableCellCenter', parent=cell_style, alignment=1)

    # 1. Custom Letterhead
    header_table_content = [
        [Paragraph("<b>BIOMED INTERNATIONAL (PVT) LTD</b>", company_name_style), Paragraph("TECHNICAL INSPECTION REPORT", report_title_style)],
        [Paragraph("Medical & Surgical Equipment Division | Colombo, Sri Lanka", company_sub_style), Paragraph("LAP SCAN & SERVICE DIAGNOSTICS", report_sub_style)]
    ]
    t_custom_header = Table(header_table_content, colWidths=[335, 200])
    t_custom_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), navy_primary),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10), ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('LINEBELOW', (0,1), (-1,1), 2, gold_accent)
    ]))
    story.append(t_custom_header)
    story.append(Spacer(1, 10))

    # 2. General Information Box
    header_data = [
        [Paragraph("Customer / Hospital:", label_style), Paragraph(hospital, value_style), Paragraph("Brand:", label_style), Paragraph(brand, value_style)],
        [Paragraph("Inspection Date:", label_style), Paragraph(inspection_date.strftime("%d %B %Y"), value_style), Paragraph("System / Set:", label_style), Paragraph(system_set, value_style)],
        [Paragraph("Technician Name:", label_style), Paragraph(technician, value_style), Paragraph("Scope Serial No:", label_style), Paragraph(scope_serial, value_style)],
        [Paragraph("Report No:", label_style), Paragraph(report_no, value_style), Paragraph("Camera System:", label_style), Paragraph(camera_system, value_style)],
        [Paragraph("Department:", label_style), Paragraph(department, value_style), Paragraph("Light Source:", label_style), Paragraph(light_source, value_style)]
    ]
    t_header = Table(header_data, colWidths=[100, 167, 100, 168])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ice_blue_bg),
        ('BOX', (0,0), (-1,-1), 1, navy_primary),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_navy),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 12))

    # 3. Main Data Table
    table_data = [[
        Paragraph("#", th_style), Paragraph("PHOTO", th_style), Paragraph("ARTICLE NO", th_style), 
        Paragraph("INSTRUMENT NAME", th_style), Paragraph("DETAILS OF DAMAGE", th_style), Paragraph("RECOMMENDATION", th_style)
    ]]
    
    for i, inst in enumerate(st.session_state.instruments):
        if inst['article_no'] or inst['name']:
            # Image Processing
            img_flowable = Paragraph("No Image", cell_center)
            if inst['image'] is not None:
                try:
                    img = Image(inst['image'])
                    img.drawHeight = 35
                    img.drawWidth = 50
                    img_flowable = img
                except:
                    pass
            
            # Formatting recommendation color
            rec_color = "#C0392B" if inst['recommendation'] == "REPLACE" else "#E67E22" if inst['recommendation'] == "REPAIR" else "#27AE60"
            rec_text = f"<b><font color='{rec_color}'>{inst['recommendation']}</font></b>"
            
            row = [
                Paragraph(f"<b>{i+1}</b>", cell_center),
                img_flowable,
                Paragraph(f"<b>{inst['article_no']}</b>", cell_style),
                Paragraph(inst['name'], cell_style),
                Paragraph(inst['damage'], cell_style),
                Paragraph(rec_text, cell_center)
            ]
            table_data.append(row)

    t_main = Table(table_data, colWidths=[20, 70, 80, 135, 135, 95])
    t_main.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), navy_primary),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, border_navy),
        ('TOPPADDING', (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_main)
    story.append(Spacer(1, 12))

    # 4. Remarks Section
    remarks_html = f"<b><font color='{navy_primary.hexval()}'>General Remarks & Technical Observations:</font></b><br/>{general_remarks}"
    t_remarks = Table([[Paragraph(remarks_html, ParagraphStyle('RemarksStyle', parent=cell_style, fontSize=8.5, leading=12))]], colWidths=[535])
    t_remarks.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ice_blue_bg),
        ('BOX', (0,0), (-1,-1), 1, navy_primary),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_remarks)
    story.append(Spacer(1, 20))

    # 5. Signatures
    sig_label_style = ParagraphStyle('SigLabel', parent=cell_style, fontSize=8.5, leading=12, textColor=navy_primary)
    t_sig = Table([[
        Paragraph(f"<b>Inspected By ({technician}):</b><br/><br/><br/>__________________________________<br/>Signature & Date", sig_label_style),
        Paragraph("<b>Verified By (Hospital Authority):</b><br/><br/><br/>__________________________________<br/>Signature & Stamp", sig_label_style)
    ]], colWidths=[267, 268])
    story.append(t_sig)

    # 6. Page Footer (POWERED BY BIOMED)
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica-BoldOblique', 8)
        canvas.setFillColor(colors.HexColor('#7F8C8D')) # Subtle Grey Color
        # Position centered at the bottom
        canvas.drawCentredString(A4[0] / 2.0, 15, "POWERED BY BIOMED")
        canvas.restoreState()

    # Build PDF with Footer
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    
    buffer.seek(0)
    return buffer

if st.button("📄 Generate Professional PDF Report", type="primary"):
    pdf_file = create_pdf()
    st.success("PDF Generated Successfully!")
    st.download_button(label="📥 Download Professional PDF Report (A4)", data=pdf_file, file_name=f"Lap_Scan_Report_{hospital}.pdf", mime="application/pdf")

# --- AI Assistant Section ---
st.markdown("---")
st.subheader("🤖 AI Assistant (Ask about Instruments or Repairs)")
st.caption("Enter your Gemini API Key in the sidebar to chat.")

api_key = st.sidebar.text_input("Gemini API Key", type="password")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask something (e.g., How to repair PL204R insulation damage?)")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            reply = response.text
        except Exception as e:
            reply = f"Error: {e}"
    else:
        reply = "Please enter your Gemini API Key in the sidebar to use the AI."

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
