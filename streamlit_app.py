import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Diagnostic Agent PRO", layout="wide")

st.title("🧠 Diagnostic Agent PRO (Byte-Level Engine)")
st.write("Paste XML log — detects faults from HISTORY byte positions (9 & 10)")

EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


# -----------------------------
# LOAD EXCEL (both tables)
# -----------------------------
@st.cache_data
def load_data():
    xls = pd.ExcelFile(EXCEL_FILE)

    err_map = {}
    source_map = {}

    for sheet in xls.sheet_names:

        # Err Code sheet
        if "err code" in sheet.lower():
            df = pd.read_excel(xls, sheet)
            df.columns = [c.strip() for c in df.columns]

            for _, row in df.iterrows():
                code = str(row.iloc[0]).strip()
                err_map[code] = {
                    "name": str(row.iloc[1]) if len(row) > 1 else "Unknown",
                    "description": str(row.iloc[2]) if len(row) > 2 else "No description"
                }

        # Error Source sheet
        if "source" in sheet.lower():
            df = pd.read_excel(xls, sheet)
            df.columns = [c.strip() for c in df.columns]

            for _, row in df.iterrows():
                key = str(row.iloc[0]).strip()
                source_map[key] = row.to_dict()

    return err_map, source_map


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
# BYTE POSITION FAULT DETECTOR
# -----------------------------
def detect_faults(history_entries):

    faults = []

    for i, entry in enumerate(history_entries):

        if len(entry) < 11:
            continue

        byte9 = entry[9]
        byte10 = entry[10]

        # KEY RULE FROM YOUR SYSTEM
        if byte9 != "00" or byte10 != "00":

            if byte9 in ["1f", "1F"]:
                faults.append({
                    "entry": i,
                    "byte": 9,
                    "value": byte9,
                    "type": "ERROR SOURCE (HMI / Controller)"
                })

            if byte10 in ["77", "1f", "1F"]:
                faults.append({
                    "entry": i,
                    "byte": 10,
                    "value": byte10,
                    "type": "ERROR CODE"
                })

    return faults


# -----------------------------
# LOAD EXCEL MAPS
# -----------------------------
err_map, source_map = load_data()


# -----------------------------
# UI
# -----------------------------
xml_input = st.text_area("Paste XML Log", height=300)


if st.button("Run Diagnosis"):

    try:
        history = parse_xml(xml_input)

        faults = detect_faults(history)

        st.subheader("📡 Byte-Level Fault Detection")

        if not faults:
            st.success("No faults detected in byte positions 9 & 10")
        else:
            for f in faults:

                st.error(
                    f"Entry {f['entry']} | Byte {f['byte']} → {f['value']} | {f['type']}"
                )

                # MAP TO ERR CODE TABLE
                code = f["value"].lower()

                if code in err_map:
                    st.write("🧠 Matched in Err Code Table")
                    st.write("**Name:**", err_map[code]["name"])
                    st.write("**Description:**", err_map[code]["description"])

                else:
                    st.warning("No match in Err Code table")

        st.subheader("📜 Raw Parsed History")
        st.write(history)

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
