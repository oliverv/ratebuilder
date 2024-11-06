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

def process_csv_data(uploaded_files, gdrive_url, rate_threshold=1.0):
    """Processes CSV data to extract vendor names, prepare data structure, and check for high rates."""
    prefix_data = defaultdict(lambda: {
        "inter_vendor_rates": [],
        "intra_vendor_rates": [],
        "vendor_rates": [],
        "description": None,
        "currency": None,
        "billing_scheme": None
    })
    vendor_names = set()
    high_rate_prefixes = []  # Store prefixes with any rate above the threshold
    file_summaries = []  # Store total prefix count and high-rate count per file

    all_files = []
    if uploaded_files:
        all_files.extend([(f, f.name) for f in uploaded_files])
    if gdrive_url:
        all_files.extend([(download_from_google_drive(gdrive_url)[0], "gdrive_file.zip")])

    for file, filename in all_files:
        prefix_count = set()  # Track unique prefixes per file
        high_rate_count = 0  # Track high-rate count per file

        if isinstance(file, io.BytesIO):
            file_contents = file.getvalue()
        else:
            file_contents = file.read()

        if filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(file_contents), 'r') as z:
                for inner_filename in z.namelist():
                    if inner_filename.endswith('.csv'):
                        with z.open(inner_filename) as f:
                            vendor_names.update(process_file(f, prefix_data, high_rate_prefixes, rate_threshold, filename, prefix_count, high_rate_count))
        elif filename.endswith('.csv'):
            vendor_names.update(process_file(file, prefix_data, high_rate_prefixes, rate_threshold, filename, prefix_count, high_rate_count))

        file_summaries.append({
            "filename": filename,
            "total_prefix_count": len(prefix_count),
            "high_rate_count": high_rate_count
        })

    return prefix_data, sorted(vendor_names), high_rate_prefixes, file_summaries

def process_file(file, prefix_data, high_rate_prefixes, rate_threshold, filename, prefix_count, high_rate_count):
    """Processes a single CSV file, adds high-rate prefixes to a separate list, and returns unique vendor names."""
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
        prefix_count.add(prefix)  # Track unique prefixes

        data = prefix_data[prefix]

        # Check each rate type and log if it exceeds the threshold
        high_rate_found = False
        for rate_key in ["Rate (inter, vendor's currency)", "Rate (intra, vendor's currency)", "Rate (vendor's currency)"]:
            rate_value = row.get(rate_key, "").strip()
            if rate_value:
                try:
                    rate_value_float = float(rate_value)
                    if rate_value_float > rate_threshold:
                        st.write(f"High rate detected in file {filename}: Prefix {prefix}, Rate {rate_value} in column {rate_key}")
                        high_rate_found = True
                except ValueError:
                    st.write(f"Warning: Non-numeric rate found in file {filename}: Prefix {prefix}, Rate {rate_value} in column {rate_key}")

        if high_rate_found:
            high_rate_prefixes.append((prefix, row, filename))  # Include filename with high-rate prefix
            high_rate_count += 1
            continue  # Skip adding this prefix to main prefix_data for LCR calculation

        # Add rates and file names to respective lists if they exist
        inter_vendor_rate = row.get("Rate (inter, vendor's currency)", "")
        intra_vendor_rate = row.get("Rate (intra, vendor's currency)", "")
        vendor_rate = row.get("Rate (vendor's currency)", "")
        if inter_vendor_rate:
            data["inter_vendor_rates"].append((inter_vendor_rate, filename))
        if intra_vendor_rate:
            data["intra_vendor_rates"].append((intra_vendor_rate, filename))
        if vendor_rate:
            data["vendor_rates"].append((vendor_rate, filename))

        # Process metadata fields
        data["description"] = data.get("description") or row.get("Description")
        data["currency"] = data.get("currency") or row.get("Vendor's currency")
        data["billing_scheme"] = data.get("billing_scheme") or row.get("Billing scheme")
    return vendor_names
    
def process_file_old (file, prefix_data, high_rate_prefixes, rate_threshold, filename, prefix_count, high_rate_count):
    """Processes a single CSV file, adds high-rate prefixes to a separate list, and returns unique vendor names."""
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
        prefix_count.add(prefix)  # Track unique prefixes

        data = prefix_data[prefix]

        # Check each rate type and add prefix to high_rate_prefixes if any rate is above the threshold
        high_rate_found = False
        for rate_key in ["Rate (inter, vendor's currency)", "Rate (intra, vendor's currency)", "Rate (vendor's currency)"]:
            rate_value = row.get(rate_key, "")
            if rate_value and float(rate_value) > rate_threshold:
                high_rate_found = True
        if high_rate_found:
            high_rate_prefixes.append((prefix, row, filename))  # Include filename with high-rate prefix
            high_rate_count += 1
            continue  # Skip adding this prefix to main prefix_data for LCR calculation

        # Add rates and file names to respective lists if they exist
        inter_vendor_rate = row.get("Rate (inter, vendor's currency)", "")
        intra_vendor_rate = row.get("Rate (intra, vendor's currency)", "")
        vendor_rate = row.get("Rate (vendor's currency)", "")
        if inter_vendor_rate:
            data["inter_vendor_rates"].append((inter_vendor_rate, filename))
        if intra_vendor_rate:
            data["intra_vendor_rates"].append((intra_vendor_rate, filename))
        if vendor_rate:
            data["vendor_rates"].append((vendor_rate, filename))

        # Process metadata fields
        data["description"] = data.get("description") or row.get("Description")
        data["currency"] = data.get("currency") or row.get("Vendor's currency")
        data["billing_scheme"] = data.get("billing_scheme") or row.get("Billing scheme")
    return vendor_names

def download_from_google_drive(url):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        file_data = io.BytesIO()
        for chunk in response.iter_content(chunk_size=1048576):  # 1 MB chunks
            file_data.write(chunk)
        file_data.seek(0)
        return [file_data]
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading from Google Drive: {e}")
        return []

# --- Streamlit App ---

# Display Logo and Title
logo = Image.open("logo.png")  # Ensure logo.png is in the working directory
st.image(logo, width=200)
st.title("Telecall - CSV Rate Aggregator Rev10")

uploaded_files = st.file_uploader(
    "Upload CSV or ZIP files (no Dropbox support)",
    type=["csv", "zip"],
    accept_multiple_files=True
)

gdrive_url = st.text_input("Google Drive URL:")

lcr_n = st.number_input("LCR Level (e.g., 4 for LCR4)", min_value=1, value=4)
decimal_places = st.number_input("Decimal Places for Display", min_value=0, value=6)
final_decimal_places = st.number_input("Decimal Places for Final Export", min_value=0, value=6)
rate_threshold = st.number_input("Rate Threshold for High Rate Check", min_value=0.01, value=1.0)

# Process files and get vendor list after upload
if uploaded_files or gdrive_url:
    prefix_data, vendor_names, high_rate_prefixes, file_summaries = process_csv_data(uploaded_files, gdrive_url, rate_threshold)
    
    # Display pre-execution summary
    st.subheader("Pre-Execution Summary")
    for summary in file_summaries:
        st.write(f"File: {summary['filename']}")
        st.write(f" - Total Prefix Count: {summary['total_prefix_count']}")
        st.write(f" - Rates Above ${rate_threshold}: {summary['high_rate_count']}")

    selected_vendor = st.selectbox("Select Base Vendor Name (for filtering):", vendor_names)

    # Button to execute processing after selecting the vendor
    if st.button("Execute"):
        results = []
        for prefix, data in prefix_data.items():
            if selected_vendor:
                avg_inter_vendor = calculate_average_rate([rate for rate, _ in data["inter_vendor_rates"]])
                avg_intra_vendor = calculate_average_rate([rate for rate, _ in data["intra_vendor_rates"]])
                avg_vendor = calculate_average_rate([rate for rate, _ in data["vendor_rates"]])

                lcr_inter_vendor = calculate_lcr_cost([rate for rate, _ in data["inter_vendor_rates"]], lcr_n)
                lcr_intra_vendor = calculate_lcr_cost([rate for rate, _ in data["intra_vendor_rates"]], lcr_n)
                lcr_vendor = calculate_lcr_cost([rate for rate, _ in data["vendor_rates"]], lcr_n)

                # Capture file names for each rate category from LCR calculations
                inter_vendor_file = data["inter_vendor_rates"][lcr_n - 1][1] if len(data["inter_vendor_rates"]) >= lcr_n else ""
                intra_vendor_file = data["intra_vendor_rates"][lcr_n - 1][1] if len(data["intra_vendor_rates"]) >= lcr_n else ""
                vendor_file = data["vendor_rates"][lcr_n - 1][1] if len(data["vendor_rates"]) >= lcr_n else ""

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
                    data["billing_scheme"],
                    inter_vendor_file,  # Source file for inter-vendor rate
                    intra_vendor_file,  # Source file for intra-vendor rate
                    vendor_file         # Source file for vendor rate
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
            "Billing scheme",
            "Inter Vendor Source File",
            "Intra Vendor Source File",
            "Vendor Source File"
        ]
        df_main = pd.DataFrame(results, columns=columns)

        # Create DataFrame for high-rate prefixes with placeholders where needed
        high_rate_columns = columns
        df_high_rates = pd.DataFrame(
            [(prefix, row.get("Description", ""), 
              row.get("Rate (inter, vendor's currency)", ""),
              row.get("Rate (intra, vendor's currency)", ""),
              row.get("Rate (vendor's currency)", ""),
              "", "", "",  # Placeholder for LCR costs if not computed for high-rate prefixes
              row.get("Vendor's currency", ""),
              row.get("Billing scheme", ""),
              source_file, source_file, source_file)  # Source file from high-rate data
             for prefix, row, source_file in high_rate_prefixes],
            columns=high_rate_columns
        )

        # Display and download main LCR results
        st.subheader("Combined Average and LCR Cost Summary (Rates <= Threshold)")
        st.dataframe(df_main)
        csv_main = df_main.to_csv(index=False, float_format=f"%.{final_decimal_places}f")
        st.download_button(
            label="Download Main LCR Results as CSV",
            data=csv_main,
            file_name='main_lcr_results.csv',
            mime='text/csv',
        )

        # Display and download high-rate prefixes
        st.subheader("Prefixes with Rates Above Threshold")
        st.dataframe(df_high_rates)
        csv_high_rates = df_high_rates.to_csv(index=False, float_format=f"%.{final_decimal_places}f")
        st.download_button(
            label="Download High-Rate Prefixes as CSV",
            data=csv_high_rates,
            file_name='high_rate_prefixes.csv',
            mime='text/csv',
        )
