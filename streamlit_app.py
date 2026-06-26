import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Diagnostic Agent PRO", layout="wide")

st.title("🧠 Diagnostic Agent PRO (Full Engine)")
st.write("Paste full XML log to analyse system + history faults")

EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


# -----------------------------
# LOAD EXCEL (Err Code sheet)
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

    # system properties
    data["system"] = {}
    for prop in root.findall(".//property"):
        pid = prop.attrib.get("id")
        val = prop.find("value")
        if pid and val is not None:
            data["system"][pid] = val.text

    # modules
    modules = []
    for m in root.findall(".//modules/*"):
        mod = {}
        for child in m:
            mod[child.tag] = child.text
        modules.append(mod)

    data["modules"] = modules

    # history entries
    history = []
    for h in root.findall(".//history/entry"):
        history.append(h.text.strip() if h.text else "")

    data["history"] = history

    return data


# -----------------------------
# HISTORY FAULT DETECTION
# -----------------------------
def detect_history_faults(history_entries):
    faults = []

    parsed = []
    for entry in history_entries:
        if not entry:
            continue
        parsed.append(entry.split())

    for i in range(1, len(parsed)):
        prev = parsed[i - 1]
        curr = parsed[i]

        min_len = min(len(prev), len(curr))

        for j in range(min_len):
            if prev[j] != curr[j]:
                faults.append({
                    "position": j,
                    "from": prev[j],
                    "to": curr[j],
                    "entry_index": i
                })

    return faults


# -----------------------------
# SYSTEM ANALYSIS
# -----------------------------
def analyze(data):
    report = {}

    report["system_error"] = data["system"].get("System:ErrorCode", "00")

    # voltage analysis
    volts = []
    for m in data["modules"]:
        try:
            volts.append(float(m.get("act", 0)))
        except:
            pass

    if volts:
        report["voltage_spread"] = round(max(volts) - min(volts), 3)
        report["electrical_status"] = "IMBALANCED" if report["voltage_spread"] > 0.3 else "OK"

    # temp analysis
    temps = []
    for m in data["modules"]:
        try:
            temps.append(float(m.get("act", 0)))
        except:
            pass

    if temps:
        report["thermal_status"] = "HIGH" if max(temps) > 45 else "OK"

    # history
    report["history_faults"] = detect_history_faults(data["history"])

    return report


# -----------------------------
# LOAD EXCEL
# -----------------------------
err_map = load_data()


# -----------------------------
# UI
# -----------------------------
xml_input = st.text_area("Paste XML Log", height=300)

if st.button("Run Full Diagnosis"):
    try:
        data = parse_xml(xml_input)
        result = analyze(data)

        st.subheader("📊 System Analysis")
        st.json(result)

        # -----------------------------
        # SYSTEM ERROR LOOKUP
        # -----------------------------
        st.subheader("🧠 System Error Diagnosis")

        sys_code = result["system_error"]

        if sys_code != "00" and sys_code in err_map:
            err = err_map[sys_code]

            st.error(f"Error Code: {sys_code}")
            st.write(f"**Name:** {err['name']}")
            st.write(f"**Description:** {err['description']}")
        else:
            st.success("No active system error found")

        # -----------------------------
        # HISTORY FAULTS
        # -----------------------------
        st.subheader("📡 History Fault Detection")

        history_faults = result["history_faults"]

        if history_faults:
            for f in history_faults:
                code = f["to"]

                st.write(f"Byte {f['position']}: {f['from']} → {f['to']}")

                if code in err_map:
                    err = err_map[code]
                    st.error(f"{err['name']}")
                    st.write(err["description"])
                else:
                    st.warning(f"Unknown mapped code: {code}")
        else:
            st.info("No history anomalies detected")

        # -----------------------------
        # RAW SNAPSHOT
        # -----------------------------
        st.subheader("🔍 System Snapshot")
        st.json(data["system"])

        st.subheader("📦 Modules")
        st.write(data["modules"])

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
