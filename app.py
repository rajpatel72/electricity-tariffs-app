import streamlit as st
import pandas as pd
import re, io

st.title("⚡ Flexible Electricity Tariff Comparator (per-sheet mapping)")

def normalize_text(s: str) -> str:
    return re.sub(r"[\s,._-]", "", str(s)).lower()

def excel_file(uploaded_file):
    """Return a fresh ExcelFile each time (avoids stale pointer)."""
    return pd.ExcelFile(io.BytesIO(uploaded_file.getvalue()))

def read_sheet(uploaded_file, sheet_name):
    """Read a specific sheet from a fresh buffer."""
    return pd.read_excel(io.BytesIO(uploaded_file.getvalue()), sheet_name=sheet_name)

uploaded_files = st.file_uploader(
    "Upload Excel files", type=["xlsx"], accept_multiple_files=True
)

if uploaded_files:
    # One tariff to search across all files/sheets (normalized)
    tariff_input_raw = st.text_input("Enter tariff code (e.g. D1DD1)")
    tariff_input = normalize_text(tariff_input_raw) if tariff_input_raw else ""

    results = []

    for uf in uploaded_files:
        st.markdown(f"### 📂 Settings for `{uf.name}`")

        # 1) Pick SHEET (from this file only)
        xls = excel_file(uf)
        sheet_key = f"sheet::{uf.name}"
        sheet_name = st.selectbox(
            f"Select sheet in {uf.name}",
            options=xls.sheet_names,
            key=sheet_key
        )

        # 2) Read the SELECTED sheet only (fresh buffer)
        df = read_sheet(uf, sheet_name)

        st.caption("Preview of selected sheet")
        st.dataframe(df.head())

        # 3) Pick columns FROM THE SELECTED SHEET ONLY
        # Use keys that depend on file + sheet so widgets refresh when sheet changes
        tariff_key = f"tariff_col::{uf.name}::{sheet_name}"
        rates_key  = f"rate_cols::{uf.name}::{sheet_name}"

        tariff_col = st.selectbox(
            f"Select tariff column in {uf.name} → {sheet_name}",
            options=df.columns.tolist(),
            key=tariff_key
        )

        rate_cols = st.multiselect(
            f"Select rate columns in {uf.name} → {sheet_name}",
            options=df.columns.tolist(),
            key=rates_key
        )

        # 4) If a tariff is provided, find it in this sheet (tolerant to commas/spaces/case)
        if tariff_input:
            try:
                norm = df[tariff_col].astype(str).apply(normalize_text)
                matches = df[norm == tariff_input]
                if not matches.empty:
                    row = matches.iloc[0]
                    out = {
                        "Retailer": uf.name,
                        "Sheet": sheet_name,
                        "Tariff": row[tariff_col],
                    }
                    for c in rate_cols:
                        out[c] = row.get(c, None)
                    results.append(out)
                else:
                    st.warning(f"No matching tariff `{tariff_input_raw}` found in **{uf.name} → {sheet_name}**.")
            except Exception as e:
                st.error(f"Error searching in {uf.name} → {sheet_name}: {e}")

    # 5) Combined comparison table
    if results:
        st.markdown("## 📊 Tariff Comparison Table")
        res_df = pd.DataFrame(results)

        # Move identifying columns to the front
        id_cols = [c for c in ["Retailer", "Sheet", "Tariff"] if c in res_df.columns]
        other_cols = [c for c in res_df.columns if c not in id_cols]
        res_df = res_df[id_cols + other_cols]

        st.dataframe(res_df)

        # Optional chart
        if st.checkbox("Show bar chart for selected rate columns"):
            if other_cols:
                melted = res_df.melt(id_vars=id_cols, var_name="Rate Type", value_name="Value")
                # Try numeric conversion where possible
                melted["Value"] = pd.to_numeric(melted["Value"], errors="coerce")
                st.bar_chart(melted.dropna(subset=["Value"]), x="Rate Type", y="Value", color="Retailer")
            else:
                st.info("Pick at least one rate column above to chart.")
