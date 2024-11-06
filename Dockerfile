# Use the official Python 3.11 image as the base image
FROM python:3.11

# Set Streamlit-specific environment variables
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_HEADLESS=true

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .
RUN mkdir .streamlit
COPY .streamlit/config.toml .streamlit/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that Streamlit will run on
EXPOSE 8080

# Command to run the Streamlit app
CMD ["streamlit", "run", "telecall_rate_builder.py", "--server.port=8080", "--server.headless=true"]
