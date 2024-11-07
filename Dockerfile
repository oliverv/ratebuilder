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

# Copy entrypoint script into the container
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the port that Streamlit will run on
EXPOSE 8080

# Command to run the Streamlit app
CMD ["streamlit", "run", "telecall_rate_builder3.py", "--server.port=8080", "--server.headless=true"]
# Command to run the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
# Start supervisord to run Nginx and multiple Streamlit apps
#CMD ["/usr/bin/supervisord"]
