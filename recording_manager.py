# Recording manager for video capture
# Handles camera control and recording state management
# Designed for Raspberry Pi Zero 2 W with IMX camera

from picamera2 import Picamera2, encoders
from picamera2.outputs import FfmpegOutput
import time
import threading
from typing import Optional
import os


class RecordingState:
    """Manages video recording state and camera control"""
    
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
        """Start a new video recording"""
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
        """Stop the current video recording"""
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

