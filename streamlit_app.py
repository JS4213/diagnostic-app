import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Industrial AI Diagnostic System", layout="wide")

st.title("🏭 Industrial AI Diagnostic System")
st.write("Root cause analysis + timeline reconstruction + fault clustering engine")

EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


# -----------------------------
# LOAD EXCEL MAPS
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
# STEP 1: DETECT EVENTS
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
                    "byte10": curr[10],
                    "raw": curr
                })

    return events


# -----------------------------
# STEP 2: CLUSTER EVENTS (FAULT INCIDENTS)
# -----------------------------
def cluster_events(events):

    if not events:
        return []

    clusters = []
    current_cluster = [events[0]]

    for i in range(1, len(events)):

        # if close in time → same fault incident
        if events[i]["index"] - events[i-1]["index"] <= 2:
            current_cluster.append(events[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [events[i]]

    clusters.append(current_cluster)

    return clusters


# -----------------------------
# STEP 3: TIMELINE + ROOT CAUSE LOGIC
# -----------------------------
def analyze_clusters(clusters):

    incidents = []

    for cluster in clusters:

        primary = cluster[0]

        # determine severity based on known patterns
        severity = "LOW"

        for e in cluster:
            if e["byte10"].lower() in ["ef", "77", "1f"]:
                severity = "HIGH"

        incidents.append({
            "start": primary["index"],
            "end": cluster[-1]["index"],
            "events": cluster,
            "primary_byte9": primary["byte9"],
            "primary_byte10": primary["byte10"],
            "severity": severity,
            "confidence": "HIGH" if len(cluster) > 1 else "MEDIUM"
        })

    return incidents


# -----------------------------
# LOAD ERROR TABLE
# -----------------------------
err_map = load_data()


# -----------------------------
# UI
# -----------------------------
xml_input = st.text_area("Paste XML Log", height=300)


if st.button("Run Industrial Diagnosis"):

    try:
        history = parse_xml(xml_input)

        events = detect_events(history)

        clusters = cluster_events(events)

        incidents = analyze_clusters(clusters)

        st.subheader("🏭 Industrial Diagnostic Report")

        if not incidents:
            st.success("No faults detected — system stable")

        for inc in incidents:

            st.error(f"Fault Incident: Entries {inc['start']} → {inc['end']}")

            st.write(f"Severity: {inc['severity']}")
            st.write(f"Confidence: {inc['confidence']}")

            code = inc["primary_byte10"].lower()

            # -----------------------------
            # ROOT CAUSE LOOKUP
            # -----------------------------
            if code in err_map:

                st.success("🧠 Root Cause Identified")

                st.write("**Error Name:**", err_map[code]["name"])
                st.write("**Description:**", err_map[code]["description"])

            else:
                st.warning(f"No match in error database for code: {code}")

            # -----------------------------
            # TIMELINE DISPLAY
            # -----------------------------
            st.write("📍 Event Timeline:")

            for e in inc["events"]:
                st.write(f"- Entry {e['index']} | B9:{e['byte9']} | B10:{e['byte10']}")

            st.divider()

    except Exception as e:
        st.error(f"System Error: {e}")
