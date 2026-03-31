# Use a lightweight Python base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port (Render/Cloud Run will set the PORT environment variable)
EXPOSE 8000

# Command to run the application
# We use $PORT provided by the environment, defaulting to 8000 if not set
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
