import streamlit as st
import subprocess

# Display a menu to select which app to run
st.title("Application Menu")
option = st.selectbox("Choose an application to launch:", ("telecall_rate_builder3", "upload"))

# Run the selected application
if st.button("Launch Application"):
    if option == "telecall_rate_builder3":
        subprocess.Popen(["streamlit", "run", "telecall_rate_builder3.py", "--server.port=8080"])
    elif option == "upload":
        subprocess.Popen(["streamlit", "run", "upload.py", "--server.port=8080"])
    st.write(f"Launching {option}... Refresh the page to reset.")
