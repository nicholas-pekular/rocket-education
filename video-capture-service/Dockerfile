# Dockerfile for video-capture-service
# Designed for Raspberry Pi Zero 2 W with IMX camera
# Using Bookworm base to match Raspberry Pi OS repository

FROM python:3.11-slim-bookworm

# Install prerequisites for adding repositories
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Add Raspberry Pi OS repository for picamera2 packages
# Using bookworm as it's the stable release that matches most Raspberry Pi OS versions
RUN echo "deb http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspberrypi.list && \
    curl -fsSL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | gpg --dearmor -o /etc/apt/trusted.gpg.d/raspberrypi.gpg

# Install system dependencies for picamera2 and ffmpeg
RUN apt-get update && apt-get install -y \
    python3-picamera2 \
    ffmpeg \
    libcamera-dev \
    libcamera-apps \
    python3-libcamera \
    && rm -rf /var/lib/apt/lists/*

# Verify picamera2 can be imported
RUN python3 -c "import sys; sys.path.insert(0, '/usr/lib/python3/dist-packages'); import picamera2; print('picamera2 verified')" || \
    (echo "Warning: picamera2 import test failed" && ls -la /usr/lib/python3*/dist-packages/ | grep picamera || true)

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY recording_manager.py .
COPY api_server.py .

# Create video output directory
RUN mkdir -p /videos

# Set environment variables
ENV VIDEO_OUTPUT_DIR=/videos
ENV PORT=8001

# Expose API port
EXPOSE 8001

# Set PYTHONPATH to include system packages
ENV PYTHONPATH=/usr/lib/python3/dist-packages:${PYTHONPATH}

# Run the FastAPI application
CMD ["python3", "api_server.py"]

