import streamlit as st
from PIL import Image

# Display the logo and application title
logo = Image.open("logo.png")
st.image(logo, width=100)
st.title("Application Switcher")

st.write("Select an application below to open it in a new tab:")

# Create buttons to launch each application
if st.button("Telecall Rate Builder"):
    st.markdown("[Open Telecall Rate Builder](http://localhost:8080/app1/)", unsafe_allow_html=True)

if st.button("Checker"):
    st.markdown("[Open Checker](http://localhost:8080/app2/)", unsafe_allow_html=True)

if st.button("Uploader"):
    st.markdown("[Open Uploader](http://localhost:8080/app3/)", unsafe_allow_html=True)
