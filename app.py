import datetime
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Biomed Lap Scan Portal", page_icon="🏥", layout="centered"
)
st.title("Biomed Lap Inspection Portal")


# --- Google Sheets Connection ---
@st.cache_resource
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Streamlit Secrets (Cloud Environment)
    if "gcp_service_account" in st.secrets:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(
            credentials_dict, scopes=scopes
        )
    else:
        # Local Development Credentials
        creds = Credentials.from_service_account_file(
            "credentials.json", scopes=scopes
        )

    client = gspread.authorize(creds)
    return client.open("Biomed Lap Inspection Summary").sheet1


# --- Function to Save Data to Google Sheet ---
def save_inspection(
    report_no,
    date,
    hospital,
    engineer,
    instrument_names,
    total_inst,
    replace_c,
    service_c,
):
    try:
        sheet = get_google_sheet()
        all_rows = sheet.get_all_values()

        # Duplicate Check: Prevent consecutive duplicate submissions by Report No
        if len(all_rows) > 1 and all_rows[-1][0] == str(report_no):
            return "duplicate"

        logged_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [
            report_no,
            str(date),
            hospital,
            engineer,
            instrument_names,
            total_inst,
            replace_c,
            service_c,
            logged_at,
        ]

        sheet.append_row(row)
        return "success"
    except Exception as e:
        return str(e)


# --- Complete Official Hospital List (59 Hospitals) ---
HOSPITAL_LIST = [
    # Southern Province
    "District General Hospital Hambantota",
    "Base Hospital Tangalle",
    "District General Hospital Matara",
    "Base Hospital Kamburupitiya",
    "National Hospital Galle (Karapitiya)",
    "Galle Mediclinic / Cardicare",
    "Ruhunu Hospital Galle",
    "Base Hospital Elpitiya",
    "Base Hospital Balapitiya",
    "Asiri Hospital Galle",
    # Western Province (Kalutara & Colombo)
    "Teaching Hospital Kalutara",
    "Philip Hospital Kalutara",
    "Kethumathi Maternity Hospital Kalutara",
    "Colombo South Teaching Hospital (Kalubowila)",
    "National Hospital of Sri Lanka (NHSL Colombo)",
    "National Eye Hospital Colombo",
    "Lady Ridgeway Hospital for Children (LRH)",
    "Sri Jayewardenepura General Hospital (SJGH)",
    "Nawaloka Hospital Colombo",
    "Lanka Hospitals Colombo",
    "Asiri Central Hospital",
    "Castle Street Hospital for Women",
    "De Soysa Hospital for Women (DMH)",
    "Apeksha Hospital Maharagama",
    "Colombo Army Hospital",
    "Durdans Hospital Colombo",
    "General Sir John Kotelawala Defence University Hospital (KDU)",
    "Wish Fertility & Women's Hospital",
    "Asiri Surgical Hospital",
    "Kings Hospital Colombo",
    # Western Province (Gampaha)
    "District General Hospital Gampaha",
    "Colombo North Teaching Hospital (Ragama)",
    "Sri Lanka Navy General Hospital Welisara",
    # North Western Province
    "District General Hospital Chilaw",
    "Base Hospital Puttalam",
    "Teaching Hospital Kuliyapitiya",
    "Teaching Hospital Kurunegala",
    "Kurunegala Co-operative Hospital",
    "Base Hospital Dambadeniya",
    # Central Province
    "Base Hospital Rikillagaskada",
    "National Hospital Kandy",
    "Asiri Hospital Kandy",
    "Teaching Hospital Peradeniya",
    "Sirimavo Bandaranaike Specialized Children's Hospital",
    "District General Hospital Matale",
    "Base Hospital Dambulla",
    # Uva / Sabaragamuwa / North Central
    "Teaching Hospital Badulla",
    "Teaching Hospital Anuradhapura",
    "District General Hospital Polonnaruwa",
    "Teaching Hospital Ratnapura",
    "Base Hospital Embilipitiya",
    "Teaching Hospital Kegalle",
    # Eastern & Northern Province
    "Teaching Hospital Batticaloa",
    "Base Hospital Valaichchenai",
    "District General Hospital Trincomalee",
    "Base Hospital Akkaraipattu",
    "Teaching Hospital Jaffna",
    "Holy Cross Hospital Jaffna",
    "Northern Central Hospital Jaffna",
    # Manual Input Option
    "Other (Type manually)",
]


# --- Streamlit UI Form ---
with st.form("inspection_form", clear_on_submit=True):
    st.subheader("Inspection Entry Form")

    report_no = st.text_input("Report No *")
    date = st.date_input("Date", datetime.date.today())

    # Hospital Selection with Dropdown Search
    selected_hospital = st.selectbox(
        "Select Hospital (Type to search)", options=HOSPITAL_LIST
    )

    # Dynamic Field: Appears only if 'Other' is selected
    if selected_hospital == "Other (Type manually)":
        final_hospital = st.text_input("Enter Hospital Name Manually *")
    else:
        final_hospital = selected_hospital

    engineer = st.text_input("Engineer Name *")
    instrument_names = st.text_area(
        "Instrument Names (Comma separated)",
        placeholder="e.g., Laparoscope 10mm, Trocar 5mm, Grasper, Curved Scissors",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        total_inst = st.number_input(
            "Total Instruments", min_value=0, step=1, value=0
        )
    with col2:
        replace_c = st.number_input(
            "Replace Count", min_value=0, step=1, value=0
        )
    with col3:
        service_c = st.number_input(
            "Service/Repair Count", min_value=0, step=1, value=0
        )

    submit_button = st.form_submit_button("Submit Record")

    # Form Submission Handler
    if submit_button:
        if (
            not report_no
            or not engineer
            or (
                selected_hospital == "Other (Type manually)"
                and not final_hospital
            )
        ):
            st.warning(
                "Please fill in all required fields (Report No, Hospital, and Engineer Name)!"
            )
        else:
            with st.spinner("Saving to Google Sheets..."):
                res = save_inspection(
                    report_no,
                    date,
                    final_hospital,
                    engineer,
                    instrument_names,
                    total_inst,
                    replace_c,
                    service_c,
                )

                if res == "success":
                    st.success("Record added successfully to Google Sheet!")
                elif res == "duplicate":
                    st.warning("Duplicate submission detected! Row skipped.")
                else:
                    st.error(f"Error occurred: {res}")
