# simple python to capture video until the program is terminated 
# tested on rasberry pi zero 2 w with IMX

from picamera2 import Picamera2, encoders
from picamera2.outputs import FfmpegOutput
import time
import signal
from datetime import datetime

running = True

def handle_sigint(signum, frame):
    global running
    print("\nStopping recording...")
    running = False

signal.signal(signal.SIGINT, handle_sigint)

def main():
    picam2 = Picamera2()

    video_config = picam2.create_video_configuration(
        main={"size": (1280, 720)},
        controls={"FrameDurationLimits": (33333, 33333)}
    )
    picam2.configure(video_config)

    encoder = encoders.H264Encoder(bitrate=5_000_000)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"video_{timestamp}.mp4"

    output = FfmpegOutput(filename)

    picam2.start()
    picam2.start_recording(encoder, output)
    print(f"Recording started. Writing to {filename}. Press Ctrl+C to stop.")

    try:
        while running:
            time.sleep(1)
    finally:
        picam2.stop_recording()
        picam2.stop()
        print(f"Recording stopped. Saved to {filename}!")

if __name__ == "__main__":
    main()