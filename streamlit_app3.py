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
file_summary = defaultdict(int)

@st.cache_data
def process_csv_data(uploaded_files):
    """Processes CSV data from uploaded files."""
    prefix_data = defaultdict(create_prefix_dict)
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.zip'):
            with zipfile.ZipFile(uploaded_file, 'r') as z:
                for inner_filename in z.namelist():
                    if inner_filename.endswith('.csv'):
                        with z.open(inner_filename) as file:
                            read_and_process_csv(file, prefix_data, inner_filename, file_summary)
        else:
            read_and_process_csv(uploaded_file, prefix_data, uploaded_file.name, file_summary)
    return prefix_data, file_summary

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
    file_summary[filename] += 1  # Track number of entries per file

# --- Streamlit App Interface ---
st.title("CSV Rate Aggregator")
uploaded_files = st.file_uploader("Upload CSV or ZIP files", type=["csv", "zip"], accept_multiple_files=True)

if uploaded_files:
    prefix_data, file_summary = process_csv_data(uploaded_files)
    st.success("Files successfully uploaded and processed.")
    vendor_options = list(set(clean_filename(file) for file in file_summary.keys()))
    
    st.header("Vendor Selection")
    vendor_selection_type = st.radio("Select Vendor Selection Type", ("Include", "Exclude"), key="vendor_selection_type")

    if vendor_selection_type == "Include":
        included_vendors = st.multiselect("Select Vendors to Include", options=vendor_options, key="vendors_include")
        excluded_vendors = None
    else:
        excluded_vendors = st.multiselect("Select Vendors to Exclude", options=vendor_options, key="vendors_exclude")
        included_vendors = None

    # Step 2: Set Parameters
    st.header("Set Parameters")
    num_cheapest = st.number_input("Number of Cheapest Vendors to Average", min_value=1, value=4)
    exclude_first_cheapest = st.checkbox("Exclude First Cheapest Vendor", value=True)
    decimal_places = st.number_input("Decimal Places for Rates", min_value=0, value=6)

    # Step 3: Process Data
    results = []
    for prefix, data in prefix_data.items():
        avg_inter_vendor, cheapest_inter_file = calculate_average_of_cheapest(
            data["inter_vendor_rates"], num_cheapest, exclude_first_cheapest, included_vendors, excluded_vendors
        )
        avg_intra_vendor, cheapest_intra_file = calculate_average_of_cheapest(
            data["intra_vendor_rates"], num_cheapest, exclude_first_cheapest, included_vendors, excluded_vendors
        )
        avg_vendor, cheapest_vendor_file = calculate_average_of_cheapest(
            data["vendor_rates"], num_cheapest, exclude_first_cheapest, included_vendors, excluded_vendors
        )

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
            cheapest_inter_file,
            cheapest_intra_file,
            cheapest_vendor_file
        ])

    # Create DataFrame and display results
    columns = [
        "Prefix", "Description",
        "Average Rate (inter, vendor's currency)",
        "Average Rate (intra, vendor's currency)",
        "Average Rate (vendor's currency)",
        "Vendor's currency", "Billing scheme",
        "Cheapest Inter-Vendor File",
        "Cheapest Intra-Vendor File",
        "Cheapest Vendor File"
    ]
    
    df = pd.DataFrame(results, columns=columns)
    
    st.subheader("Processed Results")
    st.dataframe(df)

    # Step 4: Download Results
    csv_results = df.to_csv(index=False)
    st.download_button(
        label="Download processed results as CSV",
        data=csv_results,
        file_name='processed_vendor_rates.csv',
        mime='text/csv',
    )
