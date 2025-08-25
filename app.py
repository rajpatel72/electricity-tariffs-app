import streamlit as st
import pandas as pd
import re

st.title("⚡ Flexible Electricity Tariff Comparator")

def normalize_text(s):
    if not isinstance(s, str):
        return ""
    return re.sub(r"[\s,._-]", "", str(s)).lower()

uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:
    tariff_input = st.text_input("Enter tariff code (e.g. D1DD1)").strip().lower().replace(",", "").replace(" ", "")
    results = []

    for file in uploaded_files:
        st.subheader(f"📂 Settings for `{file.name}`")

        # Load file and show available sheets
        xls = pd.ExcelFile(file)
        sheet_name = st.selectbox(f"Select sheet in {file.name}", xls.sheet_names, key=file.name)

        # Read the SELECTED sheet only
        df = pd.read_excel(file, sheet_name=sheet_name)

        # Preview
        st.write("Preview of data:")
        st.dataframe(df.head())

        # Tariff column selector (now from selected sheet only)
        tariff_col = st.selectbox(f"Select tariff column in {file.name} ({sheet_name})", df.columns, key=file.name+"_tariff")

        # Rate columns selector (from selected sheet only)
        rate_cols = st.multiselect(f"Select rate columns in {file.name} ({sheet_name})", df.columns, key=file.name+"_rates")

        # Process search
        if tariff_input:
            df["__norm_tariff__"] = df[tariff_col].astype(str).apply(normalize_text)

            if tariff_input in df["__norm_tariff__"].values:
                row = df[df["__norm_tariff__"] == tariff_input].iloc[0]
                normalized_row = {"Retailer": file.name, "Sheet": sheet_name, "Tariff": row[tariff_col]}

                for c in rate_cols:
                    normalized_row[c] = row[c]

                results.append(normalized_row)
            else:
                st.warning(f"No matching tariff `{tariff_input}` found in {file.name} ({sheet_name})")

    # Final comparison table
    if results:
        st.subheader("📊 Tariff Comparison Table")
        results_df = pd.DataFrame(results)
        st.dataframe(results_df)

        # Optional chart view
        if st.checkbox("Show chart comparison"):
            melted = results_df.melt(id_vars=["Retailer", "Tariff"], var_name="Rate Type", value_name="Value")
            st.bar_chart(melted, x="Rate Type", y="Value", color="Retailer")
