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
    rates = [float(rate) for rate in rates if str(rate).strip() and float(rate) >= 0.0]
    if rates:
        return round(sum(rates) / len(rates), 6)
    return 0.0

def calculate_lcr_cost(rates, n):
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

def process_csv_data(uploaded_files, dropbox_url, gdrive_url):
    """Processes CSV data to extract vendor names and prepare data structure."""
    prefix_data = defaultdict(lambda: {
        "inter_vendor_rates": [],
        "intra_vendor_rates": [],
        "vendor_rates": [],
        "description": None,
        "currency": None,
        "billing_scheme": None,
        "cheapest_file": {}
    })
    vendor_names = set()

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
                            vendor_names.update(process_file(f, prefix_data))
        elif filename.endswith('.csv'):
            vendor_names.update(process_file(file, prefix_data))

    return prefix_data, sorted(vendor_names)

def process_file(file, prefix_data):
    """Processes a single CSV file and returns a set of unique vendor names."""
    vendor_names = set()
    try:
        file_text = file.read().decode('utf-8')
    except UnicodeDecodeError:
        file_text = file.read().decode('latin-1')
    reader = csv.DictReader(file_text.splitlines())
    for row in reader:
        vendor_name = row.get("Vendor", "").strip()
        if vendor_name:
            vendor_names.add(vendor_name)
        prefix = row["Prefix"]
        data = prefix_data[prefix]

        # Add rates to respective lists if they exist
        inter_vendor_rate = row.get("Rate (inter, vendor's currency)", "")
        intra_vendor_rate = row.get("Rate (intra, vendor's currency)", "")
        vendor_rate = row.get("Rate (vendor's currency)", "")
        if inter_vendor_rate:
            data["inter_vendor_rates"].append(inter_vendor_rate)
        if intra_vendor_rate:
            data["intra_vendor_rates"].append(intra_vendor_rate)
        if vendor_rate:
            data["vendor_rates"].append(vendor_rate)

        # Process metadata fields
        data["description"] = data.get("description") or row.get("Description")
        data["currency"] = data.get("currency") or row.get("Vendor's currency")
        data["billing_scheme"] = data.get("billing_scheme") or row.get("Billing scheme")
    return vendor_names

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
# Logo Display
logo = Image.open("logo.jpg")  # Replace with the actual path to your logo
st.image(logo, width=200)

st.title("Telecall CSV Rate Aggregator with Dynamic Vendor Selection and LCR Cost Calculation")

uploaded_files = st.file_uploader(
    "Upload CSV or ZIP files (or provide links below)",
    type=["csv", "zip"],
    accept_multiple_files=True
)

dropbox_url = st.text_input("Dropbox Shared Link:")
gdrive_url = st.text_input("Google Drive URL:")

lcr_n = st.number_input("LCR level (e.g., 4 for LCR4)", min_value=1, value=4)
decimal_places = st.number_input("Decimal Places for Display", min_value=0, value=6)
final_decimal_places = st.number_input("Decimal Places for Final Export", min_value=0, value=6)

# Process files and get vendor list after upload
if uploaded_files or dropbox_url or gdrive_url:
    prefix_data, vendor_names = process_csv_data(uploaded_files, dropbox_url, gdrive_url)
    selected_vendor = st.selectbox("Select Base Vendor Name (for filtering):", vendor_names)

    # Button to execute processing after selecting the vendor
    if st.button("Execute"):
        results = []
        for prefix, data in prefix_data.items():
            # Filter by selected vendor and calculate averages and LCR costs
            if selected_vendor:
                avg_inter_vendor = calculate_average_rate(data["inter_vendor_rates"])
                avg_intra_vendor = calculate_average_rate(data["intra_vendor_rates"])
                avg_vendor = calculate_average_rate(data["vendor_rates"])

                lcr_inter_vendor = calculate_lcr_cost(data["inter_vendor_rates"], lcr_n)
                lcr_intra_vendor = calculate_lcr_cost(data["intra_vendor_rates"], lcr_n)
                lcr_vendor = calculate_lcr_cost(data["vendor_rates"], lcr_n)

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
        
