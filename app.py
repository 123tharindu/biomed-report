import os  
import streamlit as st  
import google.generativeai as genai  
from reportlab.lib.pagesizes import A4  
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage  
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  
from reportlab.lib import colors  
  
# Page Config  
st.set_page_config(page_title="Biomed International Report Generator", page_icon="🏥", layout="centered")  
  
# API Key configuration  
GOOGLE_API_KEY = "AQ.Ab8RN6JbpzCThvBcn30TyWb0CWus4Mofw5cdCbRq1NNI_fGyAQ"  
if GOOGLE_API_KEY:  
    genai.configure(api_key=GOOGLE_API_KEY)  
  
st.title("🏥 BIOMED INTERNATIONAL (PVT) LTD")  
st.subheader("Multi-Instrument AI Lap Scan Report Generator")  
  
# Meta Inputs  
col1, col2 = st.columns(2)  
with col1:  
    customer = st.text_input("Customer / Hospital", "BH Dambadeniya")  
    inspection_date = st.text_input("Inspection Date", "22 July 2026")  
    technician = st.text_input("Technician Name", "Biomed Technical Team")  
with col2:  
    brand = st.text_input("Brand", "Aesculap")  
    system_set = st.text_input("System / Set", "Laparoscopy")  
    report_no = st.text_input("Report No.", "BMI/LAP/2026/0527")  
  
st.markdown("---")  
st.markdown("### Instrument Inspection Details")  
  
# Dynamic rows using session state  
if 'num_rows' not in st.session_state:  
    st.session_state.num_rows = 1  
  
instruments_data = []  
  
for i in range(st.session_state.num_rows):  
    st.markdown(f"**Instrument #{i+1}**")  
    cols = st.columns([1, 1, 1])  
      
    with cols[0]:  
        article = st.text_input(f"Article Number #{i+1}", key=f"article_{i}")  
    with cols[1]:  
        photo = st.file_uploader(f"Upload Photo #{i+1}", type=['png', 'jpg', 'jpeg'], key=f"photo_{i}")  
    with cols[2]:  
        rec = st.selectbox(f"Recommendation #{i+1}", ["Replace", "Service", "Repair"], key=f"rec_{i}")  
      
    # Auto AI fetch simulation or button  
    name = f"Aesculap Surgical Instrument {article}"  
    damage = "Tip alignment and wear check required."  
      
    if article:  
        try:  
            model = genai.GenerativeModel('gemini-1.5-flash')  
            prompt = f"For Aesculap surgical instrument article '{article}', provide exact Name and short damage description separated by a comma."  
            res = model.generate_content(prompt)  
            if res and res.text:  
                parts = res.text.split(',')  
                name = parts[0].strip()  
                if len(parts) > 1:  
                    damage = parts[1].strip()  
        except:  
            pass  
  
    name_input = st.text_input(f"Instrument Name #{i+1}", value=name, key=f"name_{i}")  
    damage_input = st.text_area(f"Details of Damage #{i+1}", value=damage, key=f"damage_{i}")  
    st.markdown("---")  
      
    instruments_data.append({  
        "article": article,  
        "photo": photo,  
        "name": name_input,  
        "damage": damage_input,  
        "rec": rec  
    })  
  
if st.button("+ Add Another Instrument"):  
    st.session_state.num_rows += 1  
    st.rerun()  
  
remarks = st.text_area("Remarks", "All above instruments need service and functionality check. Please refer to the details and process the repairs.")  
  
if st.button("Generate PDF Report", type="primary"):  
    output_pdf = "output_report.pdf"  
    doc = SimpleDocTemplate(output_pdf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)  
    styles = getSampleStyleSheet()  
      
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#002D62'), alignment=1, spaceAfter=15)  
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#333333'))  
    bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#002D62'))  
  
    story = []  
    story.append(Paragraph("<b>BIOMED INTERNATIONAL (PVT) LTD.</b>", title_style))  
    story.append(Paragraph("LAP SCAN REPORT", title_style))  
      
    meta_data = [  
        [Paragraph("Customer / Hospital", bold_style), Paragraph(f": {customer}", normal_style), Paragraph("Brand", bold_style), Paragraph(f": {brand}", normal_style)],  
        [Paragraph("Inspection Date", bold_style), Paragraph(f": {inspection_date}", normal_style), Paragraph("System / Set", bold_style), Paragraph(f": {system_set}", normal_style)],  
        [Paragraph("Technician Name", bold_style), Paragraph(f": {technician}", normal_style), Paragraph("Report No.", bold_style), Paragraph(f": {report_no}", normal_style)]  
    ]  
    t_meta = Table(meta_data, colWidths=[110, 157, 110, 157])  
    t_meta.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#002D62')), ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fcfcfc')), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))  
    story.append(t_meta)  
    story.append(Spacer(1, 15))  
      
    table_rows = [[  
        Paragraph("<b>#</b>", bold_style), Paragraph("<b>PHOTO</b>", bold_style), Paragraph("<b>ARTICLE</b>", bold_style),   
        Paragraph("<b>NAME</b>", bold_style), Paragraph("<b>DAMAGE</b>", bold_style), Paragraph("<b>REC</b>", bold_style)  
    ]]  
      
    os.makedirs("temp_imgs", exist_ok=True)  
    for idx, item in enumerate(instruments_data):  
        p_cell = Paragraph("No Image", normal_style)  
        if item["photo"]:  
            img_path = os.path.join("temp_imgs", item["photo"].name)  
            with open(img_path, "wb") as f:  
                f.write(item["photo"].getbuffer())  
            try:  
                p_cell = RLImage(img_path, width=50, height=40)  
            except:  
                pass  
                  
        table_rows.append([  
            Paragraph(str(idx+1), normal_style),  
            p_cell,  
            Paragraph(item["article"], bold_style),  
            Paragraph(item["name"], normal_style),  
            Paragraph(item["damage"], normal_style),  
            Paragraph(item["rec"], normal_style)  
        ])  
          
    t_report = Table(table_rows, colWidths=[25, 60, 95, 110, 150, 94])  
    t_report.setStyle(TableStyle([  
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#002D62')),  
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#002D62')),  
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),  
        ('TOPPADDING', (0,0), (-1,-1), 6),  
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),  
    ]))  
    story.append(t_report)  
    story.append(Spacer(1, 15))  
      
    doc.build(story)  
      
    with open(output_pdf, "rb") as pdf_file:  
        st.download_button(  
            label="📥 Download Generated PDF Report",  
            data=pdf_file,  
            file_name=f"Lap_Report_{report_no.replace('/', '_')}.pdf",  
            mime="application/pdf"  
        )  
