import datetime
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

st.set_page_config(page_title="Biomed Lap Scan Portal", layout="centered")
st.title("Biomed Lap Inspection Portal")


# --- Google Sheets Authentication ---
@st.cache_resource
def get_google_sheet():
    # Google credentials සකසා ගැනීම
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Streamlit Secrets වලින් හෝ local credentials.json මගින් connect වීම
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
    else:
        creds = Credentials.from_service_account_file(
            "credentials.json", scopes=scopes
        )

    client = gspread.authorize(creds)
    return client.open("Biomed Lap Inspection Summary").sheet1


# --- Data Submission Function ---
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

        # Duplicate Check (අන්තිම row එකේ Report No එක සමාන නම් නවතන්න)
        if len(all_rows) > 1 and all_rows[-1][0] == str(report_no):
            return "duplicate"

        logged_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Row Data පිළිවෙලට සකස් කිරීම
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


# --- Streamlit UI Form ---
with st.form("inspection_form", clear_on_submit=True):
    st.subheader("Inspection Entry Form")

    report_no = st.text_input("Report No")
    date = st.date_input("Date", datetime.date.today())
    hospital = st.text_input("Hospital Name", "N/A")
    engineer = st.text_input("Engineer Name")
    instrument_names = st.text_area(
        "Instrument Names (Comma separated)",
        placeholder="Laparoscope, Scissors, Forceps",
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

    if submit_button:
        if not report_no or not engineer:
            st.warning("Please fill in Report No and Engineer Name!")
        else:
            with st.spinner("Saving to Google Sheets..."):
                res = save_inspection(
                    report_no,
                    date,
                    hospital,
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
