# Recording manager for video capture
# Handles camera control and recording state management
# Designed for Raspberry Pi Zero 2 W with IMX camera

import sys
import os

# Ensure system packages are in path (for picamera2 installed via apt)
if '/usr/lib/python3/dist-packages' not in sys.path:
    sys.path.insert(0, '/usr/lib/python3/dist-packages')

from picamera2 import Picamera2, encoders
from picamera2.outputs import FfmpegOutput
import time
import threading
from typing import Optional


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
            
            try:
                self.recording_id = recording_id
                self.filename = filename
                self.duration = duration
                self.max_file_size = max_file_size
                self.start_time = time.time()
                
                # Initialize camera
                print(f"Initializing camera for recording {recording_id}...")
                
                # Check if camera device files exist
                import os
                video_devices = ['/dev/video0', '/dev/video10', '/dev/video11', '/dev/video12']
                found_devices = [d for d in video_devices if os.path.exists(d)]
                print(f"Camera device files found: {found_devices}")
                
                if not found_devices:
                    raise RuntimeError("No camera device files found. Ensure /dev/video0 and /dev/vchiq are mounted in the container.")
                
                # Check camera availability via libcamera
                try:
                    camera_info = Picamera2.global_camera_info()
                    print(f"Available cameras (libcamera): {len(camera_info)}")
                    if len(camera_info) == 0:
                        raise RuntimeError("No cameras detected by libcamera. Check device mounts, permissions, and that the camera is enabled.")
                    print(f"Camera info: {camera_info}")
                except Exception as e:
                    print(f"Error checking camera info: {e}")
                    raise RuntimeError(f"Camera not available: {str(e)}")
                
                # Initialize camera (try camera 0 explicitly)
                try:
                    self.picam2 = Picamera2(camera_num=0)
                except Exception as e:
                    print(f"Error initializing Picamera2: {e}")
                    raise RuntimeError(f"Failed to initialize camera: {str(e)}")
                
                video_config = self.picam2.create_video_configuration(
                    main={"size": (1280, 720)},
                    controls={"FrameDurationLimits": (33333, 33333)}
                )
                self.picam2.configure(video_config)
                
                print(f"Creating encoder and output for {filename}...")
                self.encoder = encoders.H264Encoder(bitrate=5_000_000)
                self.output = FfmpegOutput(filename)
                
                print("Starting camera...")
                self.picam2.start()
                print("Starting recording...")
                self.picam2.start_recording(self.encoder, self.output)
                self.is_recording = True
                print(f"Recording started successfully: {filename}")
                
                # Start monitoring thread
                self.monitor_thread = threading.Thread(target=self._monitor_recording, daemon=True)
                self.monitor_thread.start()
            except Exception as e:
                # Clean up on error
                print(f"Error starting recording: {e}")
                self.is_recording = False
                if self.picam2:
                    try:
                        self.picam2.stop()
                    except:
                        pass
                    self.picam2 = None
                self.encoder = None
                self.output = None
                raise
    
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

