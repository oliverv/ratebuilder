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
    return round(sum(rates) / len(rates), 6) if rates else 0.0

def calculate_lcr_cost(rates, n):
    rates = sorted([float(rate) for rate in rates if str(rate).strip() and float(rate) >= 0.0])
    return rates[n - 1] if len(rates) >= n else (rates[-1] if rates else 0.0)

@st.cache_data
def process_csv_data(uploaded_files, gdrive_url, rate_threshold=1.0):
    prefix_data = defaultdict(lambda: {
        "inter_vendor_rates": [],
        "intra_vendor_rates": [],
        "vendor_rates": [],
        "description": None,
        "currency": None,
        "billing_scheme": None
    })
    vendor_names = set()
    high_rate_prefixes = []
    file_summaries = []

    all_files = [(f, f.name) for f in uploaded_files]
    if gdrive_url:
        all_files.append((download_from_google_drive(gdrive_url)[0], "gdrive_file.zip"))

    for file, filename in all_files:
        file_contents = file.getvalue() if isinstance(file, io.BytesIO) else file.read()
        
        if filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(file_contents), 'r') as z:
                for inner_filename in z.namelist():
                    if inner_filename.endswith('.csv'):
                        with z.open(inner_filename) as f:
                            prefix_count, high_rate_count = set(), [0]
                            vendor_names.update(process_individual_csv(
                                f, prefix_data, high_rate_prefixes, rate_threshold, prefix_count, high_rate_count, inner_filename
                            ))
                            file_summaries.append({
                                "filename": inner_filename.replace('.csv', ''),
                                "total_prefix_count": len(prefix_count),
                                "high_rate_count": high_rate_count[0]
                            })
        elif filename.endswith('.csv'):
            prefix_count, high_rate_count = set(), [0]
            vendor_names.update(process_individual_csv(
                file, prefix_data, high_rate_prefixes, rate_threshold, prefix_count, high_rate_count, filename.replace('.csv', '')
            ))
            file_summaries.append({
                "filename": filename.replace('.csv', ''),
                "total_prefix_count": len(prefix_count),
                "high_rate_count": high_rate_count[0]
            })
    
    return prefix_data, sorted(vendor_names), high_rate_prefixes, file_summaries

def process_individual_csv(file, prefix_data, high_rate_prefixes, rate_threshold, prefix_count, high_rate_count, filename):
    vendor_names = set()
    file_text = file.read().decode('utf-8', errors='ignore')
    reader = csv.DictReader(file_text.splitlines())

    for row in reader:
        vendor_name = row.get("Vendor", "").strip()
        if vendor_name:
            vendor_names.add(vendor_name)

        prefix = row["Prefix"]
        prefix_count.add(prefix)
        data = prefix_data[prefix]
        high_rate_found = False

        for rate_key in ["Rate (inter, vendor's currency)", "Rate (intra, vendor's currency)", "Rate (vendor's currency)"]:
            rate_value = row.get(rate_key, "").strip()
            if rate_value and float(rate_value) > rate_threshold:
                high_rate_found = True

        if high_rate_found:
            high_rate_prefixes.append((prefix, row, filename))
            high_rate_count[0] += 1

        if row.get("Rate (inter, vendor's currency)"):
            data["inter_vendor_rates"].append((row.get("Rate (inter, vendor's currency)"), filename))
        if row.get("Rate (intra, vendor's currency)"):
            data["intra_vendor_rates"].append((row.get("Rate (intra, vendor's currency)"), filename))
        if row.get("Rate (vendor's currency)"):
            data["vendor_rates"].append((row.get("Rate (vendor's currency)"), filename))

        data["description"] = data.get("description") or row.get("Description")
        data["currency"] = data.get("currency") or row.get("Vendor's currency")
        data["billing_scheme"] = data.get("billing_scheme") or row.get("Billing scheme")

    return vendor_names

def download_from_google_drive(url):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        file_data = io.BytesIO(response.content)
        file_data.seek(0)
        return [file_data]
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading from Google Drive: {e}")
        return []

# --- Streamlit App ---

logo = Image.open("logo.png")
st.image(logo, width=200)
st.title("Telecall - CSV Rate Aggregator v13.0")

# Display required headers
st.write("**Please ensure the uploaded files include the following headers in this order for optimal processing:**")
st.write("Prefix, Description, Rate (inter, vendor's currency), Rate (intra, vendor's currency), Rate (vendor's currency), Vendor's currency, Billing scheme")

uploaded_files = st.file_uploader("Upload CSV or ZIP files (no Dropbox support)", type=["csv", "zip"], accept_multiple_files=True)
gdrive_url = st.text_input("Google Drive URL:")
lcr_n = st.number_input("LCR Level (e.g., 4 for LCR4)", min_value=1, value=4)
decimal_places = st.number_input("Decimal Places for Display", min_value=0, value=6)
final_decimal_places = st.number_input("Decimal Places for Final Export", min_value=0, value=6)
rate_threshold = st.number_input("Rate Threshold for High Rate Check", min_value=0.01, value=1.0)

if uploaded_files or gdrive_url:
    prefix_data, vendor_names, high_rate_prefixes, file_summaries = process_csv_data(uploaded_files, gdrive_url, rate_threshold)
    
    st.subheader("Pre-Execution Summary")
    for summary in file_summaries:
        st.write(f"File: {summary['filename']}")
        st.write(f" - Total Prefix Count: {summary['total_prefix_count']}")
        st.write(f" - Rates Above ${rate_threshold}: {summary['high_rate_count']}")
        
    selected_vendor = st.selectbox("Select Base Vendor Name (for filtering):", vendor_names)
    
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

                inter_vendor_file = data["inter_vendor_rates"][lcr_n - 1][1] if len(data["inter_vendor_rates"]) >= lcr_n else ""
                intra_vendor_file = data["intra_vendor_rates"][lcr_n - 1][1] if len(data["intra_vendor_rates"]) >= lcr_n else ""
                vendor_file = data["vendor_rates"][lcr_n - 1][1] if len(data["vendor_rates"]) >= lcr_n else ""

                results.append([
                    prefix, data["description"],
                    f"{avg_inter_vendor:.{decimal_places}f}",
                    f"{avg_intra_vendor:.{decimal_places}f}",
                    f"{avg_vendor:.{decimal_places}f}",
                    f"{lcr_inter_vendor:.{decimal_places}f}",
                    f"{lcr_intra_vendor:.{decimal_places}f}",
                    f"{lcr_vendor:.{decimal_places}f}",
                    data["currency"], data["billing_scheme"],
                    inter_vendor_file, intra_vendor_file, vendor_file
                ])

        columns = [
            "Prefix", "Description",
            "Average Rate (inter, vendor's currency)", "Average Rate (intra, vendor's currency)", "Average Rate (vendor's currency)",
            "LCR Cost (inter, vendor's currency)", "LCR Cost (intra, vendor's currency)", "LCR Cost (vendor's currency)",
            "Vendor's currency", "Billing scheme", "Inter Vendor Source File", "Intra Vendor Source File", "Vendor Source File"
        ]
        df_main = pd.DataFrame(results, columns=columns)

        st.subheader("Final Combined Average and LCR Cost Summary (Rates <= Threshold)")
        st.write(f"Total Prefixes Processed: {len(results)}")
        st.dataframe(df_main)
        csv_main = df_main.to_csv(index=False, float_format=f"%.{final_decimal_places}f")
        st.download_button(label="Download Main LCR Results as CSV", data=csv_main, file_name='main_lcr_results.csv', mime='text/csv')

        df_high_rates = pd.DataFrame(
            [
                (
                    prefix, row.get("Description", ""),
                    row.get("Rate (inter, vendor's currency)", ""),
                    row.get("Rate (intra, vendor's currency)", ""),
                    row.get("Rate (vendor's currency)", ""),
                    "", "", "", row.get("Vendor's currency", ""), row.get("Billing scheme", ""),
                    filename, filename, filename
                )
                for prefix, row, filename in high_rate_prefixes
            ],
            columns=columns
        )

        st.subheader("Prefixes with Rates Above High-rate Threshold")
        st.dataframe(df_high_rates)
        csv_high_rates = df_high_rates.to_csv(index=False, float_format=f"%.{final_decimal_places}f")
        st.download_button(label="Download High-Rate Prefixes as CSV", data=csv_high_rates, file_name='high_rate_prefixes.csv', mime='text/csv')
