import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd


st.set_page_config(
    page_title="Diagnostic Root Cause Engine",
    layout="wide"
)


st.title("🧠 Diagnostic Root Cause Engine")
st.write("Reads Reading History entries using Regular and Extended Error Source logic")


EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


# =====================================================
# LOAD EXCEL DATA
# =====================================================

@st.cache_data
def load_data():

    xls = pd.ExcelFile(EXCEL_FILE)

    error_codes = {}
    error_sources = {}

    for sheet in xls.sheet_names:

        sheet_lower = sheet.lower()

        # -----------------------------
        # ERROR CODE TABLE
        # -----------------------------
        if "err code" in sheet_lower:

            df = pd.read_excel(xls, sheet)
            df.columns = [str(c).strip() for c in df.columns]

            for _, row in df.iterrows():

                code = str(row.iloc[0]).strip().lower()

                error_codes[code] = {
                    "name": str(row.iloc[1]),
                    "description": str(row.iloc[2])
                }


        # -----------------------------
        # ERROR SOURCE TABLE
        # -----------------------------
        if "source" in sheet_lower:

            df = pd.read_excel(xls, sheet)
            df.columns = [str(c).strip() for c in df.columns]

            for _, row in df.iterrows():

                code = str(row.iloc[0]).strip().lower()

                error_sources[code] = {
                    "description": str(row.iloc[1])
                }


    return error_codes, error_sources



# =====================================================
# READ XML HISTORY
# =====================================================

def parse_history(xml_text):

    root = ET.fromstring(xml_text)

    history = []

    for entry in root.findall(".//history/entry"):

        if entry.text:

            history.append(
                entry.text.strip().split()
            )

    return history



# =====================================================
# FIND NEW FAULT EVENTS
# =====================================================

def find_fault_events(history):

    events = []


    for i in range(1, len(history)):


        previous = history[i-1]
        current = history[i]


        if len(current) < 11:
            continue


        previous_source = previous[9]
        previous_code = previous[10]


        current_source = current[9]
        current_code = current[10]



        # Detect transition from normal state

        if previous_source == "00" and previous_code == "00":


            if current_source != "00" or current_code != "00":


                events.append({
                    "index": i,
                    "entry": current
                })


    return events



# =====================================================
# REGULAR ERROR ENTRY
# =====================================================

def decode_regular(entry, error_codes, error_sources):


    source = entry[9].lower()
    code = entry[10].lower()


    result = {

        "type": "Regular Error Source Entry",

        "source_code": source,

        "error_code": code

    }


    if source in error_sources:

        result["source_description"] = (
            error_sources[source]["description"]
        )

    else:

        result["source_description"] = "Unknown source"



    if code in error_codes:

        result["error_name"] = (
            error_codes[code]["name"]
        )

        result["error_description"] = (
            error_codes[code]["description"]
        )

    else:

        result["error_name"] = "Unknown"

        result["error_description"] = "No matching error code"



    return result



# =====================================================
# EXTENDED ERROR ENTRY
# =====================================================

def decode_extended(history, position, error_codes):


    results = []


    # next two rows contain module information

    module_bytes = []


    for row in history[position+1:position+3]:

        module_bytes.extend(row)



    # first 24 values = modules

    for module_number, code in enumerate(module_bytes[:24], start=1):


        code_clean = code.lower()


        # ignore normal modules

        if code_clean == "00":

            continue



        result = {

            "type": "Extended Error Source Entry",

            "module": module_number,

            "error_code": code_clean

        }



        if code_clean in error_codes:

            result["error_name"] = (
                error_codes[code_clean]["name"]
            )

            result["error_description"] = (
                error_codes[code_clean]["description"]
            )

        else:

            result["error_name"] = "Unknown"

            result["error_description"] = (
                "No matching error code"
            )



        results.append(result)



    return results



# =====================================================
# LOAD DATA
# =====================================================

error_codes, error_sources = load_data()



# =====================================================
# USER INPUT
# =====================================================

xml_input = st.text_area(
    "Paste XML Reading History",
    height=300
)



if st.button("Run Root Cause Analysis"):


    try:


        history = parse_history(xml_input)


        events = find_fault_events(history)



        st.subheader("🔥 Root Cause Results")



        if not events:

            st.success(
                "No new faults detected"
            )



        for event in events:


            index = event["index"]

            entry = event["entry"]


            byte9 = entry[9].lower()



            # ---------------------------------
            # EXTENDED MODE
            # ---------------------------------

            if byte9 == "20":


                st.warning(
                    f"Extended Error Source Entry detected (History row {index})"
                )


                results = decode_extended(
                    history,
                    index,
                    error_codes
                )


                for r in results:


                    st.error(
                        f"Module {r['module']} Fault"
                    )


                    st.write(
                        "Error Code:",
                        r["error_code"]
                    )


                    st.write(
                        "Error Name:",
                        r["error_name"]
                    )


                    st.write(
                        "Description:",
                        r["error_description"]
                    )



            # ---------------------------------
            # REGULAR MODE
            # ---------------------------------

            else:


                result = decode_regular(
                    entry,
                    error_codes,
                    error_sources
                )


                st.error(
                    result["type"]
                )


                st.write(
                    "Error Source:",
                    result["source_code"]
                )


                st.write(
                    result["source_description"]
                )


                st.write(
                    "Error Code:",
                    result["error_code"]
                )


                st.write(
                    "Error Name:",
                    result["error_name"]
                )


                st.write(
                    "Description:",
                    result["error_description"]
                )



            st.divider()



    except Exception as e:

        st.error(
            f"Error processing XML: {e}"
        )
