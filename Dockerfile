# Dockerfile for video-capture-service
# Designed for Raspberry Pi Zero 2 W with IMX camera

FROM python:3.11-slim

# Install system dependencies for picamera2 and ffmpeg
RUN apt-get update && apt-get install -y \
    python3-picamera2 \
    ffmpeg \
    libcamera-dev \
    libcamera-apps \
    python3-libcamera \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY capture_video.py .

# Create video output directory
RUN mkdir -p /videos

# Set environment variables
ENV VIDEO_OUTPUT_DIR=/videos
ENV PORT=8001

# Expose API port
EXPOSE 8001

# Run the FastAPI application
CMD ["python", "capture_video.py"]

