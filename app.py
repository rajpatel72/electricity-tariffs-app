import streamlit as st
import pandas as pd

# Upload Excel file
st.title("⚡ Electricity Tariff Lookup (Australia)")
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    # Load all sheets
    xls = pd.ExcelFile(uploaded_file)
    sheet_name = st.selectbox("Select sheet (tariff/region)", xls.sheet_names)

    df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

    st.write("### Preview of Data", df.head())

    # Choose tariff column (assuming file has a 'Tariff' column)
    if "Tariff" in df.columns:
        tariff_choice = st.selectbox("Select tariff", df["Tariff"].unique())
        filtered = df[df["Tariff"] == tariff_choice]
        st.write("### Rates for selected tariff", filtered)
    else:
        st.warning("No 'Tariff' column found. Please check your file structure.")
