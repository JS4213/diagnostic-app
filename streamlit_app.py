import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Diagnostic Agent", layout="wide")

st.title("🧠 Diagnostic Agent")
st.write("Paste your device log below and get instant fault diagnosis.")

# Load Excel file (you will upload it to GitHub later)
EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


@st.cache_data
def load_data():
    xls = pd.ExcelFile(EXCEL_FILE)

    err_map = {}
    source_map = {}

    for sheet in xls.sheet_names:
        if "err" in sheet.lower():
            df = pd.read_excel(xls, sheet)
            df.columns = [c.strip() for c in df.columns]

            for _, row in df.iterrows():
                code = str(row.iloc[0]).strip()
                err_map[code] = row.to_dict()

        if "source" in sheet.lower():
            df = pd.read_excel(xls, sheet)
            df.columns = [c.strip() for c in df.columns]

            for _, row in df.iterrows():
                key = str(row.iloc[0]).strip()
                source_map[key] = row.to_dict()

    return err_map, source_map


def extract_codes(text):
    return list(set(re.findall(r"0x[0-9a-fA-F]+", text)))


try:
    err_map, source_map = load_data()
except Exception as e:
    st.error("Missing Excel file. Upload it to the same GitHub repo.")
    st.stop()


log = st.text_area("Paste Log Here", height=250)

if st.button("Run Diagnosis"):
    codes = extract_codes(log)

    if not codes:
        st.warning("No error codes found.")
    else:
        for code in codes:
            st.subheader(f"Code: {code}")

            if code in err_map:
                st.success("Matched Error Code")

                data = err_map[code]

                # show clean output
                st.write("**Error Details:**")
                st.json(data)

            else:
                st.error("Unknown Code")
