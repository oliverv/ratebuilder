#!/bin/bash

# Default to running telecall_rate_builder3.py if no APP_NAME is provided
APP_NAME=${APP_NAME:-telecall_rate_builder.py}

# Run the specified Streamlit app
exec streamlit run "$APP_NAME" --server.port="$STREAMLIT_SERVER_PORT" --server.headless="$STREAMLIT_SERVER_HEADLESS"
