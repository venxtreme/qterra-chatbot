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

# Hugging Face Spaces requires port 7860
EXPOSE 7860

# Run the app on port 7860 (required by HF Spaces)
CMD uvicorn main:app --host 0.0.0.0 --port 7860
