import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import re


# =========================================================
# PAGE SETUP
# =========================================================

st.set_page_config(
    page_title="Diagnostic Root Cause Engine",
    layout="wide"
)

st.title("🧠 Diagnostic Root Cause Engine")

st.write(
    "Paste the complete device log or Reading History below. "
    "The engine automatically detects Regular and Extended Error Source entries."
)


EXCEL_FILE = "Err Code and interpretation_V1.11_APS.xlsx"


# =========================================================
# NORMALISE HEX CODES
# =========================================================

def normalise_code(value):

    if value is None:
        return ""

    value = str(value).strip().lower()

    # Remove Excel-style decimal formatting if present
    if value.endswith(".0"):
        value = value[:-2]

    # Remove 0x if present
    value = value.replace("0x", "")

    # Make two-character hex codes consistent
    if len(value) == 1:
        value = "0" + value

    return value


# =========================================================
# LOAD EXCEL DATA
# =========================================================

@st.cache_data
def load_data():

    xls = pd.ExcelFile(EXCEL_FILE)

    error_codes = {}
    error_sources = {}

    for sheet in xls.sheet_names:

        sheet_lower = sheet.lower()

        # -------------------------------------------------
        # ERR CODE SHEET
        # -------------------------------------------------

        if "err code" in sheet_lower:

            df = pd.read_excel(xls, sheet)

            df.columns = [
                str(c).strip()
                for c in df.columns
            ]

            for _, row in df.iterrows():

                if len(row) < 3:
                    continue

                code = normalise_code(row.iloc[0])

                if not code:
                    continue

                error_codes[code] = {
                    "name": str(row.iloc[1]).strip(),
                    "description": str(row.iloc[2]).strip()
                }


        # -------------------------------------------------
        # ERROR SOURCE SHEET
        # -------------------------------------------------

        if "source" in sheet_lower:

            df = pd.read_excel(xls, sheet)

            df.columns = [
                str(c).strip()
                for c in df.columns
            ]

            for _, row in df.iterrows():

                if len(row) < 2:
                    continue

                code = normalise_code(row.iloc[0])

                if not code:
                    continue

                error_sources[code] = {
                    "description": str(row.iloc[1]).strip()
                }


    return error_codes, error_sources


# =========================================================
# EXTRACT HISTORY ENTRIES
# =========================================================

def extract_history_entries(text):

    """
    Accepts either:

    1. Complete XML
    2. XML containing <entry> records
    3. Raw history lines

    This prevents the 'junk after document element'
    error when multiple <entry> elements are pasted.
    """

    entries = []


    # -----------------------------------------------------
    # FIRST: LOOK FOR <entry>...</entry>
    # -----------------------------------------------------

    xml_entries = re.findall(
        r"<entry\b[^>]*>(.*?)</entry>",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )


    if xml_entries:

        for item in xml_entries:

            bytes_found = re.findall(
                r"\b[0-9a-fA-F]{2}\b",
                item
            )

            if bytes_found:

                entries.append([
                    normalise_code(x)
                    for x in bytes_found
                ])

        return entries


    # -----------------------------------------------------
    # SECOND: TRY COMPLETE XML
    # -----------------------------------------------------

    try:

        root = ET.fromstring(text)

        for entry in root.findall(".//history/entry"):

            if entry.text:

                bytes_found = re.findall(
                    r"\b[0-9a-fA-F]{2}\b",
                    entry.text
                )

                if bytes_found:

                    entries.append([
                        normalise_code(x)
                        for x in bytes_found
                    ])

        if entries:
            return entries

    except Exception:
        pass


    # -----------------------------------------------------
    # THIRD: RAW HEX LINES
    # -----------------------------------------------------

    for line in text.splitlines():

        bytes_found = re.findall(
            r"\b[0-9a-fA-F]{2}\b",
            line
        )

        if len(bytes_found) >= 8:

            entries.append([
                normalise_code(x)
                for x in bytes_found
            ])


    return entries


# =========================================================
# FIND REGULAR FAULT EVENTS
# =========================================================

def find_regular_events(history):

    events = []

    for i in range(1, len(history)):

        previous = history[i - 1]
        current = history[i]

        if len(previous) < 11:
            continue

        if len(current) < 11:
            continue


        previous_source = normalise_code(previous[9])
        previous_code = normalise_code(previous[10])

        current_source = normalise_code(current[9])
        current_code = normalise_code(current[10])


        # -------------------------------------------------
        # REGULAR ERROR ENTRY
        #
        # Previous state = 00 / 00
        # Current state = something other than 00 / 00
        # -------------------------------------------------

        if (
            previous_source == "00"
            and
            previous_code == "00"
            and
            (
                current_source != "00"
                or
                current_code != "00"
            )
        ):

            events.append({
                "index": i,
                "type": "regular",
                "source": current_source,
                "code": current_code
            })


    return events


# =========================================================
# FIND EXTENDED ERROR SOURCE EVENTS
# =========================================================

def find_extended_events(history):

    events = []


    for i, current in enumerate(history):

        if len(current) < 11:
            continue


        byte9 = normalise_code(current[9])


        # -------------------------------------------------
        # BYTE 9 = 20
        #
        # This is an Extended Error Source Entry
        # -------------------------------------------------

        if byte9 != "20":
            continue


        # Need the following TWO rows
        if i + 2 >= len(history):
            continue


        row1 = history[i + 1]
        row2 = history[i + 2]


        module_data = row1 + row2


        # First 24 values correspond to Modules 1-24
        module_data = module_data[:24]


        module_faults = []


        for module_number, error_code in enumerate(
            module_data,
            start=1
        ):

            error_code = normalise_code(error_code)


            # 00 = no error
            if error_code == "00":
                continue


            # FF is unused/invalid padding
            if error_code == "ff":
                continue


            module_faults.append({
                "module": module_number,
                "code": error_code
            })


        if module_faults:

            events.append({
                "index": i,
                "type": "extended",
                "modules": module_faults
            })


    return events


# =========================================================
# REMOVE DUPLICATE EVENTS
# =========================================================

def remove_duplicates(events):

    unique = []
    seen = set()


    for event in events:

        if event["type"] == "regular":

            key = (
                "regular",
                event["source"],
                event["code"]
            )


        else:

            module_key = tuple(
                (
                    x["module"],
                    x["code"]
                )
                for x in event["modules"]
            )

            key = (
                "extended",
                module_key
            )


        if key not in seen:

            seen.add(key)

            unique.append(event)


    return unique


# =========================================================
# LOAD EXCEL
# =========================================================

try:

    error_codes, error_sources = load_data()

except Exception as e:

    st.error(
        "I couldn't load the Excel file. "
        "Make sure 'Err Code and interpretation_V1.11_APS.xlsx' "
        "is in the same GitHub repository as this app."
    )

    st.stop()


# =========================================================
# USER INPUT
# =========================================================

xml_input = st.text_area(
    "Paste Device Reading History Here",
    height=400,
    placeholder="Paste the complete log from your Notes app here..."
)


# =========================================================
# RUN DIAGNOSIS
# =========================================================

if st.button(
    "🔎 Run Root Cause Analysis",
    type="primary"
):

    if not xml_input.strip():

        st.warning(
            "Please paste a Reading History log first."
        )

        st.stop()


    try:

        # -------------------------------------------------
        # EXTRACT HISTORY
        # -------------------------------------------------

        history = extract_history_entries(xml_input)


        if not history:

            st.error(
                "I couldn't find any valid Reading History entries."
            )

            st.stop()


        # -------------------------------------------------
        # FIND REGULAR FAULTS
        # -------------------------------------------------

        regular_events = find_regular_events(history)


        # -------------------------------------------------
        # FIND EXTENDED FAULTS
        # -------------------------------------------------

        extended_events = find_extended_events(history)


        # -------------------------------------------------
        # COMBINE
        # -------------------------------------------------

        all_events = (
            regular_events
            +
            extended_events
        )


        # -------------------------------------------------
        # REMOVE DUPLICATES
        # -------------------------------------------------

        all_events = remove_duplicates(all_events)


        # =================================================
        # RESULTS
        # =================================================

        st.subheader("🔥 Diagnostic Result")


        if not all_events:

            st.success(
                "No new faults detected in the Reading History."
            )

        else:

            # =================================================
            # REGULAR EVENTS
            # =================================================

            for event in all_events:

                if event["type"] != "regular":
                    continue


                source = event["source"]
                code = event["code"]


                st.error(
                    "🚨 Fault Detected"
                )


                # -------------------------------------------------
                # ERROR SOURCE
                # -------------------------------------------------

                st.markdown(
                    f"### Error Source: `{source.upper()}`"
                )


                if source in error_sources:

                    st.write(
                        error_sources[source]["description"]
                    )

                else:

                    st.warning(
                        "Error source not found in "
                        "Error Source_komplete."
                    )


                # -------------------------------------------------
                # ERROR CODE
                # -------------------------------------------------

                st.markdown(
                    f"### Error Code: `{code.upper()}`"
                )


                if code in error_codes:

                    st.write(
                        "**Error Name:** "
                        + error_codes[code]["name"]
                    )

                    st.write(
                        "**Description:** "
                        + error_codes[code]["description"]
                    )

                else:

                    st.warning(
                        f"Error code `{code.upper()}` "
                        "was not found in the Err Code sheet."
                    )


                st.caption(
                    f"Detected at history entry {event['index'] + 1}"
                )


                st.divider()


            # =================================================
            # EXTENDED EVENTS
            # =================================================

            for event in all_events:

                if event["type"] != "extended":
                    continue


                st.error(
                    "🚨 Extended Error Source Entry Detected"
                )


                st.markdown(
                    "### Extended Module Faults"
                )


                for module_fault in event["modules"]:

                    module_number = module_fault["module"]
                    code = module_fault["code"]


                    st.markdown(
                        f"#### Module {module_number}"
                    )


                    st.write(
                        f"**Error Code:** `{code.upper()}`"
                    )


                    # -------------------------------------------------
                    # LOOK UP ERROR CODE
                    # -------------------------------------------------

                    if code in error_codes:

                        st.write(
                            "**Error Name:** "
                            + error_codes[code]["name"]
                        )

                        st.write(
                            "**Description:** "
                            + error_codes[code]["description"]
                        )

                    else:

                        st.warning(
                            f"Error code `{code.upper()}` "
                            "was not found in the Err Code sheet."
                        )


                st.caption(
                    f"Detected at history entry {event['index'] + 1}"
                )


                st.divider()


        # =================================================
        # SMALL SUMMARY
        # =================================================

        st.subheader("📊 Analysis Summary")

        st.write(
            f"History entries analysed: **{len(history)}**"
        )

        st.write(
            f"Fault events detected: **{len(all_events)}**"
        )


    except Exception as e:

        st.error(
            f"Something went wrong while analysing the log: {e}"
        )
