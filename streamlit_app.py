import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import re

st.set_page_config(page_title="Diagnostic Agent Pro", layout="wide")

st.title("🧠 Diagnostic Agent PRO (XML Engine)")
st.write("Paste full device XML log for full diagnostic analysis.")

EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


@st.cache_data
def load_data():
    xls = pd.ExcelFile("Err Code and interpretation_V1.11_APS.xlsx")

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

    # modules
    modules = []
    for m in root.findall(".//modules/*"):
        mod_data = {}
        for child in m:
            mod_data[child.tag] = child.text
        modules.append(mod_data)

    data["modules"] = modules

    # history
    history = []
    for h in root.findall(".//history/entry"):
        history.append(h.text)

    data["history"] = history

    return data


def analyze(data):
    report = {}

    # 1. system error
    report["system_error"] = data["system"].get("System:ErrorCode", "unknown")

    # 2. voltage imbalance
    voltages = []
    for m in data["modules"]:
        try:
            v = float(m["act"])
            voltages.append(v)
        except:
            pass

    if voltages:
        spread = max(voltages) - min(voltages)
        report["voltage_spread"] = round(spread, 3)
        report["electrical_status"] = "IMBALANCED" if spread > 0.3 else "OK"

    # 3. temperature check
    temps = []
    for m in data["modules"]:
        try:
            t = float(m.get("act", 0))
            temps.append(t)
        except:
            pass

    report["thermal_status"] = "OK" if max(temps) < 45 else "HIGH"

    # 4. history presence
    report["history_events"] = len(data["history"])
    report["historical_faults"] = "YES" if len(data["history"]) > 5 else "LOW"

    return report


excel_map = load_excel()

xml_input = st.text_area("Paste XML Log", height=300)

if st.button("Run Full Diagnosis"):
    try:
        data = parse_xml(xml_input)
        result = analyze(data)

        st.subheader("📊 Diagnostic Report")
        st.json(result)

        st.subheader("🔍 System Snapshot")
        st.json(data["system"])

        st.subheader("📦 Module Overview")
        st.write(data["modules"])

        st.subheader("📜 History Entries")
        st.write(data["history"])

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
