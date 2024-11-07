import streamlit as st
from PIL import Image

# Display the logo and application title
logo = Image.open("logo.png")
st.image(logo, width=100)
st.title("Application Switcher")

st.write("Select an application below to open it in a new tab:")

# Retrieve the current host's base URL to make links flexible
base_url = f"{st.experimental_get_query_params().get('base_url', [''])[0] or 'https://ratebuilder.oliverv.dev'}"

# Create buttons to launch each application
if st.button("Telecall Rate Builder"):
    st.markdown(f"[Open Telecall Rate Builder]({base_url}/app1/)", unsafe_allow_html=True)

if st.button("Checker"):
    st.markdown(f"[Open Checker]({base_url}/app2/)", unsafe_allow_html=True)

if st.button("Uploader"):
    st.markdown(f"[Open Uploader]({base_url}/app3/)", unsafe_allow_html=True)
