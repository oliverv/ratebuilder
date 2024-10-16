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

#@st.cache_data
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
    file_summary[filename]["valid"] += 1  # Track number of valid entries

def summarize_and_highlight_cheapest(prefix_data, num_cheapest=4):
    """Summarizes the data to highlight the lowest rates and counts for each prefix."""
    summary_data = []
    
    for prefix, data in prefix_data.items():
        avg_inter_vendor, cheapest_inter_file = calculate_average_of_cheapest(
            data["inter_vendor_rates"], num_cheapest, exclude_first_cheapest=False
        )
        avg_intra_vendor, cheapest_intra_file = calculate_average_of_cheapest(
            data["intra_vendor_rates"], num_cheapest, exclude_first_cheapest=False
        )
        avg_vendor, cheapest_vendor_file = calculate_average_of_cheapest(
            data["vendor_rates"], num_cheapest, exclude_first_cheapest=False
        )
        
        summary_data.append({
            "Prefix": prefix,
            "Description": data["description"],
            "Cheapest Inter-Vendor Rate": avg_inter_vendor,
            "Cheapest Inter-Vendor File": clean_filename(cheapest_inter_file),
            "Cheapest Intra-Vendor Rate": avg_intra_vendor,
            "Cheapest Intra-Vendor File": clean_filename(cheapest_intra_file),
            "Cheapest Vendor Rate": avg_vendor,
            "Cheapest Vendor File": clean_filename(cheapest_vendor_file),
            "Vendor's currency": data["currency"],
            "Billing scheme": data["billing_scheme"]
        })

    return pd.DataFrame(summary_data)

# --- Streamlit App Interface ---
st.title("CSV Rate Aggregator with Duplicates and Cheapest Rates Highlight")

# Step 1: File Upload
uploaded_files = st.file_uploader("Upload CSV or ZIP files", type=["csv", "zip"], accept_multiple_files=True)

if uploaded_files:
    prefix_data, file_summary = process_csv_data(uploaded_files)

    # Display file summaries before final processing
    st.header("File Summary")
    summary_data = [{"File": file, "Total Rows": data["rows"], "Missing Data": data["missing"], "Valid Rows": data["valid"]}
                    for file, data in file_summary.items()]
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df)

    # Ask user if they want to proceed
    if st.button("Proceed with Final Processing"):
        st.success("Files successfully processed.")
        
        # Summarize and highlight cheapest rates
        summarized_df = summarize_and_highlight_cheapest(prefix_data)
        
        # Highlight the lowest rates
        st.subheader("Cheapest Rates by Prefix")
        st.dataframe(summarized_df.style.highlight_min(subset=["Cheapest Inter-Vendor Rate", "Cheapest Intra-Vendor Rate", "Cheapest Vendor Rate"], color='lightgreen'))
        
        # Display detailed stats per file
        st.subheader("Summary per File")
        st.write(summary_df)

    # Allow download of processed data
    csv_results = summarized_df.to_csv(index=False)
    st.download_button(
        label="Download processed results as CSV",
        data=csv_results,
        file_name='processed_vendor_rates.csv',
        mime='text/csv',
    )
