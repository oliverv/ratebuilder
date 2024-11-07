import streamlit as st
import subprocess
from PIL import Image

# Display logo and menu title
logo = Image.open("logo.png")
st.image(logo, width=50)
st.title("Application Menu")

# Application options
options = {
    "telecall_rate_builder": "telecall_rate_builder.py",
    "checker": "check.py",
    "upload": "upload.py",
    "streamlit_app": "streamlit_app.py",
    "telecall_rate_builder_old": "telecall_rate_builder_old.py"
}

# Select application from dropdown
option = st.selectbox("Choose an application to launch:", list(options.keys()))

# Run the selected application
if st.button("Launch Application"):
    selected_app = options[option]
    subprocess.Popen(["streamlit", "run", selected_app, "--server.port=8081"])
    st.write(f"Launching {option}... Refresh the page to reset.")
