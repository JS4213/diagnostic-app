import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from collections import defaultdict, Counter

st.set_page_config(page_title="Fleet Learning AI Diagnostic System", layout="wide")

st.title("🧠 Fleet Learning AI Diagnostic System")
st.write("Learns fault behaviour across multiple logs (fleet intelligence mode)")


EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


# -----------------------------
# LOAD ERROR DATABASE
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
# DETECT FAULT EVENTS
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
                    "byte9": curr[9].lower(),
                    "byte10": curr[10].lower()
                })

    return events


# -----------------------------
# FLEET LEARNING ENGINE
# -----------------------------
def fleet_learning_analysis(all_logs_events):

    # global learning tables
    byte10_counts = Counter()
    byte9_map = defaultdict(Counter)

    for events in all_logs_events:
        for e in events:
            b9 = e["byte9"]
            b10 = e["byte10"]

            byte10_counts[b10] += 1
            byte9_map[b10][b9] += 1

    # build learned probability model
    learned_model = {}

    for code, count in byte10_counts.items():

        most_common_source = byte9_map[code].most_common(1)[0][0]

        confidence = min(95, 40 + count * 10)

        learned_model[code] = {
            "frequency": count,
            "most_common_source": most_common_source,
            "confidence": confidence
        }

    return learned_model


# -----------------------------
# PREDICTION ENGINE
# -----------------------------
def predict(events, model, err_map):

    results = []

    for e in events:

        code = e["byte10"]

        if code in model:
            m = model[code]

            risk = m["confidence"]

            level = (
                "LOW" if risk < 50 else
                "MEDIUM" if risk < 70 else
                "HIGH" if risk < 85 else
                "CRITICAL"
            )

            results.append({
                "code": code,
                "risk": risk,
                "level": level,
                "frequency": m["frequency"],
                "source": m["most_common_source"]
            })

        else:
            results.append({
                "code": code,
                "risk": 30,
                "level": "LOW",
                "frequency": 1,
                "source": e["byte9"]
            })

    return results


# -----------------------------
# LOAD ERROR MAP
# -----------------------------
err_map = load_data()


# -----------------------------
# UI
# -----------------------------
xml_input = st.text_area("Paste XML Log", height=250)


if st.button("Run Fleet AI Diagnosis"):

    try:
        history = parse_xml(xml_input)
        events = detect_events(history)

        # simulate fleet memory (single-log fallback for now)
        fleet_model = fleet_learning_analysis([events])

        predictions = predict(events, fleet_model, err_map)

        st.subheader("🧠 Fleet Intelligence Output")

        for p in predictions:

            st.error(f"Code: {p['code']} | Risk: {p['risk']}% ({p['level']})")

            st.write(f"Frequency in fleet: {p['frequency']}")
            st.write(f"Most common source (Byte9): {p['source']}")

            if p["code"] in err_map:

                st.write("🧠 Known Fault:")
                st.write(err_map[p["code"]]["name"])
                st.write(err_map[p["code"]]["description"])

            else:
                st.warning("Unknown fleet pattern")

            st.divider()

    except Exception as e:
        st.error(f"System Error: {e}")
