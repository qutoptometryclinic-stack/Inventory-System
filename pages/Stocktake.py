import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- Custom CSS for button colors ---
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #27ae60 !important;
        color: white !important;
        font-weight: bold;
        border-radius: 6px;
        border: none;
        height: 38px;
        min-width: 170px;
    }
    div[data-testid="column"] button#empty_scanned_btn {
        background-color: #e74c3c !important;
        color: white !important;
        font-weight: bold;
    }
    button#confirm_empty_scanned_btn {
        background-color: #3498db !important;
        color: white !important;
        font-weight: bold;
    }
    button#cancel_empty_scanned_btn {
        background-color: #f1c40f !important;
        color: black !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

def clean_barcode(val):
    try:
        if pd.isnull(val) or val == "":
            return ""
        s = str(val).strip().replace('\u200b','').replace('\u00A0','')
        f = float(s)
        s = str(int(f))
        return s
    except:
        return str(val).strip()

def force_all_columns_to_string(df):
    for col in df.columns:
        df[col] = df[col].astype(str)
    return df

def clean_nans(df):
    return df.replace([pd.NA, 'nan'], '', regex=True)

def format_rrp(val):
    try:
        f = float(str(val).replace("$", "").strip())
        return f"${f:.2f}"
    except Exception:
        return "$0.00"

def clean_for_display(df):
    df = df.copy()
    if "BARCODE" in df.columns:
        df["BARCODE"] = df["BARCODE"].apply(lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','',1).isdigit() and float(x).is_integer() else x)
    if "QUANTITY" in df.columns:
        df["QUANTITY"] = df["QUANTITY"].apply(lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','',1).isdigit() and float(x).is_integer() else x)
    df = df.replace("nan", "").replace(pd.NA, "").replace(float("nan"), "")
    return df

VISIBLE_FIELDS = [
    "BARCODE", "LOCATION", "FRAMENUM", "MANUFACT", "MODEL", "SIZE",
    "FCOLOUR", "FRAMETYPE", "F GROUP", "SUPPLIER", "QUANTITY", "F TYPE", "TEMPLE",
    "DEPTH", "DIAG", "BASECURVE", "RRP", "EXCOSTPR", "COST PRICE", "TAXPC",
    "FRSTATUS", "AVAILFROM", "NOTE"
]

# --- Shared scanned barcodes CSV ---
SCANNED_FILE = os.path.join(os.path.dirname(__file__), "..", "scanned_barcodes.csv")
UNFOUND_FILE = os.path.join(os.path.dirname(__file__), "..", "unfound_barcodes.csv")

def load_scanned_barcodes():
    if os.path.exists(SCANNED_FILE):
        return pd.read_csv(SCANNED_FILE)["barcode"].astype(str).tolist()
    return []

def save_scanned_barcodes(barcodes):
    pd.DataFrame({"barcode": barcodes}).to_csv(SCANNED_FILE, index=False)

def load_unfound_barcodes():
    if os.path.exists(UNFOUND_FILE):
        return pd.read_csv(UNFOUND_FILE, dtype={"barcode": str})
    return pd.DataFrame(columns=["barcode", "timestamp"])

def save_unfound_barcodes(df):
    df.to_csv(UNFOUND_FILE, index=False)

# --- Load inventory ---
INVENTORY_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Inventory")
inventory_files = [f for f in os.listdir(INVENTORY_FOLDER) if f.lower().endswith(('.xlsx', '.csv'))]
selected_file = inventory_files[0]
if len(inventory_files) > 1:
    selected_file = st.selectbox("Select inventory file to use:", inventory_files)
INVENTORY_FILE = os.path.join(INVENTORY_FOLDER, selected_file)

def load_inventory():
    if os.path.exists(INVENTORY_FILE):
        if INVENTORY_FILE.lower().endswith('.xlsx'):
            df = pd.read_excel(INVENTORY_FILE)
        elif INVENTORY_FILE.lower().endswith('.csv'):
            df = pd.read_csv(INVENTORY_FILE)
        else:
            st.error("Unsupported inventory file type.")
            st.stop()
        df = force_all_columns_to_string(df)
        return df
    else:
        st.error(f"Inventory file '{INVENTORY_FILE}' not found.")
        st.stop()

df = load_inventory()
barcode_col = "BARCODE"
if barcode_col not in df.columns:
    st.error(f"No {barcode_col} column found in your inventory file!")
    st.stop()

# Clean the DataFrame barcodes as strings
df[barcode_col] = df[barcode_col].map(clean_barcode).astype(str)

st.title("Stocktake - Scan Barcodes (Shared)")

# --- Shared scanned barcodes list ---
scanned_barcodes = load_scanned_barcodes()

# --- Track the last unfound barcode in session state ---
if "last_unfound_barcode" not in st.session_state:
    st.session_state["last_unfound_barcode"] = None

# --- Scan input using a form (clears on submit) ---
with st.form("stocktake_scan_form", clear_on_submit=True):
    scanned_barcode = st.text_input("Scan or enter barcode", key="stocktake_scan_input")
    submit = st.form_submit_button("Add Scanned Barcode")
    if submit:
        cleaned = clean_barcode(scanned_barcode)
        if cleaned == "":
            st.warning("Please scan or enter a barcode.")
            st.session_state["last_unfound_barcode"] = None
        elif cleaned in scanned_barcodes:
            st.warning("Barcode already scanned.")
            st.session_state["last_unfound_barcode"] = None
        elif cleaned in df[barcode_col].values:
            scanned_barcodes.append(str(cleaned))
            save_scanned_barcodes(scanned_barcodes)
            st.success(f"Added barcode: {cleaned}")
            st.session_state["last_unfound_barcode"] = None
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()
        else:
            st.error("Barcode not found in inventory.")
            st.session_state["last_unfound_barcode"] = cleaned

# --- Show button to add last unfound barcode (outside the form) ---
if st.session_state.get("last_unfound_barcode", None):
    cleaned = st.session_state["last_unfound_barcode"]
    if st.button("Add to Unfound Barcodes Table", key=f"add_unfound_{cleaned}"):
        unfound_df = load_unfound_barcodes()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row = pd.DataFrame([{"barcode": cleaned, "timestamp": now}])
        unfound_df = pd.concat([unfound_df, new_row], ignore_index=True)
        save_unfound_barcodes(unfound_df)
        st.success(f"Barcode {cleaned} added to unfound table.")
        st.session_state["last_unfound_barcode"] = None
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()

# --- Empty Table Functionality with Confirmation Prompt ---
st.markdown("#### Manage Scanned Products Table")
clear_col, prompt_col = st.columns([1, 6], gap="small")
with clear_col:
    if st.button("🗑️ Empty Table", key="empty_scanned_btn"):
        st.session_state["confirm_clear_scanned_barcodes"] = True

if st.session_state.get("confirm_clear_scanned_barcodes", False):
    with prompt_col:
        st.warning("Are you sure you want to **empty the scanned products table**? This cannot be undone.")
        yes_col, no_col = st.columns([1, 1])
        with yes_col:
            if st.button("Yes, Empty Table", key="confirm_empty_scanned_btn"):
                scanned_barcodes = []
                save_scanned_barcodes(scanned_barcodes)
                st.session_state["confirm_clear_scanned_barcodes"] = False
                st.success("Scanned products table emptied.")
                if hasattr(st, "rerun"):
                    st.rerun()
                elif hasattr(st, "experimental_rerun"):
                    st.experimental_rerun()
        with no_col:
            if st.button("Cancel", key="cancel_empty_scanned_btn"):
                st.session_state["confirm_clear_scanned_barcodes"] = False

# --- Optional: Show missing items ---
if st.checkbox("Show missing products (in inventory but not scanned)"):
    missing_df = df[~df[barcode_col].isin(scanned_barcodes)]
    st.markdown("### Missing Products")
    st.dataframe(format_inventory_table(missing_df), width='stretch')
    if not missing_df.empty:
        st.download_button(
            label="Download Missing Table (CSV)",
            data=format_inventory_table(missing_df).to_csv(index=False).encode('utf-8'),
            file_name="stocktake_missing.csv",
            mime="text/csv"
        )
        excel_buffer_missing = io.BytesIO()
        format_inventory_table(missing_df).to_excel(excel_buffer_missing, index=False)
        excel_buffer_missing.seek(0)
        st.download_button(
            label="Download Missing Table (Excel)",
            data=excel_buffer_missing,
            file_name="stocktake_missing.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- Table formatting helper ---
def format_inventory_table(input_df):
    df_disp = input_df.copy()
    cols = [col for col in VISIBLE_FIELDS if col in df_disp.columns]
    df_disp = df_disp[cols]
    if "BARCODE" in df_disp.columns:
        df_disp["BARCODE"] = df_disp["BARCODE"].map(clean_barcode)
    if "RRP" in df_disp.columns:
        df_disp["RRP"] = df_disp["RRP"].apply(format_rrp).astype(str)
    return clean_nans(df_disp)

# --- Table of scanned products as ONE table, most recent scan on top ---
ordered_barcodes = list(reversed(scanned_barcodes))
present_barcodes = [b for b in ordered_barcodes if b in df[barcode_col].values]
scanned_df = df[df[barcode_col].isin(present_barcodes)]
if not scanned_df.empty:
    scanned_df = scanned_df.assign(
        __order=scanned_df[barcode_col].apply(lambda x: present_barcodes.index(x))
    ).sort_values('__order').drop(columns='__order')
    display_df = clean_for_display(scanned_df)
    display_df = display_df[[col for col in VISIBLE_FIELDS if col in display_df.columns]]
    st.markdown("### Scanned Products Table")
    st.dataframe(display_df, width='stretch', hide_index=True)

    # Remove functionality: select barcode and remove with button
    remove_options = display_df["BARCODE"].tolist()
    if remove_options:
        remove_barcode = st.selectbox("Select a barcode to remove", remove_options)
        if st.button("Remove Selected"):
            scanned_barcodes = [b for b in scanned_barcodes if b != remove_barcode]
            save_scanned_barcodes(scanned_barcodes)
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()

    st.download_button(
        label="Download Scanned Table (CSV)",
        data=format_inventory_table(scanned_df).to_csv(index=False).encode('utf-8'),
        file_name="stocktake_scanned.csv",
        mime="text/csv"
    )
    excel_buffer = io.BytesIO()
    format_inventory_table(scanned_df).to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    st.download_button(
        label="Download Scanned Table (Excel)",
        data=excel_buffer,
        file_name="stocktake_scanned.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No scanned products to display.")

# --- Unfound Barcodes Table at the Bottom ---
st.markdown("### Unfound Barcodes Table")
unfound_df = load_unfound_barcodes()
if not unfound_df.empty:
    unfound_df = unfound_df[::-1]  # Show most recent first
    st.dataframe(unfound_df, width='stretch', hide_index=True)
    st.download_button(
        label="Download Unfound Table (CSV)",
        data=unfound_df.to_csv(index=False).encode('utf-8'),
        file_name="unfound_barcodes.csv",
        mime="text/csv"
    )
else:
    st.info("No unfound barcodes yet.")