import streamlit as st
import pandas as pd

st.title("⚡ Electricity Tariff Lookup (Australia)")

# Upload multiple retailer files
uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:
    # Select retailer (file)
    retailer_choice = st.selectbox("Select Retailer", [f.name for f in uploaded_files])
    file_obj = next(f for f in uploaded_files if f.name == retailer_choice)

    # Load available sheets
    xls = pd.ExcelFile(file_obj)
    sheet_choice = st.selectbox("Select Sheet", xls.sheet_names)

    # Load chosen sheet into dataframe
    df = pd.read_excel(file_obj, sheet_name=sheet_choice)
    st.write("### Preview of Data", df.head())

    # Pick tariff column
    column_choice = st.selectbox("Select Tariff Column", df.columns)

    # Pick tariff value
    tariff_choice = st.selectbox("Select Tariff", df[column_choice].dropna().unique())

    # Filter and show
    filtered = df[df[column_choice] == tariff_choice]
    st.write("### Rates for selected tariff", filtered)
