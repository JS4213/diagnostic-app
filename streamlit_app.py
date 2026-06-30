import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Diagnostic Agent PRO", layout="wide")

st.title("🧠 Diagnostic Agent PRO (Byte 9/10 Engine)")
st.write("Detects Error Source (Byte 9) + Error Code (Byte 10) correctly")

EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


# -----------------------------
# LOAD EXCEL ERROR TABLE
# -----------------------------
@st.cache_data
def load_data():
    xls = pd.ExcelFile(EXCEL_FILE)

    err_map = {}

    for sheet in xls.sheet_names:
        if "err code" in sheet.lower():
            df = pd.read_excel(xls, sheet)
            df.columns = [c.strip() for c in df.columns]

            for _, row in df.iterrows():
                code = str(row.iloc[0]).strip().lower()

                err_map[code] = {
                    "name": str(row.iloc[1]) if len(row) > 1 else "Unknown",
                    "description": str(row.iloc[2]) if len(row) > 2 else "No description"
                }

    return err_map


# -----------------------------
# PARSE XML
# -----------------------------
def parse_xml(xml_text):
    root = ET.fromstring(xml_text)

    history = []
    for h in root.findall(".//history/entry"):
        if h.text:
            history.append(h.text.split())

    return history


# -----------------------------
# BYTE 9/10 ENGINE (FIXED LOGIC)
# -----------------------------
def detect_faults(history_entries):

    faults = []

    for i, entry in enumerate(history_entries):

        if len(entry) < 11:
            continue

        byte9 = entry[9].lower()
        byte10 = entry[10].lower()

        # BYTE 9 = SOURCE (context only)
        source = "UNKNOWN"

        if byte9 == "1f":
            source = "HMI / Controller"
        elif byte9 != "00":
            source = f"Source Code {byte9}"

        # BYTE 10 = REAL ERROR CODE (LOOKUP KEY)
        error_code = byte10

        faults.append({
            "entry": i,
            "byte9_source": byte9,
            "byte10_code": error_code,
            "source_label": source
        })

    return faults


# -----------------------------
# LOAD EXCEL
# -----------------------------
err_map = load_data()


# -----------------------------
# UI
# -----------------------------
xml_input = st.text_area("Paste XML Log", height=300)


if st.button("Run Diagnosis"):

    try:
        history = parse_xml(xml_input)
        faults = detect_faults(history)

        st.subheader("📡 Fault Detection (Byte 9/10 Logic)")

        for f in faults:

            st.write(f"Entry {f['entry']}")

            st.write(f"Byte 9 (Source): {f['byte9_source']} → {f['source_label']}")
            st.write(f"Byte 10 (Error Code): {f['byte10_code']}")

            code = f["byte10_code"]

            # -----------------------------
            # IMPORTANT FIX: LOOKUP BYTE 10
            # -----------------------------
            if code in err_map:

                err = err_map[code]

                st.error(f"🚨 {err['name']}")
                st.write(err["description"])

            else:
                st.warning(f"No match in Err Code table for: {code}")

            st.divider()

        st.subheader("📜 Raw History")
        st.write(history)

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
