import streamlit as st
import csv
from collections import defaultdict
import pandas as pd
import zipfile
import io

# --- Helper Functions ---
def clean_filename(filename):
    """Remove 'dial_peer' prefix, '.csv' and '.zip' extensions, and replace underscores with spaces."""
    if filename.startswith("dial_peer"):
        filename = filename.replace("dial_peer", "")
    return filename.replace(".csv", "").replace(".zip", "").replace("_", " ")

def calculate_average_of_cheapest(rates_with_files, n=4, exclude_first_cheapest=True, included_vendors=None, excluded_vendors=None):
    """Calculate the average of the cheapest n rates after applying include/exclude filters."""
    rates_with_files = sorted([(float(rate), file) for rate, file in rates_with_files if str(rate).strip() and float(rate) >= 0.0 and
                              ((included_vendors is None or clean_filename(file) in included_vendors) and
                               (excluded_vendors is None or clean_filename(file) not in excluded_vendors))])
    if exclude_first_cheapest and len(rates_with_files) > 0:
        rates_with_files.pop(0)  # Remove the first cheapest rate
    selected_rates = rates_with_files[:n] if len(rates_with_files) >= n else rates_with_files
    avg_rate = round(sum(rate for rate, _ in selected_rates) / len(selected_rates), 6) if selected_rates else 0.0
    cheapest_file = selected_rates[0][1] if selected_rates else None
    return avg_rate, cheapest_file

def create_prefix_dict():
    """Creates a dictionary to store data for each prefix."""
    return {
        "inter_vendor_rates": [],
        "intra_vendor_rates": [],
        "vendor_rates": [],
        "description": None,
        "currency": None,
        "billing_scheme": None,
        "cheapest_file": {}
    }

# Initialize file_summary outside to ensure it's always available
file_summary = defaultdict(lambda: {"rows": 0, "missing": 0, "valid": 0})

# Cache data using st.cache_resource for resources that are not serializable
@st.cache_resource
def process_csv_data(uploaded_files):
    """Processes CSV data from uploaded files and generates a summary before final processing."""
    prefix_data = defaultdict(create_prefix_dict)
    summary_results = {}

    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.zip'):
            with zipfile.ZipFile(uploaded_file, 'r') as z:
                for inner_filename in z.namelist():
                    if inner_filename.endswith('.csv'):
                        with z.open(inner_filename) as file:
                            count_and_summarize(file, inner_filename, file_summary)
                            read_and_process_csv(file, prefix_data, inner_filename, file_summary)
        else:
            count_and_summarize(uploaded_file, uploaded_file.name, file_summary)
            read_and_process_csv(uploaded_file, prefix_data, uploaded_file.name, file_summary)

    # Return only serializable data
    summary_results["prefix_data"] = prefix_data
    summary_results["file_summary"] = dict(file_summary)
    return summary_results

def count_and_summarize(file, filename, summary):
    """Counts the rows in a file and checks for missing data."""
    try:
        file_text = file.read().decode('utf-8')
    except UnicodeDecodeError:
        file_text = file.read().decode('latin-1')
    reader = csv.DictReader(io.StringIO(file_text))
    row_count = 0
    missing_count = 0
    for row in reader:
        row_count += 1
        if not row.get("Prefix") or not row.get("Rate (vendor's currency)"):
            missing_count += 1
    
    summary[filename]["rows"] = row_count
    summary[filename]["missing"] = missing_count
    summary[filename]["valid"] = row_count - missing_count

def read_and_process_csv(file, prefix_data, filename, file_summary):
    """Reads and processes CSV file data."""
    try:
        file_text = file.read().decode('utf-8')
    except UnicodeDecodeError:
        file_text = file.read().decode('latin-1')
    reader = csv.DictReader(io.StringIO(file_text))
    for row in reader:
        process_row(prefix_data, row, filename, file_summary)

def process_row(prefix_data, row, filename, file_summary):
    """Processes each row of the CSV file."""
    prefix = row["Prefix"]
    data = prefix_data[prefix]
    data["inter_vendor_rates"].append((row.get("Rate (inter, vendor's currency)", 0), filename))
    data["intra_vendor_rates"].append((row.get("Rate (intra, vendor's currency)", 0), filename))
    data["vendor_rates"].append((row.get("Rate (vendor's currency)", 0), filename))
    file_summary[filename]["valid"] += 1  # Track number of valid entries

# --- Streamlit App Interface ---
st.title("CSV Rate Aggregator with File Summary")

uploaded_files = st.file_uploader("Upload CSV or ZIP files", type=["csv", "zip"], accept_multiple_files=True)

if uploaded_files:
    result = process_csv_data(uploaded_files)
    prefix_data = result["prefix_data"]
    file_summary = result["file_summary"]

    # Display file summaries before final processing
    st.header("File Summary")
    summary_data = [{"File": file, "Total Rows": data["rows"], "Missing Data": data["missing"], "Valid Rows": data["valid"]}
                    for file, data in file_summary.items()]
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df)

    # Ask user if they want to proceed
    if st.button("Proceed with Final Processing"):
        st.success("Files successfully processed.")
        # Further data processing can happen here as needed
