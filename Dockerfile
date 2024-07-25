FROM python:3.11

# Set environment variables
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_HEADLESS=true

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    python3.11 \
    python3-pip \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that Streamlit uses
EXPOSE 8080

# Command to run the Streamlit app
CMD ["streamlit", "run", "app1.py"]
#"--server.maxUploadSize 1000", "--browser.serverPort 8080"]
