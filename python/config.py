"""
Configuration settings for the Bird Detection and Deterrence System.
This file holds all constant settings, hardware parameters, and network details.
"""

import os
import logging

# Logging Settings
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Flask Web Server Settings
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

# Computer Vision & Detection Settings
YOLO_MODEL_NAME = "yolov8n.pt"
DETECTION_CONFIDENCE = 0.25
TARGET_CLASS_ID = 14  # COCO class ID for 'bird'
CLEAR_DELAY_SECONDS = 1.0  # Time to wait before clearing alarm after last detection

# Serial Communications (Arduino Controller)
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 0.1
SERIAL_RETRY_INTERVAL = 5.0  # Seconds to wait before attempting to reconnect

# Camera Capture Parameters
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 20

# Command array for native Raspberry Pi Camera streaming via stdout
RPICAM_ARGS = [
    "rpicam-vid",
    "-t", "0",
    "--width", str(CAMERA_WIDTH),
    "--height", str(CAMERA_HEIGHT),
    "--framerate", str(CAMERA_FPS),
    "--codec", "yuv420",
    "-o", "-"
]
