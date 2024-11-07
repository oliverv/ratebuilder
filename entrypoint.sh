#!/bin/bash

# Start Nginx
service nginx start

# Start each Streamlit app on a different port
streamlit run telecall_rate_builder.py --server.port=8080 &
#streamlit run check.py --server.port=8502 &
#streamlit run upload.py --server.port=8503 &

# Keep the container running
tail -f /dev/null

# Default to running telecall_rate_builder3.py if no APP_NAME is provided
#APP_NAME=${APP_NAME:-telecall_rate_builder.py}

# Run the specified Streamlit app
#exec streamlit run "$APP_NAME" --server.port="$STREAMLIT_SERVER_PORT" --server.headless="$STREAMLIT_SERVER_HEADLESS"
