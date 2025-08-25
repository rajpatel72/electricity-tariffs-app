import streamlit as st
import pandas as pd

st.title("⚡ Electricity Tariff Comparison (Australia)")

# Upload multiple files
uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:
    comparison_data = {}

    for file in uploaded_files:
        st.subheader(f"⚙️ Settings for {file.name}")

        # Load Excel
        xls = pd.ExcelFile(file)
        sheet_choice = st.selectbox(f"Select Sheet for {file.name}", xls.sheet_names, key=file.name+"_sheet")

        df = pd.read_excel(file, sheet_name=sheet_choice)
        st.write("Preview", df.head())

        # Pick tariff column
        column_choice = st.selectbox(f"Select Tariff Column for {file.name}", df.columns, key=file.name+"_col")

        # Normalize tariffs (lowercase, remove spaces/commas)
        df["__tariff_normalized__"] = df[column_choice].astype(str).str.lower().str.replace(r"[\s,]", "", regex=True)

        # Let user pick which tariff to compare
        tariff_choice = st.selectbox(f"Select tariff from {file.name}", df["__tariff_normalized__"].unique(), key=file.name+"_tariff")

        # Save filtered data
        comparison_data[file.name] = df[df["__tariff_normalized__"] == tariff_choice]

    # --- Show Comparison ---
    if comparison_data:
        st.subheader("📊 Tariff Comparison Table")

        # Combine results into one table
        combined = pd.DataFrame()
        for retailer, data in comparison_data.items():
            # Take only numeric columns + keep tariff name
            numeric_cols = data.select_dtypes(include=["number"]).copy()
            numeric_cols["Retailer"] = retailer
            combined = pd.concat([combined, numeric_cols], axis=0)

        if not combined.empty:
            st.write(combined)
