# Use the official Python 3.11 image as the base image
FROM python:3.11

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_HEADLESS=true

# Set the working directory in the container
WORKDIR /app

# Copy application code into the container
COPY . .

# Copy the requirements file into the container
COPY requirements.txt .
RUN mkdir -p .streamlit
COPY .streamlit/config.toml .streamlit/

# Install dependencies
RUN apt-get update && apt-get install -y nginx supervisor && \
    pip install --no-cache-dir -r requirements.txt

# Copy Nginx and supervisord configuration
COPY nginx.conf /etc/nginx/sites-enabled/default
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose Nginx port
EXPOSE 8080

# Start supervisord to run Nginx and multiple Streamlit apps
#CMD ["/usr/bin/supervisord"]
