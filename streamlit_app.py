import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Diagnostic Agent PRO", layout="wide")

st.title("🧠 Diagnostic Agent PRO (Event Trigger Mode)")
st.write("Shows ONLY real fault events when Byte 9 & 10 change from 00")

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
# PARSE XML HISTORY
# -----------------------------
def parse_xml(xml_text):
    root = ET.fromstring(xml_text)

    history = []
    for h in root.findall(".//history/entry"):
        if h.text:
            history.append(h.text.split())

    return history


# -----------------------------
# EVENT DETECTION (CORE LOGIC)
# -----------------------------
def detect_events(history):

    events = []

    for i in range(1, len(history)):

        prev = history[i - 1]
        curr = history[i]

        if len(prev) < 11 or len(curr) < 11:
            continue

        prev_b9, prev_b10 = prev[9], prev[10]
        curr_b9, curr_b10 = curr[9], curr[10]

        # ONLY TRIGGER WHEN BOTH CHANGE FROM 00 STATE
        if prev_b9 == "00" and prev_b10 == "00":

            if curr_b9 != "00" or curr_b10 != "00":

                events.append({
                    "entry": i,
                    "byte9": curr_b9,
                    "byte10": curr_b10
                })

    return events


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
        events = detect_events(history)

        st.subheader("🚨 Detected Fault Events")

        if not events:
            st.success("No fault transitions detected (system stable)")
        else:

            for e in events:

                st.error(
                    f"Entry {e['entry']} | Byte9: {e['byte9']} | Byte10: {e['byte10']}"
                )

                # ONLY LOOK UP BYTE 10 (real error code)
                code = e["byte10"].lower()

                if code in err_map:
                    err = err_map[code]

                    st.write("🧠 Error Name:", err["name"])
                    st.write("📄 Description:", err["description"])
                else:
                    st.warning(f"No match in Err Code table for: {code}")

        st.subheader("📜 Total History Entries")
        st.write(len(history))

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
