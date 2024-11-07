# Use the official Python 3.11 image as the base image
FROM python:3.11

# Set Streamlit-specific environment variables
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true

# Set the working directory in the container
WORKDIR /app


# Copy the rest of the application code into the container
COPY . .

# Copy the requirements file into the container
COPY requirements.txt .
RUN mkdir .streamlit
COPY .streamlit/config.toml .streamlit/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Install Nginx
RUN apt-get update && apt-get install -y nginx
# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Start Nginx alongside Streamlit
CMD service nginx start && streamlit run app_switcher.py --server.port=8500

# Expose the Streamlit default port
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "menu_app.py"]

