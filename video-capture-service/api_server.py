# FastAPI server for video capture service
# Provides REST API endpoints to control video recording
# Containerized as video-capture-service

import sys
import os

# Debug: Print Python info before importing anything
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")

# Ensure system packages are in path BEFORE importing recording_manager
if '/usr/lib/python3/dist-packages' not in sys.path:
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
print(f"Updated Python path: {sys.path}")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import traceback
from datetime import datetime

# Import ULID - python-ulid package
# python-ulid 2.2.0: import the package and use ULID class
import ulid

# Debug: Check what's in the ulid module (only print once)
# print(f"ULID module dir: {[x for x in dir(ulid) if not x.startswith('_')]}")

# Try to create ULID - python-ulid 2.x uses ULID() constructor
try:
    # Test if we can create a ULID
    test_ulid = ulid.ULID()
    def generate_ulid():
        """Generate a new ULID string"""
        return str(ulid.ULID())
except (AttributeError, TypeError) as e:
    print(f"Error creating ULID: {e}")
    # Fallback to uuid
    import uuid
    def generate_ulid():
        """Generate a new UUID string (fallback)"""
        return str(uuid.uuid4())

from recording_manager import RecordingState

app = FastAPI(title="Video Capture Service")

# Initialize recording state
recording_state = RecordingState()

# API Models
class StartRecordingRequest(BaseModel):
    duration: Optional[int] = None
    file_prefix: Optional[str] = None
    max_file_size: Optional[int] = 500 * 1024 * 1024 

class StartRecordingResponse(BaseModel):
    recording_id: str
    filename: str
    message: str

class StopRecordingResponse(BaseModel):
    recording_id: str
    filename: str
    message: str

# API Endpoints
@app.post("/record/start", response_model=StartRecordingResponse)
def start_recording(request: StartRecordingRequest):
    """Start a new video recording"""
    try:
        with recording_state.lock:
            if recording_state.is_recording:
                raise HTTPException(status_code=409, detail="Recording already in progress")
        
        # Generate ULID for recording
        recording_id = generate_ulid()
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        prefix = request.file_prefix if request.file_prefix else "video"
        filename = f"{prefix}_{timestamp}_{recording_id}.mp4"
        
        # Ensure output directory exists (will be mounted as volume)
        output_dir = os.getenv("VIDEO_OUTPUT_DIR", "/videos")
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        # Start recording
        try:
            recording_state.start_recording(
                recording_id=recording_id,
                filename=filepath,
                duration=request.duration,
                max_file_size=request.max_file_size
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            error_msg = f"Failed to start recording: {str(e)}"
            print(f"ERROR: {error_msg}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=error_msg)
        
        return StartRecordingResponse(
            recording_id=recording_id,
            filename=filename,
            message=f"Recording started with ID: {recording_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"ERROR: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/record/stop", response_model=StopRecordingResponse)
def stop_recording():
    """Stop the current video recording"""
    try:
        with recording_state.lock:
            if not recording_state.is_recording:
                raise HTTPException(status_code=404, detail="No recording in progress")
            
            # Save filename and recording_id before stopping
            filename = os.path.basename(recording_state.filename) if recording_state.filename else "unknown"
            recording_id = recording_state.recording_id
        
        # Stop the recording (this will clear the state)
        stopped_id = recording_state.stop_recording()
        
        if stopped_id is None or stopped_id != recording_id:
            raise HTTPException(status_code=500, detail="Error stopping recording")
        
        return StopRecordingResponse(
            recording_id=recording_id,
            filename=filename,
            message=f"Recording stopped. ID: {recording_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop recording: {str(e)}")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "video-capture-service"}

@app.get("/record/status")
def get_recording_status():
    """Get the current recording status"""
    with recording_state.lock:
        if recording_state.is_recording:
            elapsed = time.time() - recording_state.start_time if recording_state.start_time else 0
            filename = os.path.basename(recording_state.filename) if recording_state.filename else None
            
            # Get current file size if file exists
            file_size = 0
            if recording_state.filename and os.path.exists(recording_state.filename):
                try:
                    file_size = os.path.getsize(recording_state.filename)
                except:
                    pass
            
            return {
                "is_recording": True,
                "recording_id": recording_state.recording_id,
                "filename": filename,
                "elapsed_seconds": int(elapsed),
                "duration_limit": recording_state.duration,
                "max_file_size": recording_state.max_file_size,
                "current_file_size": file_size
            }
        else:
            return {
                "is_recording": False,
                "recording_id": None,
                "filename": None
            }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)

