import streamlit as st
import csv
from collections import defaultdict
import pandas as pd
import zipfile
import requests
import io

# --- Configuration ---
# st.set_option('server.maxUploadSize', 200)  # Set max upload size to 200MB

# --- Functions ---

def calculate_average_rate(rates):
    rates = [float(rate) for rate in rates if str(rate).strip() and float(rate) >= 0.0]
    if rates:
        return round(sum(rates) / len(rates), 4)
    return 0.0

def calculate_average_of_cheapest(rates, n=4):
    rates = sorted([float(rate) for rate in rates if str(rate).strip() and float(rate) >= 0.0])
    if len(rates) >= n:
        return round(sum(rates[:n]) / n, 4)
    return calculate_average_rate(rates)

def process_csv_data(uploaded_files, dropbox_url, gdrive_url):
    prefix_data = defaultdict(lambda: {
        "inter_vendor_rates": [],
        "intra_vendor_rates": [],
        "vendor_rates": [],
        "description": None,
        "currency": None,
        "billing_scheme": None
    })

    all_files = []
    if uploaded_files:
        all_files.extend([(f, f.name) for f in uploaded_files])  # Store filename with file object
    if dropbox_url:
        all_files.extend([(download_from_dropbox(dropbox_url)[0], "dropbox_file.zip")])  # Assume zip from Dropbox
    if gdrive_url:
        all_files.extend([(download_from_google_drive(gdrive_url)[0], "gdrive_file.zip")])  # Assume zip from GDrive

    for file, filename in all_files:  # Unpack file and filename
        if isinstance(file, io.BytesIO):
            file_contents = file.getvalue()
        else:
            file_contents = file.read()

        if filename.endswith('.zip'): 
            with zipfile.ZipFile(io.BytesIO(file_contents), 'r') as z:
                for filename in z.namelist():
                    if filename.endswith('.csv'):
                        with z.open(filename) as f:
                            process_file(f, prefix_data)
        elif filename.endswith('.csv'):
            process_file(file, prefix_data)

    return prefix_data

def process_file(file, prefix_data):
    try:
        file_text = file.read().decode('utf-8')
    except UnicodeDecodeError:
        file_text = file.read().decode('latin-1')
    reader = csv.DictReader(file_text.splitlines())
    for row in reader:
        process_row(prefix_data, row)

def process_row(prefix_data, row):
    prefix = row["Prefix"]
    data = prefix_data[prefix]
    data["inter_vendor_rates"].append(row.get("Rate (inter, vendor's currency)", ""))
    data["intra_vendor_rates"].append(row.get("Rate (intra, vendor's currency)", ""))
    data["vendor_rates"].append(row.get("Rate (vendor's currency)", ""))
    # Assuming these are consistent per prefix, update only if not already set
    data["description"] = data.get("description") or row.get("Description")
    data["currency"] = data.get("currency") or row.get("Vendor's currency")
    data["billing_scheme"] = data.get("billing_scheme") or row.get("Billing scheme")

def download_from_dropbox(url):
    """Downloads a file from a Dropbox shared link."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return [io.BytesIO(response.content)]
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading from Dropbox: {e}")
        return []

def download_from_google_drive(url):
    """Downloads a file from a Google Drive shared link."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return [io.BytesIO(response.content)]
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading from Google Drive: {e}")
        return []

# --- Streamlit App ---

st.title("CSV Rate Aggregator")

uploaded_files = st.file_uploader(
    "Upload CSV or ZIP files (or provide links below)",
    type=["csv", "zip"],
    accept_multiple_files=True
)

dropbox_url = st.text_input("Dropbox Shared Link:")
gdrive_url = st.text_input("Google Drive URL:")

calculate_cheapest = st.checkbox("Calculate Average Rate for 4 Cheapest Vendors", value=True)

if uploaded_files or dropbox_url or gdrive_url:
    prefix_data = process_csv_data(uploaded_files, dropbox_url, gdrive_url)

    results = []
    for prefix, data in prefix_data.items():
        avg_inter_vendor = calculate_average_rate(data["inter_vendor_rates"])
        avg_intra_vendor = calculate_average_rate(data["intra_vendor_rates"])
        avg_vendor = calculate_average_rate(data["vendor_rates"])
        avg_cheapest_vendor = calculate_average_of_cheapest(data["vendor_rates"]) if calculate_cheapest else None

        row = [
            prefix,
            data["description"],
            avg_inter_vendor,
            avg_intra_vendor,
            avg_vendor,
            data["currency"],
            data["billing_scheme"]
        ]
        
        if calculate_cheapest:
            row.insert(5, avg_cheapest_vendor)

        results.append(row)

    columns = [
        "Prefix", "Description",
        "Average Rate (inter, vendor's currency)",
        "Average Rate (intra, vendor's currency)",
        "Average Rate (vendor's currency)",
        "Vendor's currency",
        "Billing scheme"
    ]

    if calculate_cheapest:
        columns.insert(5, "Average Rate (4 cheapest vendors)")

    df = pd.DataFrame(results, columns=columns)

    st.dataframe(df)

    csv = df.to_csv(index=False)
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='compiled_rates.csv',
        mime='text/csv',
    )
