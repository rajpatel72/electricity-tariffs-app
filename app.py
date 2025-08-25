import streamlit as st
import pandas as pd
import re, io

st.set_page_config(page_title="Electricity Tariff Comparator", layout="wide")
st.title("⚡ Smart Electricity Tariff Comparator")

# ---------- Helpers ----------
def fresh_bytes(uploaded_file):
    """Return a new BytesIO for every read (avoids stale sheet/first-sheet issues)."""
    return io.BytesIO(uploaded_file.getvalue())

def read_excel_file(uploaded_file):
    return pd.ExcelFile(fresh_bytes(uploaded_file))

def read_sheet(uploaded_file, sheet_name):
    return pd.read_excel(fresh_bytes(uploaded_file), sheet_name=sheet_name)

def normalize_text(s):
    """Lowercase + remove spaces/commas/dots/underscores/hyphens to match 'd1,dd1' with 'd1dd1'."""
    return re.sub(r"[ \t\n\r,._-]", "", str(s)).lower()

# Column alias logic (optional)
ALIASES = {
    "peak": [
        "peak","peakusage","peakinclgst","peakexgst","peak_rate","peak1","pk","pk1",
        "anytime","generalusage","single","singleusage","energy_peak","peakblock1rate",
        "tariff_anytime_peak","usage_std"
    ],
    "shoulder": ["shoulder","shoulderusage","shoulder_rate","shoulder1","sh","sh1","shoulderblock1rate"],
    "offpeak": [
        "offpeak","off_peak","off peak","op","op1","offpeakusage","offpeak_rate",
        "offpeakblock1rate","eveningoffpeak","overnight"
    ],
    "daily": [
        "dailysupplycharge","dailycharge","service_to_property","servicetoproperty",
        "supplycharge","fixedcharge","supply","daily"
    ],
    "cl1": ["cl1","controlledload1","controlled_load1","controlledload_1","cl 1"],
    "cl2": ["cl2","controlledload2","controlled_load2","controlledload_2","cl 2"],
    "demand1": ["demand1","demand_1","demand 1","kwdemand","maxdemand","demandkw"],
    "demand2": ["demand2","demand_2","demand 2"],
    "feedin": ["feedin","feed-in","fit","solarfeedin","solarfeed-in","exporttariff","feedintariff"]
}

# Make sure 'offpeak' is checked before 'peak' to avoid accidental mapping
CANON_ORDER = ["offpeak","peak","shoulder","daily","cl1","cl2","demand1","demand2","feedin"]

def canonical_name(raw):
    n = normalize_text(raw)
    # check in priority order
    for canon in CANON_ORDER + [k for k in ALIASES if k not in CANON_ORDER]:
        for alias in ALIASES.get(canon, []):
            if alias in n:
                # add _incl_gst or _ex_gst suffix if detectable
                if "inclgst" in n or "incl.gst" in n or "incl" in n and "gst" in n:
                    return f"{canon}_incl_gst"
                if "exgst" in n or ("ex" in n and "gst" in n):
                    return f"{canon}_ex_gst"
                return canon
    return None

def apply_aliases(df, id_col):
    """Rename columns to canonical labels where possible (non-id columns only)."""
    new_cols = {}
    used = set()
    for c in df.columns:
        if c == id_col: 
            continue
        m = canonical_name(c)
        if m is None:
            continue
        # Prevent collisions: if already used, keep original to avoid overwriting
        if m in used:
            continue
        new_cols[c] = m
        used.add(m)
    return df.rename(columns=new_cols)

# ---------- UI: Upload + global tariff ----------
uploaded_files = st.file_uploader("Upload Excel files (multiple allowed)", type=["xlsx"], accept_multiple_files=True)

col1, col2 = st.columns([2,1])
with col1:
    tariff_raw = st.text_input("Enter the tariff code to search (e.g., D1DD1)").strip()
with col2:
    loose = st.checkbox("Loose match (contains)", value=False, help="If exact normalized match fails, use substring contains.")

smart_alias = st.checkbox("Apply smart column aliases (Peak/Offpeak/Daily alignment)", value=True)

if uploaded_files and tariff_raw:
    tariff_norm = normalize_text(tariff_raw)
    results = []
    messages = []

    for uf in uploaded_files:
        st.markdown(f"---\n### 📂 {uf.name}")
        xls = read_excel_file(uf)
        sheet = st.selectbox(
            f"Select sheet in **{uf.name}**",
            options=xls.sheet_names,
            key=f"sheet::{uf.name}"
        )

        df_raw = read_sheet(uf, sheet)
        st.caption("Preview of selected sheet")
        st.dataframe(df_raw.head())

        # Tariff column (from this sheet only)
        tariff_col = st.selectbox(
            f"Select **tariff column** in {uf.name} → {sheet}",
            options=df_raw.columns.tolist(),
            key=f"tariff_col::{uf.name}::{sheet}"
        )

        # Layout: columns vs rows
        layout = st.radio(
            f"How are rates stored in {uf.name} → {sheet}?",
            ["Rates are in columns", "Rates are in rows"],
            key=f"layout::{uf.name}::{sheet}",
            horizontal=True
        )

        if layout == "Rates are in columns":
            working_df = df_raw.copy()
            # Let user choose which rate columns to keep
            rate_cols = st.multiselect(
                f"Select rate columns (usage, daily, demand, etc.) in {uf.name} → {sheet}",
                options=[c for c in working_df.columns if c != tariff_col],
                key=f"rate_cols::{uf.name}::{sheet}"
            )

        else:
            # Rates are in rows: need a "type" column and a "value" column
            rate_type_col = st.selectbox(
                "Select the column that contains **rate type names** (e.g., Peak, Offpeak, Daily Supply)",
                options=[c for c in df_raw.columns if c != tariff_col],
                key=f"rate_type_col::{uf.name}::{sheet}"
            )
            rate_value_col = st.selectbox(
                "Select the column that contains **rate values**",
                options=[c for c in df_raw.columns if c != tariff_col],
                key=f"rate_value_col::{uf.name}::{sheet}"
            )

            # Pivot rows ➜ columns
            try:
                working_df = df_raw.pivot_table(
                    index=tariff_col,
                    columns=rate_type_col,
                    values=rate_value_col,
                    aggfunc="first"
                ).reset_index()
            except Exception as e:
                st.error(f"Pivot failed: {e}")
                continue

            # After pivot, all rate columns are candidates (except tariff)
            rate_cols = st.multiselect(
                f"Select rate columns (after pivot) in {uf.name} → {sheet}",
                options=[c for c in working_df.columns if c != tariff_col],
                default=[c for c in working_df.columns if c != tariff_col],
                key=f"rate_cols_pivot::{uf.name}::{sheet}"
            )

        # Optional smart aliasing (on the pivoted/working df)
        if smart_alias:
            working_df = apply_aliases(working_df, id_col=tariff_col)

        # Find the tariff row (tolerant)
        try:
            norm_series = working_df[tariff_col].astype(str).apply(normalize_text)
            if loose:
                matches = working_df[norm_series.str.contains(tariff_norm, na=False)]
            else:
                matches = working_df[norm_series == tariff_norm]

            if matches.empty and not loose:
                # automatic fallback to contains
                contains_matches = working_df[norm_series.str.contains(tariff_norm, na=False)]
                if not contains_matches.empty:
                    messages.append(f"ℹ️ Used loose match for **{uf.name} → {sheet}** (no exact normalized match).")
                    matches = contains_matches

            if matches.empty:
                st.warning(f"No match for tariff `{tariff_raw}` in **{uf.name} → {sheet}**.")
                continue

            if len(matches) > 1:
                st.info(f"Multiple matches found in **{uf.name} → {sheet}** — taking the first. (Matches: {len(matches)})")

            row = matches.iloc[0]

            # Build result row
            out = {
                "Retailer": uf.name,
                "Sheet": sheet,
                "Tariff (original)": row[tariff_col],
            }

            # Keep only selected rate columns; if none selected, try to include all except id
            chosen_cols = rate_cols if rate_cols else [c for c in working_df.columns if c != tariff_col]
            for c in chosen_cols:
                out[str(c)] = row.get(c, None)

            results.append(out)

        except Exception as e:
            st.error(f"Error processing {uf.name} → {sheet}: {e}")

    # ---- Combined output ----
    if results:
        st.markdown("## 📊 Side-by-side Comparison")
        res_df = pd.DataFrame(results)

        # Move identifiers first
        id_cols = [c for c in ["Retailer", "Sheet", "Tariff (original)"] if c in res_df.columns]
        other_cols = [c for c in res_df.columns if c not in id_cols]
        res_df = res_df[id_cols + other_cols]

        # Try numeric conversion for charting (without altering the displayed table types)
        numeric_cols = {}
        for c in other_cols:
            numeric_cols[c] = pd.to_numeric(res_df[c].astype(str).str.replace(r"[^\d\.-]", "", regex=True), errors="coerce")

        st.dataframe(res_df, use_container_width=True)

        if messages:
            with st.expander("Match notes"):
                for m in messages:
                    st.write(m)

        # Chart
        st.markdown("### 📈 Quick Chart (select columns)")
        chart_cols = st.multiselect(
            "Choose rate types to chart",
            options=other_cols,
            default=[c for c in other_cols if any(k in normalize_text(c) for k in ["peak","offpeak","daily"])][:3]
        )

        if chart_cols:
            chart_df = res_df[id_cols].copy()
            for c in chart_cols:
                chart_df[c] = numeric_cols[c]
            melted = chart_df.melt(id_vars=id_cols, var_name="Rate Type", value_name="Value").dropna(subset=["Value"])
            if not melted.empty:
                st.bar_chart(melted, x="Rate Type", y="Value", color="Retailer")
            else:
                st.info("No numeric values available to plot for the chosen columns.")

        # Download
        csv = res_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download comparison as CSV", data=csv, file_name="tariff_comparison.csv", mime="text/csv")

else:
    st.info("Upload one or more Excel files and enter a tariff to begin.")
