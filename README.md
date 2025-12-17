# rocket-education
code snippets for educational model rocket stuff

## Video Capture Service

A containerized video capture service for Raspberry Pi Zero 2 W with IMX camera, controlled via FastAPI.

### Prerequisites

```bash
# On Raspberry Pi, install Docker and Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### Building and Running

#### Using Docker Compose (Recommended)

```bash
# Build and start the service
docker-compose up -d --build

# View logs
docker-compose logs -f video-capture-service

# Stop the service
docker-compose down
```

#### Using Docker directly

```bash
# Build the image
docker build -t video-capture-service .

# Run the container
docker run -d \
  --name video-capture-service \
  --privileged \
  -p 8001:8001 \
  -v $(pwd)/videos:/videos \
  --device=/dev/video0:/dev/video0 \
  --device=/dev/vchiq:/dev/vchiq \
  video-capture-service
```

### API Usage

The service exposes a FastAPI server on port 8001. API documentation is available at `http://localhost:8001/docs`.

#### Start Recording

**Using curl:**

```bash
# Start recording with default settings (500MB max file size)
curl -X POST "http://localhost:8001/record/start" \
  -H "Content-Type: application/json" \
  -d '{}'

# Start recording with custom duration (60 seconds)
curl -X POST "http://localhost:8001/record/start" \
  -H "Content-Type: application/json" \
  -d '{"duration": 60}'

# Start recording with custom prefix and max file size
curl -X POST "http://localhost:8001/record/start" \
  -H "Content-Type: application/json" \
  -d '{
    "file_prefix": "rocket_launch",
    "max_file_size": 1000000000,
    "duration": 120
  }'
```

**Using Python requests:**

```python
import requests

BASE_URL = "http://localhost:8001"

# Start recording with default settings (500MB max file size)
response = requests.post(f"{BASE_URL}/record/start", json={})
print(response.json())

# Start recording with custom duration (60 seconds)
response = requests.post(
    f"{BASE_URL}/record/start",
    json={"duration": 60}
)
print(response.json())

# Start recording with custom prefix and max file size
response = requests.post(
    f"{BASE_URL}/record/start",
    json={
        "file_prefix": "rocket_launch",
        "max_file_size": 1000000000,  # 1GB in bytes
        "duration": 120  # 2 minutes
    }
)
print(response.json())
```

Response:
```json
{
  "recording_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "filename": "video_2024-01-15_14-30-00_01ARZ3NDEKTSV4RRFFQ69G5FAV.mp4",
  "message": "Recording started with ID: 01ARZ3NDEKTSV4RRFFQ69G5FAV"
}
```

#### Stop Recording

**Using curl:**

```bash
curl -X POST "http://localhost:8001/record/stop"
```

**Using Python requests:**

```python
import requests

BASE_URL = "http://localhost:8001"

response = requests.post(f"{BASE_URL}/record/stop")
print(response.json())
```

Response:
```json
{
  "recording_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "filename": "video_2024-01-15_14-30-00_01ARZ3NDEKTSV4RRFFQ69G5FAV.mp4",
  "message": "Recording stopped. ID: 01ARZ3NDEKTSV4RRFFQ69G5FAV"
}
```

#### Get Recording Status

**Using curl:**

```bash
curl "http://localhost:8001/record/status"
```

**Using Python requests:**

```python
import requests

BASE_URL = "http://localhost:8001"

response = requests.get(f"{BASE_URL}/record/status")
print(response.json())
```

Response (when recording):
```json
{
  "is_recording": true,
  "recording_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "filename": "video_2024-01-15_14-30-00_01ARZ3NDEKTSV4RRFFQ69G5FAV.mp4",
  "elapsed_seconds": 45,
  "duration_limit": 120,
  "max_file_size": 500000000,
  "current_file_size": 23456789
}
```

### Complete Python Example

```python
import requests
import time

BASE_URL = "http://localhost:8001"

# Start a recording
print("Starting recording...")
start_response = requests.post(
    f"{BASE_URL}/record/start",
    json={
        "file_prefix": "rocket_launch",
        "duration": 60,  # Record for 60 seconds
        "max_file_size": 500000000  # 500MB max
    }
)
start_data = start_response.json()
print(f"Recording started: {start_data}")

recording_id = start_data["recording_id"]

# Monitor recording status
for i in range(10):
    time.sleep(5)
    status_response = requests.get(f"{BASE_URL}/record/status")
    status = status_response.json()
    if status["is_recording"]:
        print(f"Recording in progress: {status['elapsed_seconds']}s elapsed, "
              f"{status['current_file_size'] / 1024 / 1024:.2f}MB recorded")
    else:
        print("Recording has stopped")
        break

# Stop recording (if still running)
if status["is_recording"]:
    stop_response = requests.post(f"{BASE_URL}/record/stop")
    print(f"Recording stopped: {stop_response.json()}")
```

### Video Output

Recorded videos are saved to the `./videos` directory (mounted as a volume) with the format:
`<prefix>_<timestamp>_<ulid>.mp4`

Example: `video_2024-01-15_14-30-00_01ARZ3NDEKTSV4RRFFQ69G5FAV.mp4`

### API Parameters

#### Start Recording Request
- `duration` (optional): Maximum recording duration in seconds. Recording will auto-stop when reached.
- `file_prefix` (optional): Prefix for the filename (default: "video")
- `max_file_size` (optional): Maximum file size in bytes (default: 500MB = 524288000 bytes). Recording will auto-stop when reached.

### Notes

- Only one recording can be active at a time
- Recordings automatically stop when:
  - Duration limit is reached (if specified)
  - File size limit is reached (if specified)
  - Stop endpoint is called
- The container requires privileged mode and device access for camera functionality
- Videos are saved to the mounted volume at `/videos` inside the container (mapped to `./videos` on the host)
