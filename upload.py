import streamlit as st
from google.cloud import storage
from datetime import datetime
import os

# --- Google Cloud Storage Setup ---
BUCKET_NAME = 'ratestelecall'

def upload_to_bucket(file, bucket_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(file)
    return blob.public_url

def list_files_in_bucket(bucket_name):
    """Lists all the files in the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    files = [(blob.name, blob.public_url) for blob in blobs]
    return files

# --- Navigation Menu ---
menu_option = st.sidebar.selectbox("Choose a feature", ["Home", "File Upload", "View and Download Files"])

if menu_option == "Home":
    st.title("Welcome to Telecall - CSV Rate Aggregator")
    st.write("Use the menu to navigate through the app features.")

elif menu_option == "File Upload":
    # Title for File Upload Section
    st.title("Upload Files to Google Cloud Storage")
    st.write("Upload your files and process them on Google Cloud Storage.")
    
    # Step 1: File Upload
    uploaded_files = st.file_uploader("Upload CSV or ZIP files", type=["csv", "zip"], accept_multiple_files=True)

    # Step 2: Upload to GCS with Date Stamping
    if uploaded_files:
        for file in uploaded_files:
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination_blob_name = f"{timestamp}_{file.name}"
            
            # Upload file to Google Cloud Storage
            st.write(f"Uploading {file.name} to Google Cloud Storage...")
            try:
                file.seek(0)  # Reset file pointer
                public_url = upload_to_bucket(file, BUCKET_NAME, destination_blob_name)
                st.success(f"Uploaded {file.name} as {destination_blob_name}.")
                st.write(f"File URL: {public_url}")
            except Exception as e:
                st.error(f"Failed to upload {file.name}: {e}")

        # Step 3: Trigger Execution Code after Upload
        if st.button("Process Uploaded Files"):
            st.write("Starting processing for uploaded files...")
            # Run your processing code here, e.g., process_csv_data(uploaded_files, ...)
            st.success("Processing complete!")

elif menu_option == "View and Download Files":
    # Display list of files in the bucket
    st.title("View and Download Files from Google Cloud Storage")
    st.write("Files available in the bucket:")

    files = list_files_in_bucket(BUCKET_NAME)
    if files:
        for file_name, file_url in files:
            st.write(f"File: {file_name}")
            st.write(f"[Download Link]({file_url})")
    else:
        st.write("No files found in the bucket.")
