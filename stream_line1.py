import streamlit as st
import csv
from collections import defaultdict
import pandas as pd
import zipfile
import requests
import io

# --- Functions ---

def calculate_average_rate(rates):
    rates = [float(rate) for rate in rates if str(rate).strip() and float(rate) >= 0.0]
    if rates:
        return round(sum(rates) / len(rates), 6)  # Default to 6 decimal places
    return 0.0

def calculate_average_of_cheapest(rates, n=4, exclude_first_cheapest=True):
    rates = sorted([float(rate) for rate in rates if str(rate).strip() and float(rate) >= 0.0])
    if exclude_first_cheapest and len(rates) > 0:
        rates = rates[1:]  # Exclude the first cheapest rate
    if len(rates) >= n:
        return round(sum(rates[:n]) / n, 6)  # Default to 6 decimal places
    return calculate_average_rate(rates)

def process_csv_data(uploaded_files, dropbox_url, gdrive_url):
    prefix_data = defaultdict(lambda: {
        "inter_vendor_rates": [],
        "intra_vendor_rates": [],
        "vendor_rates": [],
        "description": None,
        "currency": None,
        "billing_scheme": None,
        "cheapest_file": {"inter_vendor": None, "intra_vendor": None, "vendor": None}
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
                            process_file(f, prefix_data, inner_filename)
        elif filename.endswith('.csv'):
            process_file(file, prefix_data, filename)

    return prefix_data

def process_file(file, prefix_data, filename):
    try:
        file_text = file.read().decode('utf-8')
    except UnicodeDecodeError:
        file_text = file.read().decode('latin-1')
    reader = csv.DictReader(file_text.splitlines())
    for row in reader:
        process_row(prefix_data, row, filename)

def process_row(prefix_data, row, filename):
    prefix = row["Prefix"]
    data = prefix_data[prefix]

    data["inter_vendor_rates"].append(row.get("Rate (inter, vendor's currency)", ""))
    data["intra_vendor_rates"].append(row.get("Rate (intra, vendor's currency)", ""))
    data["vendor_rates"].append(row.get("Rate (vendor's currency)", ""))
    data["description"] = data.get("description") or row.get("Description")
    data["currency"] = data.get("currency") or row.get("Vendor's currency")
    data["billing_scheme"] = data.get("billing_scheme") or row.get("Billing scheme")

    for rate_type in ["inter_vendor", "intra_vendor", "vendor"]:
        rate_key = f"Rate ({rate_type.replace('_', ', ') if '_' in rate_type else rate_type}, vendor's currency)"
        current_rate = float(row.get(rate_key, "inf"))
        if current_rate < float(data["cheapest_file"][rate_type].get("rate", "inf")):
            data["cheapest_file"][rate_type] = {"rate": current_rate, "file": filename}

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

st.title("CSV Rate Aggregator")

uploaded_files = st.file_uploader(
    "Upload CSV or ZIP files (or provide links below)",
    type=["csv", "zip"],
    accept_multiple_files=True
)

dropbox_url = st.text_input("Dropbox Shared Link:")
gdrive_url = st.text_input("Google Drive URL:")

num_cheapest = st.number_input("Number of Cheapest Vendors to Average", min_value=1, value=4)
decimal_places = st.number_input("Decimal Places for Rates", min_value=0, value=6)

if uploaded_files or dropbox_url or gdrive_url:
    prefix_data = process_csv_data(uploaded_files, dropbox_url, gdrive_url)

    results = []
    for prefix, data in prefix_data.items():
        avg_inter_vendor = calculate_average_rate(data["inter_vendor_rates"])
        avg_intra_vendor = calculate_average_rate(data["intra_vendor_rates"])
        avg_vendor = calculate_average_rate(data["vendor_rates"])

        # Format the rates using f-strings:
        avg_inter_vendor = f"{avg_inter_vendor:.{decimal_places}f}"
        avg_intra_vendor = f"{avg_intra_vendor:.{decimal_places}f}"
        avg_vendor = f"{avg_vendor:.{decimal_places}f}"

        results.append([
            prefix,
            data["description"],
            avg_inter_vendor,
            avg_intra_vendor,
            avg_vendor,
            data["currency"],
            data["billing_scheme"],
            data["cheapest_file"]["inter_vendor"]["file"],
            data["cheapest_file"]["intra_vendor"]["file"],
            data["cheapest_file"]["vendor"]["file"]
        ])

    columns = [
        "Prefix", "Description",
        "Average Rate (inter, vendor's currency)",
        "Average Rate (intra, vendor's currency)",
        "Average Rate (vendor's currency)",
        "Vendor's currency",
        "Billing scheme",
        "Cheapest Inter-Vendor File",
        "Cheapest Intra-Vendor File",
        "Cheapest Vendor File"
    ]

    df = pd.DataFrame(results, columns=columns)

    st.subheader("All Vendors' Average Rates")
    st.dataframe(df)

    st.subheader(f"Average Rates of {num_cheapest} Cheapest Vendors (Excluding First Cheapest)")
    st.dataframe(df_cheapest)

    csv_all = df.to_csv(index=False)
    csv_cheapest = df_cheapest.to_csv(index=False)

    st.download_button(
        label="Download all vendors' average rates as CSV",
        data=csv_all,
        file_name='all_vendors_average_rates.csv',
        mime='text/csv',
    )

    st.download_button(
        label=f"Download average rates of {num_cheapest} cheapest vendors excluding 1 as CSV",
        data=csv_cheapest,
        file_name=f'{num_cheapest}_cheapest_vendors_excluding_1_average_rates.csv',
        mime='text/csv',
    )
