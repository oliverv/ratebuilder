import streamlit as st
import csv
from collections import defaultdict
import pandas as pd
import zipfile
import requests
import io
import matplotlib.pyplot as plt
import os

# --- Functions ---

def clean_filename(filename):
    """Remove 'dial_peer' prefix, '.csv' and '.zip' extensions, and replace underscores with spaces."""
    if filename.startswith("dial_peer"):
        filename = filename.replace("dial_peer", "")
    return filename.replace(".csv", "").replace(".zip", "").replace("_", " ")

def calculate_average_rate(rates, included_vendors=None, excluded_vendors=None):
    """Calculates the average rate from a list of rates."""
    rates = [float(rate) for rate, _ in rates if str(rate).strip() and float(rate) >= 0.0 and
             ((included_vendors is None or clean_filename(file) in included_vendors) and
              (excluded_vendors is None or clean_filename(file) not in excluded_vendors))]
    if rates:
        return round(sum(rates) / len(rates), 6)  # Default to 6 decimal places
    return 0.0

def calculate_average_of_cheapest(rates_with_files, n=4, exclude_first_cheapest=True, included_vendors=None, excluded_vendors=None):
    """Calculates the average of the n cheapest rates, optionally excluding the first cheapest.
       Also returns the file name where the cheapest rate is found."""
    rates_with_files = sorted([(float(rate), file) for rate, file in rates_with_files if str(rate).strip() and float(rate) >= 0.0 and
                             ((included_vendors is None or clean_filename(file) in included_vendors) and
                              (excluded_vendors is None or clean_filename(file) not in excluded_vendors))])
    if exclude_first_cheapest and len(rates_with_files) > 0:
        rates_with_files = rates_with_files[1:]  # Exclude the first cheapest rate
    if len(rates_with_files) >= n:
        selected_rates = rates_with_files[:n]
    else:
        selected_rates = rates_with_files

    avg_rate = round(sum(rate for rate, _ in selected_rates) / len(selected_rates), 6) if selected_rates else 0.0
    cheapest_file = selected_rates[0][1] if selected_rates else None  # File with the cheapest rate
    return avg_rate, cheapest_file

@st.cache_data
def process_csv_data(uploaded_files, dropbox_url, gdrive_url):
    """Processes CSV data from uploaded files or provided links."""
    prefix_data = defaultdict(create_prefix_dict)
    file_summary = defaultdict(int)
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

    return prefix_data, file_summary

def create_prefix_dict():
    """Creates the dictionary structure for each prefix."""
    return {
        "inter_vendor_rates": [],
        "intra_vendor_rates": [],
        "vendor_rates": [],
        "description": None,
        "currency": None,
        "billing_scheme": None,
        "cheapest_file": {}
    }

def process_file(file, prefix_data, filename):
    """Processes a single CSV file."""
    try:
        file_text = file.read().decode('utf-8')
    except UnicodeDecodeError:
        file_text = file.read().decode('latin-1')
    reader = csv.DictReader(file_text.splitlines())
    for row in reader:
        process_row(prefix_data, row, filename)

def process_row(prefix_data, row, filename):
    """Processes a single row from a CSV file."""
    prefix = row["Prefix"]
    data = prefix_data[prefix]

    # Convert rates to float directly during processing
    data["inter_vendor_rates"].append((float(row.get("Rate (inter, vendor's currency)", "0.0")), filename))
    data["intra_vendor_rates"].append((float(row.get("Rate (intra, vendor's currency)", "0.0")), filename))
    data["vendor_rates"].append((float(row.get("Rate (vendor's currency)", "0.0")), filename))
    data["description"] = data.get("description") or row.get("Description")
    data["currency"] = data.get("currency") or row.get("Vendor's currency")
    data["billing_scheme"] = data.get("billing_scheme") or row.get("Billing scheme")
    data["vendor_file"] = filename  # Store the filename separately

    for rate_type in ["inter_vendor", "intra_vendor", "vendor"]:
        rate_key = f"Rate ({rate_type.replace('_', ', ') if '_' in rate_type else rate_type}, vendor's currency)"
        current_rate = float(row.get(rate_key, "inf"))

        # Initialize with the first valid numeric rate:
        if rate_type not in data["cheapest_file"]:
            data["cheapest_file"][rate_type] = {"rate": current_rate, "file": filename}
        else:
            # Compare only if the existing cheapest rate is numeric:
            try:
                cheapest_rate = float(data["cheapest_file"][rate_type]["rate"])
            except (TypeError, ValueError):
                cheapest_rate = float("inf")

            if current_rate < cheapest_rate:
                data["cheapest_file"][rate_type] = {"rate": current_rate, "file": filename}

# --- Streamlit App ---

st.title("CSV Rate Aggregator")

# Step 1: File Upload
st.header("Upload CSV or ZIP files (or provide links below)")
uploaded_files = st.file_uploader(
    "Upload CSV or ZIP files",
    type=["csv", "zip"],
    accept_multiple_files=True
)

dropbox_url = st.text_input("Dropbox Shared Link:")
gdrive_url = st.text_input("Google Drive URL:")

# Step 2: Set Parameters
st.header("Set Parameters")
num_cheapest = st.number_input("Number of Cheapest Vendors to Average", min_value=1, value=4)
exclude_first_cheapest = st.checkbox("Exclude First Cheapest Vendor", value=True)
decimal_places = st.number_input("Decimal Places for Rates", min_value=0, value=6)

# Step 3: Vendor Selection
st.header("Vendor Selection")
vendor_selection_type = st.radio("Select Vendor Selection Type", ("Include", "Exclude"))

if vendor_selection_type == "Include":
    included_vendors = st.multiselect("Select Vendors to Include", options=[], help="Include only these vendors in calculations.")
    excluded_vendors = None
elif vendor_selection_type == "Exclude":
    excluded_vendors = st.multiselect("Select Vendors to Exclude", options=[], help="Exclude these vendors from calculations.")
    included_vendors = None

# Step 4: Process Data
if uploaded_files or dropbox_url or gdrive_url:
    prefix_data, file_summary = process_csv_data(uploaded_files, dropbox_url, gdrive_url)
    st.success("Files successfully uploaded and processed.")

    # Update vendor selection options based on processed data
    vendor_options = list(set(clean_filename(file) for file in file_summary.keys()))
    if vendor_selection_type == "Include":
        included_vendors = st.multiselect("Select Vendors to Include", options=vendor_options, help="Include only these vendors in calculations.")
    elif vendor_selection_type == "Exclude":
        excluded_vendors = st.multiselect("Select Vendors to Exclude", options=vendor_options, help="Exclude these vendors from calculations.")

    # Define columns
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

    # Step 4: Calculate and Display Results
    results = []
    cheapest_results = []

    for prefix, data in prefix_data.items():
        avg_inter_vendor, cheapest_inter_file = calculate_average_of_cheapest(
            data["inter_vendor_rates"], num_cheapest, exclude_first_cheapest=exclude_first_cheapest, included_vendors=included_vendors, excluded_vendors=excluded_vendors
        )
        avg_intra_vendor, cheapest_intra_file = calculate_average_of_cheapest(
            data["intra_vendor_rates"], num_cheapest, exclude_first_cheapest=exclude_first_cheapest, included_vendors=included_vendors, excluded_vendors=excluded_vendors
        )
        avg_vendor, cheapest_vendor_file = calculate_average_of_cheapest(
            data["vendor_rates"], num_cheapest, exclude_first_cheapest=exclude_first_cheapest, included_vendors=included_vendors, excluded_vendors=excluded_vendors
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

        # Calculate average cheapest rates
        avg_cheapest_inter_vendor, _ = calculate_average_of_cheapest(
            data["inter_vendor_rates"], num_cheapest, exclude_first_cheapest=exclude_first_cheapest, included_vendors=included_vendors, excluded_vendors=excluded_vendors
        )
        avg_cheapest_intra_vendor, _ = calculate_average_of_cheapest(
            data["intra_vendor_rates"], num_cheapest, exclude_first_cheapest=exclude_first_cheapest, included_vendors=included_vendors, excluded_vendors=excluded_vendors
        )
        avg_cheapest_vendor, _ = calculate_average_of_cheapest(
            data["vendor_rates"], num_cheapest, exclude_first_cheapest=exclude_first_cheapest, included_vendors=included_vendors, excluded_vendors=excluded_vendors
        )

        # Format cheapest rates
        avg_cheapest_inter_vendor = f"{avg_cheapest_inter_vendor:.{decimal_places}f}"
        avg_cheapest_intra_vendor = f"{avg_cheapest_intra_vendor:.{decimal_places}f}"
        avg_cheapest_vendor = f"{avg_cheapest_vendor:.{decimal_places}f}"

        cheapest_results.append([
            prefix,
            data["description"],
            avg_cheapest_inter_vendor,
            avg_cheapest_intra_vendor,
            avg_cheapest_vendor,
            data["currency"],
            data["billing_scheme"],
            cheapest_inter_file,
            cheapest_intra_file,
            cheapest_vendor_file
        ])

    df = pd.DataFrame(results, columns=columns)
    df_cheapest = pd.DataFrame(cheapest_results, columns=columns)

    st.subheader("All Vendors' Average Rates")
    st.dataframe(df)

    st.subheader(f"Average Rates of {num_cheapest} Cheapest Vendors (Excluding First Cheapest)")
    st.dataframe(df_cheapest)

    # Step 5: Generate Graphs
    st.subheader("Graphs")

    # Convert relevant columns to numeric before plotting
    df[["Average Rate (inter, vendor's currency)", "Average Rate (intra, vendor's currency)", "Average Rate (vendor's currency)"]] = df[["Average Rate (inter, vendor's currency)", "Average Rate (intra, vendor's currency)", "Average Rate (vendor's currency)"]].astype(float)

    for rate_type in ["Average Rate (inter, vendor's currency)", "Average Rate (intra, vendor's currency)", "Average Rate (vendor's currency)"]:
        fig, ax = plt.subplots()
        df.plot(x="Prefix", y=rate_type, kind="bar", ax=ax)
        ax.set_title(f"{rate_type} per Prefix")
        ax.set_xlabel("Prefix")
        ax.set_ylabel("Rate")
        st.pyplot(fig)

    # Step 6: Display Statistics
    st.subheader("Statistics")
    for rate_type in ["Average Rate (inter, vendor's currency)", "Average Rate (intra, vendor's currency)", "Average Rate (vendor's currency)"]:
        st.write(f"**Stats for {rate_type}:**")
        st.write(df[rate_type].astype(float).describe())

    # Step 7: Download Results
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

    # Display file summary
    st.subheader("Cheapest Vendor File Summary")
    for file, count in file_summary.items():
        st.write(f"File: {file}, Appearances: {count}")

    # Create a bar graph for the file summary
    st.subheader("Cheapest Vendor File Summary Graph")
    fig, ax = plt.subplots()
    ax.bar(file_summary.keys(), file_summary.values())
    ax.set_xlabel("File Name")
    ax.set_ylabel("Number of Appearances")
    ax.set_title("Cheapest Vendor File Summary")
    st.pyplot(fig)

# Step 8: Upload Files for Storage
st.header("Upload Files for Storage")
uploaded_file = st.file_uploader("Upload a file")
if uploaded_file is not None:
    # Create a directory if it doesn't exist
    directory = "uploaded_files"
    os.makedirs(directory, exist_ok=True)

    # Save the file
    file_path = os.path.join(directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    st.success(f"File '{uploaded_file.name}' saved successfully.")
