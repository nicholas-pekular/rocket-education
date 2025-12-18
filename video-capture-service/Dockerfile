# Dockerfile for video-capture-service
# Designed for Raspberry Pi Zero 2 W with IMX camera
# Using Debian Bookworm base to match Raspberry Pi OS repository

FROM debian:bookworm-slim

# Install Python 3.11 and prerequisites
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    build-essential \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks so python3 points to python3.11
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Install pip for Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 && \
    python3.11 -m pip install --upgrade pip && \
    python3.11 -m pip --version

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

# Find where picamera2 is installed and verify
RUN echo "=== Checking Python versions ===" && \
    python3 --version && \
    python --version && \
    echo "=== Checking picamera2 installation ===" && \
    find /usr -name "picamera2" -type d 2>/dev/null && \
    find /usr -name "*picamera2*" 2>/dev/null | head -10 && \
    echo "=== Checking dist-packages ===" && \
    ls -la /usr/lib/python3*/dist-packages/ | grep -i picamera || echo "No picamera2 in dist-packages" && \
    echo "=== Testing import with system python3 ===" && \
    python3 -c "import sys; print('Python path:', sys.path); import picamera2; print('✓ picamera2 found')" || \
    (echo "=== Trying with explicit path ===" && \
     python3 -c "import sys; sys.path.insert(0, '/usr/lib/python3/dist-packages'); import picamera2; print('✓ picamera2 found with path')" || \
     echo "⚠ picamera2 import failed")

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3.11 -m pip --version && \
    python3.11 -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python3.11 -m pip install --no-cache-dir -r requirements.txt

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

# Verify we can import picamera2 before starting - use the same python3 that will run the app
RUN which python3 && \
    python3 -c "import sys; print('Build Python:', sys.executable); print('Build Path:', sys.path)" && \
    python3 -c "import picamera2; print('✓ picamera2 is available at build time')" || \
    (echo "ERROR: picamera2 not available at build time" && \
     find /usr -name "picamera2" -type d 2>/dev/null && \
     ls -la /usr/lib/python3*/dist-packages/ 2>/dev/null | head -20 && \
     exit 1)

# Run the FastAPI application using system python3
CMD ["python3", "api_server.py"]

