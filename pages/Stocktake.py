import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

st.set_page_config(layout="wide")  # Always use wide mode

# Barcode image generation
import barcode
from barcode.writer import ImageWriter

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
    div[data-testid="column"] button#empty_unfound_btn {
        background-color: #a569bd !important;
        color: white !important;
        font-weight: bold;
    }
    button#confirm_empty_scanned_btn, button#confirm_empty_unfound_btn {
        background-color: #3498db !important;
        color: white !important;
        font-weight: bold;
    }
    button#cancel_empty_scanned_btn, button#cancel_empty_unfound_btn {
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
        df["BARCODE"] = df["BARCODE"].apply(
            lambda x: str(int(float(x))) if pd.notnull(x)
            and str(x).replace('.','',1).isdigit()
            and float(x).is_integer() else x
        )
    if "QUANTITY" in df.columns:
        df["QUANTITY"] = df["QUANTITY"].apply(
            lambda x: str(int(float(x))) if pd.notnull(x)
            and str(x).replace('.','',1).isdigit()
            and float(x).is_integer() else x
        )
    df = df.replace("nan", "").replace(pd.NA, "")
    return df

# --- Replace VISIBLE_FIELDS with the exact headers you requested ---
VISIBLE_FIELDS = [
    "BARCODE","LOCATION","LOCATION2","PKEY","PKEY0","FRAMENUM","FRAMENUM0","SXFRAME",
    "QUANTITY","MANUFACT","MODEL","FCOLOUR","SIZE","FRDESC","LOCATION3","STKTAKE",
    "CHANGE","QTYAPPRO","QTY3","SUPBARCODE","ISTOCKCODE","SUPPLIER","SUPPLIER2",
    "FRAMETYPE","FRAMEGROUP","TEMPLE","DEPTH","DIAG","BASECURVE","SUNGRX","FROTHER",
    "FROTHER2","REORDDATE","REORDER","REORDQTY","RRP","EXLISTPR","LISTPRICE","EXCOSTPR",
    "COSTPRICE","EXPREVCOST","PREVCOST","EXAVGCOST","AVGCOST","DPRECOST","DPREEXCOST",
    "WSALEET","WSALEIT","APPORDER","LASTSALE2","LASTSALE","FIRSTPUR","LASTPUR","RETURNBY",
    "DQTY","REFRESH","LASTINV","DISPC","TAXPC","FRSTATUS","FRSTATUS2","QTYONORDER",
    "QTYONAPPRO","PHOTOEXT","PHOTONAME","LIFESTYLE","LIFECYCLE","RELEASE","AVAILFROM",
    "AVAILTILL","FRANGE","SPH1","SPH2","CYL1","CYL2","MINPD","BASEC","SRVCHARGE",
    "EXLISTSRV","LISTSRV","EXRRPSRV","RRPSRV","MODKEY","ORDERAGAIN","PROSUPPLY",
    "PSSUPFIT","PSCREATED","PSUPDATEAT","USER","MODIFIED","DELFLAG","XFER","PROVISION",
    "PVINACTIVE","LOGSTR","FGID","SUPSTATUS","LLABORDER","LDOWNLOAD","UUID","NOTE","PHOTO"
]

# --- Shared scanned barcodes CSV ---
SCANNED_FILE = os.path.join(os.path.dirname(__file__), "..", "scanned_barcodes.csv")
UNFOUND_FILE = os.path.join(os.path.dirname(__file__), "..", "unfound_barcodes.csv")

def load_scanned_barcodes():
    if os.path.exists(SCANNED_FILE):
        try:
            return pd.read_csv(SCANNED_FILE)["barcode"].astype(str).tolist()
        except Exception:
            return []
    return []

def save_scanned_barcodes(barcodes):
    pd.DataFrame({"barcode": barcodes}).to_csv(SCANNED_FILE, index=False)

def load_unfound_barcodes():
    if os.path.exists(UNFOUND_FILE):
        return pd.read_csv(UNFOUND_FILE, dtype={"barcode": str})
    return pd.DataFrame(columns=["barcode", "timestamp"])

def save_unfound_barcodes(df):
    df.to_csv(UNFOUND_FILE, index=False)

def empty_unfound_barcodes():
    pd.DataFrame(columns=["barcode", "timestamp"]).to_csv(UNFOUND_FILE, index=False)

# --- Load inventory ---
INVENTORY_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Inventory")
inventory_files = []
if os.path.exists(INVENTORY_FOLDER):
    inventory_files = [f for f in os.listdir(INVENTORY_FOLDER) if f.lower().endswith(('.xlsx', '.csv'))]

if not inventory_files:
    st.error("No inventory files found in the Inventory/ folder.")
    st.stop()

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

# Optional: Normalize common column name variants from inventory to expected names
COLUMN_NAME_MAP = {
    "F GROUP": "FRAMEGROUP",
    "COST PRICE": "COSTPRICE",
    # Add other mappings if your inventory has alternate names
}
df = df.rename(columns={k: v for k, v in COLUMN_NAME_MAP.items() if k in df.columns})

# Clean the DataFrame barcodes as strings
df[barcode_col] = df[barcode_col].map(clean_barcode).astype(str)

st.title("Stocktake - Scan Barcodes")

# --- Shared scanned barcodes list ---
scanned_barcodes = load_scanned_barcodes()

# --- Track the last unfound barcode and last successful barcode in session state ---
if "last_unfound_barcode" not in st.session_state:
    st.session_state["last_unfound_barcode"] = None
if "last_success_barcode" not in st.session_state:
    st.session_state["last_success_barcode"] = None
if "confirm_clear_scanned_barcodes" not in st.session_state:
    st.session_state["confirm_clear_scanned_barcodes"] = False
if "confirm_clear_unfound_barcodes" not in st.session_state:
    st.session_state["confirm_clear_unfound_barcodes"] = False

# IDENTIFYING FIELDS used to detect same product (adjust as needed)
IDENTIFYING_FIELDS = ["FRAMENUM", "MODEL", "MANUFACT", "SIZE", "FCOLOUR", "FRAMETYPE"]

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
            # Found in inventory but not scanned yet
            product_row = df[df[barcode_col] == cleaned].iloc[0]

            def make_signature(row):
                return tuple(str(row.get(f, "")).strip() for f in IDENTIFYING_FIELDS)

            new_sig = make_signature(product_row)

            # Build signatures for already scanned products
            scanned_sigs = {}
            for b in scanned_barcodes:
                if b in df[barcode_col].values:
                    r = df[df[barcode_col] == b].iloc[0]
                    scanned_sigs[b] = make_signature(r)

            # Check if any scanned signature matches the new one
            duplicate_found = False
            for b, sig in scanned_sigs.items():
                if sig == new_sig:
                    duplicate_found = True
                    matching_barcode = b
                    break

            if duplicate_found:
                st.warning("Product with the same framecode/details has already been scanned.")
                col_yes, col_no = st.columns([1, 1])
                with col_yes:
                    if st.button("Add anyway (increment quantity)", key=f"force_add_{cleaned}"):
                        scanned_barcodes.append(str(cleaned))
                        save_scanned_barcodes(scanned_barcodes)
                        st.success(f"Added barcode: {cleaned} — quantity incremented for matching product.")
                        st.session_state["last_unfound_barcode"] = None
                        st.session_state["last_success_barcode"] = cleaned
                        if hasattr(st, "rerun"):
                            st.rerun()
                        elif hasattr(st, "experimental_rerun"):
                            st.experimental_rerun()
                with col_no:
                    if st.button("Cancel", key=f"cancel_add_{cleaned}"):
                        st.info("Add cancelled.")
                        st.session_state["last_unfound_barcode"] = None
            else:
                # Normal add
                scanned_barcodes.append(str(cleaned))
                save_scanned_barcodes(scanned_barcodes)
                st.success(f"Added barcode: {cleaned}")
                st.session_state["last_unfound_barcode"] = None
                st.session_state["last_success_barcode"] = cleaned
                if hasattr(st, "rerun"):
                    st.rerun()
                elif hasattr(st, "experimental_rerun"):
                    st.experimental_rerun()
        else:
            st.error("Barcode not found in inventory.")
            st.session_state["last_unfound_barcode"] = cleaned

# --- Show details for last successful barcode scanned (persists after rerun, compact layout) ---
if st.session_state.get("last_success_barcode"):
    last_barcode = st.session_state["last_success_barcode"]
    if last_barcode in df[barcode_col].values:
        product_row = df[df[barcode_col] == last_barcode].iloc[0]
        framecode = product_row.get("FRAMENUM", "N/A")
        model = product_row.get("MODEL", "N/A")
        manufact = product_row.get("MANUFACT", "N/A")
        colour = product_row.get("FCOLOUR", "N/A")
        frametype = product_row.get("FRAMETYPE", "N/A")
        size = product_row.get("SIZE", "N/A")
        rrp = product_row.get("RRP", "N/A")
        img_col, details_col = st.columns([1, 3])
        with img_col:
            try:
                CODE128 = barcode.get_barcode_class('code128')
                barcode_img = CODE128(str(last_barcode), writer=ImageWriter())
                buffer = io.BytesIO()
                barcode_img.write(buffer)
                buffer.seek(0)
                st.image(buffer, caption="", width=120)
            except Exception:
                st.warning("Could not generate barcode image.")
        with details_col:
            st.markdown(
                f"<div style='font-size:15px; line-height:1.5em; margin-top:16px;'>"
                f"<b>Barcode:</b> {last_barcode} &nbsp; | &nbsp; "
                f"<b>Framecode:</b> {framecode} &nbsp; | &nbsp; "
                f"<b>Model:</b> {model} &nbsp; | &nbsp; "
                f"<b>Manufacturer:</b> {manufact} &nbsp; | &nbsp; "
                f"<b>Colour:</b> {colour} &nbsp; | &nbsp; "
                f"<b>Frametype:</b> {frametype} &nbsp; | &nbsp; "
                f"<b>Size:</b> {size} &nbsp; | &nbsp; "
                f"<b>RRP:</b> {rrp}"
                f"</div>", unsafe_allow_html=True
            )
    else:
        st.session_state["last_success_barcode"] = None

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

# --- Empty Table Functionality with Confirmation Prompt for scanned barcodes ---
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
def format_inventory_table(input_df):
    df_disp = input_df.copy()
    # Ensure all columns exist, and cast to string
    for col in df_disp.columns:
        df_disp[col] = df_disp[col].astype(str)
    if "BARCODE" in df_disp.columns:
        df_disp["BARCODE"] = df_disp["BARCODE"].map(clean_barcode)
    if "RRP" in df_disp.columns:
        df_disp["RRP"] = df_disp["RRP"].apply(format_rrp).astype(str)
    # Reindex to the exact VISIBLE_FIELDS order, creating missing columns with empty strings
    df_disp = df_disp.reindex(columns=VISIBLE_FIELDS).fillna("").replace("nan", "").replace(pd.NA, "")
    return df_disp

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

# --- Table of scanned products as ONE table, most recent scan on top ---
ordered_barcodes = list(reversed(scanned_barcodes))
present_barcodes = [b for b in ordered_barcodes if b in df[barcode_col].values]
scanned_df = df[df[barcode_col].isin(present_barcodes)].copy()

if not scanned_df.empty:
    # Preserve the scanning order by assigning an order index
    scanned_df = scanned_df.assign(
        __order=scanned_df[barcode_col].apply(lambda x: present_barcodes.index(x))
    ).sort_values('__order').drop(columns='__order')

    # Compute scanned-counts per identifying signature (we use FRAMENUM as main key; fallback to BARCODE)
    def get_key_for_row(row):
        val = str(row.get("FRAMENUM", "")).strip()
        return val if val != "" else str(row.get(barcode_col, "")).strip()

    # Count how many scanned barcodes map to each key
    key_counts = {}
    for b in scanned_barcodes:
        if b in df[barcode_col].values:
            row = df[df[barcode_col] == b].iloc[0]
            k = get_key_for_row(row)
            key_counts[k] = key_counts.get(k, 0) + 1

    # Prepare display dataframe and inject computed QUANTITY
    display_df = clean_for_display(scanned_df)
    display_df = display_df.reindex(columns=VISIBLE_FIELDS).fillna("").replace("nan", "").replace(pd.NA, "")

    if "QUANTITY" in display_df.columns:
        computed_qtys = []
        for _, r in scanned_df.iterrows():
            k = get_key_for_row(r)
            computed_qtys.append(str(key_counts.get(k, r.get("QUANTITY", ""))))
        display_df["QUANTITY"] = computed_qtys

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

# --- Unfound Barcodes Table at the Bottom w/ empty functionality ---
st.markdown("### Unfound Barcodes Table")

# Button to empty unfound barcodes table with confirmation
unfound_clear_col, unfound_prompt_col = st.columns([1, 6], gap="small")
with unfound_clear_col:
    if st.button("🗑️ Empty Unfound Table", key="empty_unfound_btn"):
        st.session_state["confirm_clear_unfound_barcodes"] = True

if st.session_state.get("confirm_clear_unfound_barcodes", False):
    with unfound_prompt_col:
        st.warning("Are you sure you want to **empty the unfound barcodes table**? This cannot be undone.")
        yes_unfound_col, no_unfound_col = st.columns([1, 1])
        with yes_unfound_col:
            if st.button("Yes, Empty Unfound Table", key="confirm_empty_unfound_btn"):
                empty_unfound_barcodes()
                st.session_state["confirm_clear_unfound_barcodes"] = False
                st.success("Unfound barcodes table emptied.")
                if hasattr(st, "rerun"):
                    st.rerun()
                elif hasattr(st, "experimental_rerun"):
                    st.experimental_rerun()
        with no_unfound_col:
            if st.button("Cancel", key="cancel_empty_unfound_btn"):
                st.session_state["confirm_clear_unfound_barcodes"] = False

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
