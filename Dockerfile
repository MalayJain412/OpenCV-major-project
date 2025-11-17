# Use Python 3.12 bullseye slim base image for better package availability
FROM python:3.12-bullseye-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port (matching Procfile)
EXPOSE 5003

# Run the application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5003", "app:app"]