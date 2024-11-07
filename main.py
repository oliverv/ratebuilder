import streamlit as st
import subprocess

# Display a menu to select which app to run
logo = Image.open("logo.png")
st.image(logo, width=50)

st.title("Application Menu")

option = st.selectbox("Choose an application to launch:", ("telecall_rate_builder", "checker" , "upload" , "streamlit_app"))

# Run the selected application
if st.button("Launch Application"):
    if option == "telecall_rate_builder":
        subprocess.Popen(["streamlit", "run", "telecall_rate_builder.py", "--server.port=8080"])
    if option == "checker":
        subprocess.Popen(["streamlit", "run", "check.py", "--server.port=8080"])
    st.write(f"Launching {option}... Refresh the page to reset.")
    if option == "upload":
        subprocess.Popen(["streamlit", "run", "upload.py", "--server.port=8080"])
    st.write(f"Launching {option}... Refresh the page to reset.")
    if option == "streamlit_app":
        subprocess.Popen(["streamlit", "run", "streamlit_app.py", "--server.port=8080"])
    st.write(f"Launching {option}... Refresh the page to reset.")
    elif option == "telecall_rate_builder_old":
        subprocess.Popen(["streamlit", "run", "telecall_rate_builder_old.py", "--server.port=8080"])
    st.write(f"Launching {option}... Refresh the page to reset.")
    
