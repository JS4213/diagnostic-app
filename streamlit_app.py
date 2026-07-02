import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Predictive AI Diagnostic System", layout="wide")

st.title("🔮 Predictive AI Diagnostic System")
st.write("Detects faults + predicts future failures from byte behaviour patterns")

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
# DETECT RAW EVENTS
# -----------------------------
def detect_events(history):

    events = []

    for i in range(1, len(history)):

        prev = history[i - 1]
        curr = history[i]

        if len(curr) < 11:
            continue

        if prev[9] == "00" and prev[10] == "00":

            if curr[9] != "00" or curr[10] != "00":

                events.append({
                    "index": i,
                    "byte9": curr[9],
                    "byte10": curr[10]
                })

    return events


# -----------------------------
# PREDICTIVE ANALYSIS ENGINE
# -----------------------------
def predictive_analysis(events):

    if not events:
        return []

    predictions = []

    byte10_sequence = [e["byte10"].lower() for e in events]
    byte9_sequence = [e["byte9"].lower() for e in events]

    freq = Counter(byte10_sequence)

    for e in events:

        code = e["byte10"].lower()

        # BASE RISK
        risk = 0

        # repeated occurrences = higher risk
        risk += freq[code] * 20

        # known critical codes
        if code in ["77", "ef"]:
            risk += 40

        if code in ["1f"]:
            risk += 25

        # escalation detection (pattern instability)
        if len(set(byte10_sequence[-3:])) > 1:
            risk += 20

        # classify
        if risk < 30:
            level = "LOW"
        elif risk < 60:
            level = "MEDIUM"
        elif risk < 85:
            level = "HIGH"
        else:
            level = "CRITICAL"

        predictions.append({
            "entry": e["index"],
            "byte9": e["byte9"],
            "byte10": e["byte10"],
            "risk": risk,
            "level": level
        })

    return predictions


# -----------------------------
# LOAD EXCEL
# -----------------------------
err_map = load_data()


# -----------------------------
# UI
# -----------------------------
xml_input = st.text_area("Paste XML Log", height=300)


if st.button("Run Predictive Diagnosis"):

    try:
        history = parse_xml(xml_input)

        events = detect_events(history)

        predictions = predictive_analysis(events)

        st.subheader("🔮 Predictive Fault Analysis")

        if not predictions:
            st.success("No predictive fault patterns detected")

        for p in predictions:

            st.error(f"Entry {p['entry']} | Risk Level: {p['level']} ({p['risk']}%)")

            st.write(f"Byte 9: {p['byte9']}")
            st.write(f"Byte 10: {p['byte10']}")

            code = p["byte10"].lower()

            if code in err_map:

                st.write("🧠 Predicted Fault:")
                st.write("**", err_map[code]["name"], "**")
                st.write(err_map[code]["description"])

            else:
                st.warning("Unknown code (not in database)")

            st.divider()

    except Exception as e:
        st.error(f"System Error: {e}")
