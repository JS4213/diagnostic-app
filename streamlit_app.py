import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Diagnostic Root Cause Engine", layout="wide")

st.title("🧠 Root Cause Diagnostic Engine (FINAL)")
st.write("Groups history events into true root causes (not noise detection)")

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
# STEP 1: DETECT RAW EVENTS
# -----------------------------
def detect_events(history):

    events = []

    for i in range(1, len(history)):

        prev = history[i - 1]
        curr = history[i]

        if len(curr) < 11:
            continue

        # ONLY detect transitions from baseline
        if prev[9] == "00" and prev[10] == "00":

            if curr[9] != "00" or curr[10] != "00":

                events.append({
                    "entry": i,
                    "byte9": curr[9],
                    "byte10": curr[10]
                })

    return events


# -----------------------------
# STEP 2: GROUP INTO ROOT CAUSES
# -----------------------------
def build_root_causes(events):

    root_causes = []

    used = set()

    for i, e in enumerate(events):

        if i in used:
            continue

        cluster = [e]

        # group nearby events (noise reduction)
        for j in range(i + 1, len(events)):
            if abs(events[j]["entry"] - e["entry"]) <= 2:
                cluster.append(events[j])
                used.add(j)

        # determine primary fault = first byte10 occurrence
        primary = cluster[0]

        root_causes.append({
            "start_entry": primary["entry"],
            "byte9": primary["byte9"],
            "byte10": primary["byte10"],
            "cluster_size": len(cluster)
        })

    return root_causes


# -----------------------------
# LOAD EXCEL
# -----------------------------
err_map = load_data()


# -----------------------------
# UI
# -----------------------------
xml_input = st.text_area("Paste XML Log", height=300)


if st.button("Run Root Cause Analysis"):

    try:
        history = parse_xml(xml_input)

        events = detect_events(history)

        root_causes = build_root_causes(events)

        st.subheader("🔥 Root Cause Analysis")

        if not root_causes:
            st.success("No faults detected — system stable")

        for rc in root_causes:

            st.error(f"Root Fault at Entry {rc['start_entry']}")

            st.write(f"Byte 9 (Source): {rc['byte9']}")
            st.write(f"Byte 10 (Code): {rc['byte10']}")
            st.write(f"Cluster Size: {rc['cluster_size']} event(s)")

            code = rc["byte10"].lower()

            if code in err_map:

                st.success("🧠 Root Cause Identified")

                st.write("**Error Name:**", err_map[code]["name"])
                st.write("**Description:**", err_map[code]["description"])

            else:
                st.warning("No match in Err Code table")

            st.divider()

    except Exception as e:
        st.error(f"Error parsing XML: {e}")
