import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import re

st.set_page_config(page_title="Diagnostic Agent PRO", layout="wide")

st.title("🧠 Diagnostic Agent PRO (XML Engine)")
st.write("Paste full device XML log for full diagnostic analysis.")

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
                code = str(row.iloc[0]).strip()

                err_map[code] = {
                    "name": str(row.iloc[1]) if len(row) > 1 else "Unknown",
                    "description": str(row.iloc[2]) if len(row) > 2 else "No description available"
                }

    return err_map


# -----------------------------
# PARSE XML
# -----------------------------
def parse_xml(xml_text):
    root = ET.fromstring(xml_text)

    data = {}

    # System properties
    data["system"] = {}
    for prop in root.findall(".//property"):
        pid = prop.attrib.get("id")
        val = prop.find("value")
        if pid and val is not None:
            data["system"][pid] = val.text

    # Modules
    modules = []
    for m in root.findall(".//modules/*"):
        mod_data = {}
        for child in m:
            mod_data[child.tag] = child.text
        modules.append(mod_data)

    data["modules"] = modules

    # History
    history = []
    for h in root.findall(".//history/entry"):
        history.append(h.text)

    data["history"] = history

    return data


# -----------------------------
# ANALYSE SYSTEM STATE
# -----------------------------
def analyze(data):
    report = {}

    # system error
    report["system_error"] = data["system"].get("System:ErrorCode", "00")

    # voltage imbalance
    voltages = []
    for m in data["modules"]:
        try:
            voltages.append(float(m["act"]))
        except:
            pass

    if voltages:
        spread = max(voltages) - min(voltages)
        report["voltage_spread"] = round(spread, 3)
        report["electrical_status"] = "IMBALANCED" if spread > 0.3 else "OK"

    # temperature check
    temps = []
    for m in data["modules"]:
        try:
            temps.append(float(m["act"]))
        except:
            pass

    if temps:
        report["thermal_status"] = "OK" if max(temps) < 45 else "HIGH"

    # history
    report["history_events"] = len(data["history"])

    return report


# -----------------------------
# LOAD EXCEL
# -----------------------------
err_map = load_data()


# -----------------------------
# UI INPUT
# -----------------------------
xml_input = st.text_area("Paste XML Log", height=300)


# -----------------------------
# RUN DIAGNOSIS
# -----------------------------
if st.button("Run Full Diagnosis"):
    try:
        data = parse_xml(xml_input)
        result = analyze(data)

        st.subheader("📊 System Analysis")
        st.json(result)

        st.subheader("🔍 System Snapshot")
        st.json(data["system"])

        st.subheader("📦 Module Data")
        st.write(data["modules"])

        st.subheader("📜 History")
        st.write(data["history"])

        # -----------------------------
        # ERROR LOOKUP (THIS IS THE FIX)
        # -----------------------------
        system_error = result["system_error"]

        st.subheader("🧠 Error Diagnosis")

        if system_error != "00" and system_error in err_map:
            err = err_map[system_error]

            st.error(f"Error Code: {system_error}")
            st.write(f"**Name:** {err['name']}")
            st.write(f"**Description:** {err['description']}")

        else:
            st.success("No active error found in system (or not listed in Excel)")

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
