import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Diagnostic Agent PRO", layout="wide")

st.title("🧠 Diagnostic Agent PRO (Extended Entry Engine)")
st.write("Handles Normal + Extended Error Source Entries (Byte 9 = 20 mode)")

EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


# -----------------------------
# LOAD ERROR TABLE
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
# DETECT FAULT EVENTS ONLY
# -----------------------------
def detect_events(history):

    events = []

    for i in range(1, len(history)):

        prev = history[i - 1]
        curr = history[i]

        if len(curr) < 11:
            continue

        byte9 = curr[9]
        byte10 = curr[10]

        # ONLY TRIGGER WHEN SOMETHING CHANGES FROM BASELINE
        if prev[9] == "00" and prev[10] == "00":

            if byte9 != "00" or byte10 != "00":

                events.append({
                    "entry": i,
                    "byte9": byte9,
                    "byte10": byte10,
                    "raw": curr
                })

    return events


# -----------------------------
# EXTENDED MODE PARSER (BYTE 9 = 20)
# -----------------------------
def parse_extended_entry(entry, err_map):

    """
    When Byte 9 = 20:
    - ignore fixed positions
    - scan entire entry for known error codes
    """

    found = []

    for token in entry:
        code = token.lower()

        if code in err_map:
            found.append({
                "code": code,
                "name": err_map[code]["name"],
                "description": err_map[code]["description"]
            })

    return found


# -----------------------------
# NORMAL MODE PARSER
# -----------------------------
def parse_normal(byte10, err_map):

    code = byte10.lower()

    if code in err_map:
        return [{
            "code": code,
            "name": err_map[code]["name"],
            "description": err_map[code]["description"]
        }]

    return []


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

        st.subheader("🚨 Fault Events")

        if not events:
            st.success("No fault events detected")
        else:

            for e in events:

                st.write(f"Entry {e['entry']}")

                byte9 = e["byte9"]
                byte10 = e["byte10"]

                st.write(f"Byte 9: {byte9}")
                st.write(f"Byte 10: {byte10}")

                # -----------------------------
                # MODE SWITCH
                # -----------------------------
                if byte9 == "20":

                    st.warning("Extended Error Source Entry Mode")

                    results = parse_extended_entry(e["raw"], err_map)

                    if results:
                        for r in results:
                            st.error(f"{r['name']}")
                            st.write(r["description"])
                    else:
                        st.warning("No matching extended error found")

                else:

                    results = parse_normal(byte10, err_map)

                    if results:
                        for r in results:
                            st.error(f"{r['name']}")
                            st.write(r["description"])
                    else:
                        st.warning(f"No match for code: {byte10}")

                st.divider()

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
