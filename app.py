import streamlit as st
import pandas as pd
import datetime
import io
import os
from PIL import Image, ImageOps
from google import genai
from reportlab.lib.pagesizes import A4
# RLImage මෙතනට import කර ඇත
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
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

# Comprehensive Sri Lankan Hospitals List
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
        Line 2: Single-word Recommendation (Choose strictly one: Replace, Repair, Service, or OK).
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
            for r in ["Replace", "Repair", "Service", "OK"]:
                if r.lower() in possible_rec.lower():
                    rec_text = r
                    break
        return damage_text, rec_text
    except Exception as e:
        return f"Auto-analysis unavailable: {str(e)}", "OK"
