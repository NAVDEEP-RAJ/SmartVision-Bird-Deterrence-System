"""
Platform-agnostic camera streaming module.
Runs high-performance Raspberry Pi camera commands but falls back to active OpenCV webcams on PC.
"""

import cv2
import numpy as np
import subprocess
import logging
from python import config

logger = logging.getLogger("CameraService")


class CameraService:
    def __init__(self):
        self.width = config.CAMERA_WIDTH
        self.height = config.CAMERA_HEIGHT
        self.fps = config.CAMERA_FPS
        
        self.process = None
        self.capture = None
        self.driver = None  # "rpicam" or "opencv"
        
        self._start_stream()

    def _start_stream(self):
        """Attempts to start rpicam-vid utility, defaulting to system webcam if missing."""
        try:
            logger.info("Starting hardware rpicam-vid process pipeline...")
            self.process = subprocess.Popen(
                config.RPICAM_ARGS,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            self.driver = "rpicam"
            logger.info("Raspberry Pi High-Speed camera pipeline online.")
        except (FileNotFoundError, OSError):
            logger.warning("rpicam-vid utility not found, switching to OpenCV driver...")
            self._start_opencv()
        except Exception as e:
            logger.warning(f"Unexpected camera error: {e}. Switching to OpenCV driver...")
            self._start_opencv()

    def _start_opencv(self):
        """Configures platform webcam capture."""
        self.capture = cv2.VideoCapture(0)
        if self.capture.isOpened():
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.capture.set(cv2.CAP_PROP_FPS, self.fps)
            self.driver = "opencv"
            logger.info("OpenCV system webcam stream online.")
        else:
            self.driver = None
            logger.error("Camera interface initialization failed - no inputs available.")

    def read_frame(self):
        """
        Polls the active camera driver for raw images.
        Outputs BGR standard OpenCV array format.
        """
        if self.driver == "rpicam" and self.process:
            frame_bytes = self.width * self.height * 3 // 2
            try:
                raw_data = self.process.stdout.read(frame_bytes)
                if len(raw_data) != frame_bytes:
                    logger.warning("Incomplete video buffer read. Refreshing connection...")
                    self._start_opencv()
                    return self.read_frame()
                
                # Reshape YUV420 planar buffer to BGR
                yuv_array = np.frombuffer(raw_data, dtype=np.uint8)
                yuv_array = yuv_array.reshape((self.height * 3 // 2, self.width))
                bgr_frame = cv2.cvtColor(yuv_array, cv2.COLOR_YUV2BGR_I420)
                return bgr_frame
            except Exception as e:
                logger.error(f"Error compiling active Pi Stream: {e}. Shifting default drivers...")
                self._start_opencv()
                return self.read_frame()

        elif self.driver == "opencv" and self.capture:
            success, bgr_frame = self.capture.read()
            if success:
                return bgr_frame
            else:
                logger.warning("Failed capture on OpenCV stream frame.")
                return None
                
        return None

    def get_status(self) -> dict:
        """Retrieves diagnostics for camera device."""
        return {
            "driver": self.driver,
            "width": self.width,
            "height": self.height,
            "fps": self.fps
        }

    def close(self):
        """Terminates open camera pipeline handles."""
        logger.info("Releasing camera capture interfaces...")
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1.0)
            except Exception:
                pass
            self.process = None
        if self.capture:
            try:
                self.capture.release()
            except Exception:
                pass
            self.capture = None
        self.driver = None
