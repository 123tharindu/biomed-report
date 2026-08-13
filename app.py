import os
import requests
import streamlit as st
import google.generativeai as genai

# ==========================================
# 1. PAGE SETUP & CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Biomedical Report Generator",
    page_icon="🏥",
    layout="wide"
)

# Secrets වලින් API Keys සහ Webhook URL ලබා ගැනීම
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
WEBHOOK_URL = st.secrets.get("WEBHOOK_URL")

if not GEMINI_API_KEY:
    st.error("🔑 GEMINI_API_KEY එක Streamlit Secrets වල සෙට් කර නැත!")
    st.stop()

# Gemini API Config
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def sync_to_google_sheet(hospital, machine, serial, issue, report_content):
    """ Google Apps Script Webhook එක හරහා Google Sheet එකට Data යැවීම """
    if not WEBHOOK_URL:
        st.warning("⚠️ WEBHOOK_URL එක Streamlit Secrets වල සෙට් කර නැත. Sheet එකට Data Sync වුණේ නැත.")
        return False
    
    payload = {
        "hospital": hospital,
        "machine": machine,
        "serial": serial,
        "issue": issue,
        "report": report_content
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            st.error(f"Google Sheet Sync Error: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Webhook connection error: {e}")
        return False

# ==========================================
# 3. STREAMLIT UI & LOGIC
# ==========================================

st.title("🏥 Biomed International - Inspection Report Generator")
st.subheader("Generate Professional Technical Reports & Sync to Google Sheet")

with st.form("report_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        hospital_name = st.text_input("Hospital / Institution Name", placeholder="e.g. National Hospital Colombo")
        machine_name = st.text_input("Equipment / Machine Name", placeholder="e.g. Laparoscopic Tower")
    
    with col2:
        serial_number = st.text_input("Serial Number", placeholder="e.g. SN-987654321")
        reported_issue = st.text_area("Reported Issue / Notes", placeholder="Describe the technical fault or inspection notes...")
    
    submit_btn = st.form_submit_button("🚀 Generate Report & Sync")

if submit_btn:
    if not hospital_name or not machine_name or not reported_issue:
        st.warning("⚠️ කරුණාකර සියලුම අවශ්‍ය විස්තර (Hospital, Machine, Issue) ලබා දෙන්න.")
    else:
        with st.spinner("🤖 Gemini Report එක සකස් කරමින් පවතී..."):
            
            # Gemini Prompt Construction
            prompt = f"""
            You are a senior Biomedical Engineer at Biomed International. 
            Write a formal, high-quality, professional technical service inspection report based on the following details:

            - **Hospital/Client:** {hospital_name}
            - **Equipment:** {machine_name}
            - **Serial Number:** {serial_number if serial_number else 'N/A'}
            - **Reported Issue & Inspection Findings:** {reported_issue}

            **Structure of the Report:**
            1. Executive Summary
            2. System Inspection Details
            3. Technical Observations & Root Cause Analysis
            4. Corrective Actions Taken / Recommendations
            5. Final Status (Pass / Fail / Pending Parts)

            Use clear headings, professional technical tone, bullet points, and proper Markdown formatting.
            """
            
            try:
                # Gemini call
                response = model.generate_content(prompt)
                generated_report = response.text
                
                st.success("✅ Report එක සාර්ථකව සකස් කරන ලදී!")
                
                # Google Sheet Sync
                with st.spinner("📊 Google Sheet එකට Data Sync කරමින් පවතී..."):
                    synced = sync_to_google_sheet(
                        hospital=hospital_name,
                        machine=machine_name,
                        serial=serial_number,
                        issue=reported_issue,
                        report_content=generated_report
                    )
                    
                    if synced:
                        st.success("✅ Google Sheet එකට Data සාර්ථකව Ekතු විය!")

                st.markdown("---")
                st.markdown("### 📄 Generated Inspection Report")
                st.markdown(generated_report)
                
                # Download Button for the report as Markdown/Text
                st.download_button(
                    label="📥 Download Report (.txt)",
                    data=generated_report,
                    file_name=f"Biomed_Report_{hospital_name.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"❌ Error occurred while generating report: {e}")
