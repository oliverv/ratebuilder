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
RUN apt-get update && apt-get install -y nginx && \
    pip install --no-cache-dir -r requirements.txt

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/sites-enabled/default

# Copy entrypoint script into the container
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the port for Nginx
EXPOSE 8080

# Start entrypoint script that will handle both Nginx and Streamlit apps
ENTRYPOINT ["/entrypoint.sh"]
