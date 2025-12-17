# Video capture service with FastAPI control
# Designed for Raspberry Pi Zero 2 W with IMX camera
# Containerized as video-capture-service

from picamera2 import Picamera2, encoders
from picamera2.outputs import FfmpegOutput
import time
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import ulid

app = FastAPI(title="Video Capture Service")

# Recording state
class RecordingState:
    def __init__(self):
        self.is_recording = False
        self.recording_id = None
        self.picam2 = None
        self.encoder = None
        self.output = None
        self.filename = None
        self.start_time = None
        self.duration = None
        self.max_file_size = None
        self.monitor_thread = None
        self.lock = threading.Lock()
    
    def start_recording(self, recording_id: str, filename: str, duration: Optional[int], max_file_size: int):
        with self.lock:
            if self.is_recording:
                raise ValueError("Recording already in progress")
            
            self.recording_id = recording_id
            self.filename = filename
            self.duration = duration
            self.max_file_size = max_file_size
            self.start_time = time.time()
            
            # Initialize camera
            self.picam2 = Picamera2()
            video_config = self.picam2.create_video_configuration(
                main={"size": (1280, 720)},
                controls={"FrameDurationLimits": (33333, 33333)}
            )
            self.picam2.configure(video_config)
            
            self.encoder = encoders.H264Encoder(bitrate=5_000_000)
            self.output = FfmpegOutput(filename)
            
            self.picam2.start()
            self.picam2.start_recording(self.encoder, self.output)
            self.is_recording = True
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_recording, daemon=True)
            self.monitor_thread.start()
    
    def stop_recording(self):
        with self.lock:
            if not self.is_recording:
                return None
            
            recording_id = self.recording_id
            
            try:
                if self.picam2:
                    self.picam2.stop_recording()
                    self.picam2.stop()
            except Exception as e:
                print(f"Error stopping recording: {e}")
            finally:
                self.is_recording = False
                self.picam2 = None
                self.encoder = None
                self.output = None
            
            return recording_id
    
    def _monitor_recording(self):
        """Monitor recording for duration and file size limits"""
        while self.is_recording:
            time.sleep(1)  # Check every second
            
            # Check duration
            if self.duration is not None:
                elapsed = time.time() - self.start_time
                if elapsed >= self.duration:
                    print(f"Duration limit reached ({self.duration}s), stopping recording...")
                    self.stop_recording()
                    break
            
            # Check file size
            if self.max_file_size is not None and self.filename and os.path.exists(self.filename):
                try:
                    file_size = os.path.getsize(self.filename)
                    if file_size >= self.max_file_size:
                        print(f"File size limit reached ({self.max_file_size} bytes), stopping recording...")
                        self.stop_recording()
                        break
                except Exception as e:
                    print(f"Error checking file size: {e}")

recording_state = RecordingState()

# API Models
class StartRecordingRequest(BaseModel):
    duration: Optional[int] = None  # Duration in seconds
    file_prefix: Optional[str] = None
    max_file_size: Optional[int] = 500 * 1024 * 1024  # Default 500MB in bytes

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
        recording_id = str(ulid.new())
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        prefix = request.file_prefix if request.file_prefix else "video"
        filename = f"{prefix}_{timestamp}_{recording_id}.mp4"
        
        # Ensure output directory exists (will be mounted as volume)
        output_dir = os.getenv("VIDEO_OUTPUT_DIR", "/videos")
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        # Start recording
        recording_state.start_recording(
            recording_id=recording_id,
            filename=filepath,
            duration=request.duration,
            max_file_size=request.max_file_size
        )
        
        return StartRecordingResponse(
            recording_id=recording_id,
            filename=filename,
            message=f"Recording started with ID: {recording_id}"
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start recording: {str(e)}")

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
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
