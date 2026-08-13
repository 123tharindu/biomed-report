import datetime
from flask import Flask, jsonify, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# --- Google Sheets API Setup ---
def get_google_sheet():
    # Google Credentials සඳහා Scope එක
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # credentials.json ෆයිල් එක app.py තියෙන Folder එකේම තිබිය යුතුය
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(creds)

    # Google Sheet එක Open කරගැනීම
    sheet = client.open("Biomed Lap Inspection Summary").sheet1
    return sheet


# --- API Endpoint to Submit Inspection Data ---
@app.route("/submit-inspection", methods=["POST"])
def submit_inspection():
    try:
        data = request.get_json()

        # Request එකෙන් එන දත්ත ලබාගැනීම
        report_no = data.get("report_no")
        date = data.get("date")
        hospital = data.get("hospital", "N/A")
        engineer = data.get("engineer")
        instrument_names = data.get(
            "instrument_names"
        )  # උදා: "Laparoscope, Scissors, Forceps"
        total_instruments = data.get("total_instruments", 0)
        replace_count = data.get("replace_count", 0)
        service_count = data.get("service_count", 0)

        # 1. Google Sheet එක සම්බන්ධ කරගැනීම
        sheet = get_google_sheet()
        all_rows = sheet.get_all_values()

        # 2. Duplicate Check: අන්තිම Row එකේ Report No එකත් දැන් එන Report No එකත් සමානදැයි බලයි
        if len(all_rows) > 1:
            last_row = all_rows[-1]
            if last_row[0] == str(report_no):
                return (
                    jsonify(
                        {
                            "status": "warning",
                            "message": "Duplicate submission detected and ignored.",
                        }
                    ),
                    200,
                )

        # 3. Logged timestamp සකසා ගැනීම
        logged_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. Sheet එකට පිළිවෙලට Row එක සකස් කිරීම
        # Columns: Report No | Date | Hospital | Engineer | Instrument Names | Total | Replace | Service | Logged At
        row_data = [
            report_no,
            date,
            hospital,
            engineer,
            instrument_names,
            total_instruments,
            replace_count,
            service_count,
            logged_at,
        ]

        # 5. Row එක Sheet එකට append කිරීම
        sheet.append_row(row_data)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Data logged successfully!",
                    "data": row_data,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
