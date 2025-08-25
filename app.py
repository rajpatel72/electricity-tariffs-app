import streamlit as st
import pandas as pd
import re

st.title("⚡ Smart Electricity Tariff Comparator")

# Define synonyms for rate columns
COLUMN_SYNONYMS = {
    "peak": ["peak", "peak usage", "peak_rate", "pk1", "peak_block1_rate"],
    "shoulder": ["shoulder", "shoulder_rate", "shoulder_block1_rate"],
    "offpeak": ["off peak", "offpeak", "off_peak", "op", "offpeak_block1_rate"],
    "daily": ["daily supply charge", "daily charge", "service_to_property"],
    "controlled_load1": ["cl1", "controlled load 1", "controlled_load1_block1_rate"],
    "controlled_load2": ["cl2", "controlled load 2", "controlled_load2"],
    "demand1": ["demand1", "demand 1", "demand_1_rate"],
    "demand2": ["demand2", "demand 2", "demand_2_rate"]
}

def normalize_text(s):
    if not isinstance(s, str):
        return ""
    return re.sub(r"[\s,._-]", "", s).lower()

def match_column(col_name):
    """Map raw column name to a standard category"""
    cname = normalize_text(col_name)
    for standard, options in COLUMN_SYNONYMS.items():
        for opt in options:
            if opt.replace(" ", "") in cname:
                return standard
    return None

# Upload files
uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:
    # User enters one tariff code to search across all
    tariff_input = st.text_input("Enter tariff code to search (e.g. d1dd1)").lower().replace(" ", "").replace(",", "")

    if tariff_input:
        results = []

        for file in uploaded_files:
            xls = pd.ExcelFile(file)
            for sheet in xls.sheet_names:
                try:
                    df = pd.read_excel(file, sheet_name=sheet)
                except:
                    continue

                # Normalize tariff column candidates
                for col in df.columns:
                    df[col] = df[col].astype(str)
                    df["__norm_tariff__"] = df[col].str.lower().str.replace(r"[\s,]", "", regex=True)

                    if tariff_input in df["__norm_tariff__"].values:
                        # Map useful columns
                        row = df[df["__norm_tariff__"] == tariff_input].iloc[0]
                        normalized_row = {"Retailer": file.name, "Sheet": sheet, "Tariff": row[col]}

                        for c in df.columns:
                            mapped = match_column(c)
                            if mapped:
                                normalized_row[mapped] = row[c]

                        results.append(normalized_row)

        if results:
            st.subheader("📊 Comparison Table")
            st.write(pd.DataFrame(results))
        else:
            st.warning("No matching tariffs found in uploaded files.")
