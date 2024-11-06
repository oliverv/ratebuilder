import streamlit as st
import csv
from collections import defaultdict
import pandas as pd
import zipfile
import requests
import io
from PIL import Image

# --- Functions ---

def calculate_average_rate(rates):
    """Calculates the average of provided rates."""
    rates = [float(rate) for rate in rates if str(rate).strip() and float(rate) >= 0.0]
    if rates:
        return round(sum(rates) / len(rates), 6)
    return 0.0

def calculate_lcr_cost(rates, n):
    """Determines the LCR cost based on the number of vendors and predefined rules."""
    rates = sorted([float(rate) for rate in rates if str(rate).strip() and float(rate) >= 0.0])
    vendor_count = len(rates)

    if vendor_count == 1:
        return rates[0]
    elif vendor_count == 2:
        return rates[1]
    elif vendor_count == 3:
        return rates[2]
    elif vendor_count >= n:
        return rates[n - 1]
    return 0.0

def process_csv_data_with_vendor(uploaded_files, dropbox_url, gdrive_url, base_vendor_name, lcr_n):
    """Processes CSV data with a pre-selected base vendor."""
    prefix_data = defaultdict(lambda: {
        "inter_vendor_rates": [],
        "intra_vendor_rates": [],
        "vendor_rates": [],
        "description": None,
        "currency": None,
        "billing_scheme": None,
        "cheapest_file": {}
    })

    all_files = []
    if uploaded_files:
        all_files.extend([(f, f.name) for f in uploaded_files])
    if dropbox_url:
        all_files.extend([(download_from_dropbox(dropbox_url)[0], "dropbox_file.zip")])
    if gdrive_url:
        all_files.extend([(download_from_google_drive(gdrive_url)[0], "gdrive_file.zip")])

    for file, filename in all_files:
        if isinstance(file, io.BytesIO):
            file_contents = file.getvalue()
        else:
            file_contents = file.read()

        if filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(file_contents), 'r') as z:
                for inner_filename in z.namelist():
                    if inner_filename.endswith('.csv'):
                        with z.open(inner_filename) as f:
                            process_file_with_vendor(f, prefix_data, inner_filename, base_vendor_name)
        elif filename.endswith('.csv'):
            process_file_with_vendor(file, prefix_data, filename, base_vendor_name)

    return prefix_data

def process_file_with_vendor(file, prefix_data, filename, base_vendor_name):
    """Processes a single CSV file, filtering by a base vendor name."""
    try:
        file_text = file.read().decode('utf-8')
    except UnicodeDecodeError:
        file_text = file.read().decode('latin-1')
    reader = csv.DictReader(file_text.splitlines())
    for row in reader:
        if base_vendor_name.lower() in row["Vendor"].lower():
            process_row_with_lcr(prefix_data, row, filename)

def process_row_with_lcr(prefix_data, row, filename):
    """Processes a single row with LCR cost structure."""
    prefix = row["Prefix"]
    data = prefix_data[prefix]

    inter_vendor_rate = row.get("Rate (inter, vendor's currency)", "")
    intra_vendor_rate = row.get("Rate (intra, vendor's currency)", "")
    vendor_rate = row.get("Rate (vendor's currency)", "")

    if inter_vendor_rate:
        data["inter_vendor_rates"].append(inter_vendor_rate)
    if intra_vendor_rate:
        data["intra_vendor_rates"].append(intra_vendor_rate)
    if vendor_rate:
        data["vendor_rates"].append(vendor_rate)

    data["description"] = data.get("description") or row.get("Description")
    data["currency"] = data.get("currency") or row.get("Vendor's currency")
    data["billing_scheme"] = data.get("billing_scheme") or row.get("Billing scheme")

def download_from_dropbox(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return [io.BytesIO(response.content)]
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading from Dropbox: {e}")
        return []

def download_from_google_drive(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return [io.BytesIO(response.content)]
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading from Google Drive: {e}")
        return []

# --- Streamlit App ---

# Logo Display
logo = Image.open("https://api.getkoala.com/web/companies/telecall.com/logo")  # Replace with actual path to the logo
st.image(logo, use_column_width=True)

st.title("Telecall CSV Rate Aggregator with Vendor Pre-selection and Combined LCR & Average Cost Calculation")

# Vendor selection input
base_vendor_name = st.text_input("Base Vendor Name (for filtering):")

uploaded_files = st.file_uploader(
    "Upload CSV or ZIP files (or provide links below)",
    type=["csv", "zip"],
    accept_multiple_files=True
)

gdrive_url = st.text_input("Google Drive URL:")

lcr_n = st.number_input("LCR level (e.g., 4 for LCR4)", min_value=1, value=4)
decimal_places = st.number_input("Decimal Places for Display", min_value=0, value=6)
final_decimal_places = st.number_input("Decimal Places for Final Export", min_value=0, value=6)

if (uploaded_files or dropbox_url or gdrive_url) and base_vendor_name:
    prefix_data = process_csv_data_with_vendor(uploaded_files, gdrive_url, base_vendor_name, lcr_n)

    results = []
    for prefix, data in prefix_data.items():
        # Calculate average rates
        avg_inter_vendor = calculate_average_rate(data["inter_vendor_rates"])
        avg_intra_vendor = calculate_average_rate(data["intra_vendor_rates"])
        avg_vendor = calculate_average_rate(data["vendor_rates"])

        # Calculate LCR-based costs
        lcr_inter_vendor = calculate_lcr_cost(data["inter_vendor_rates"], lcr_n)
        lcr_intra_vendor = calculate_lcr_cost(data["intra_vendor_rates"], lcr_n)
        lcr_vendor = calculate_lcr_cost(data["vendor_rates"], lcr_n)

        # Append results with averages and LCR costs
        results.append([
            prefix,
            data["description"],
            f"{avg_inter_vendor:.{decimal_places}f}",
            f"{avg_intra_vendor:.{decimal_places}f}",
            f"{avg_vendor:.{decimal_places}f}",
            f"{lcr_inter_vendor:.{decimal_places}f}",
            f"{lcr_intra_vendor:.{decimal_places}f}",
            f"{lcr_vendor:.{decimal_places}f}",
            data["currency"],
            data["billing_scheme"]
        ])

    # Create DataFrame for results
    columns = [
        "Prefix", "Description",
        "Average Rate (inter, vendor's currency)",
        "Average Rate (intra, vendor's currency)",
        "Average Rate (vendor's currency)",
        "LCR Cost (inter, vendor's currency)",
        "LCR Cost (intra, vendor's currency)",
        "LCR Cost (vendor's currency)",
        "Vendor's currency",
        "Billing scheme"
    ]
    df = pd.DataFrame(results, columns=columns)

    # Display results in Streamlit
    st.subheader("Combined Average and LCR Cost Summary")
    st.dataframe(df)

    # Prepare final CSV with specified precision for download
    csv_final = df.to_csv(index=False, float_format=f"%.{final_decimal_places}f")
    st.download_button(
        label="Download Combined Average and LCR Cost Summary as CSV",
        data=csv_final,
        file_name='combined_average_lcr_cost_summary.csv',
        mime='text/csv',
    )   
