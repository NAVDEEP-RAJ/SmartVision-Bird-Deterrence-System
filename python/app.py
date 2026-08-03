"""
Flask Web Application for real-time monitoring and hardware control feed.
Manages background computer vision thread and exposes REST telemetry endpoints.
"""

import time
import logging
from collections import deque
import threading
from datetime import timedelta
import cv2  # Required for frame compression
from flask import Flask, Response, render_template, jsonify, request

from python import config
from python.hardware import ArduinoBridge
from python.detector import BirdDetector
from python.camera import CameraService

# Set up logging using the central configuration
logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT)
logger = logging.getLogger("AppOrchestrator")

app = Flask(__name__)
boot_time = time.time()

# Internal Telemetry buffers
system_logs = deque(maxlen=30)
total_deterrents_fired = 0
fps_measurement = 0

# Shared resources
output_frame = None
active_sighted = False
laser_status = "DEACTIVATED"

lock = threading.Lock()
arduino = ArduinoBridge()
camera = None
detector = None


def add_log(message: str):
    """Queues a message to log to python stdout and push to the frontend dashboard console."""
    logger.info(message)
    system_logs.append(message)


def video_processing_thread():
    """Background scanner thread performing camera acquisition, detection, and Arduino signalling."""
    global output_frame, active_sighted, laser_status, total_deterrents_fired, fps_measurement, camera, detector
    
    add_log("[SYSTEM] Launching Vision Service components...")
    
    detector = BirdDetector()
    camera = CameraService()
    
    bird_detected_state = False
    last_detect_time = 0
    frame_count = 0
    last_fps_calc = time.time()
    
    add_log("[SYSTEM] Detector thread active and monitoring.")

    while True:
        frame = camera.read_frame()
        if frame is None:
            time.sleep(0.01)
            continue
            
        # Performance/diagnostic tracking
        frame_count += 1
        current_time = time.time()
        
        if current_time - last_fps_calc >= 1.0:
            fps_measurement = frame_count
            frame_count = 0
            last_fps_calc = current_time

        # Run vision inference
        processed_frame, detected, metadata = detector.process_frame(frame)
        
        # State machine transition checking
        if detected:
            last_detect_time = current_time
            if not bird_detected_state:
                add_log("[ALARM] Target bird detected in active tracking grid!")
                arduino.send_command("BIRD")
                bird_detected_state = True
                total_deterrents_fired += 1
                laser_status = "ACTIVE"
        else:
            if bird_detected_state and (current_time - last_detect_time > config.CLEAR_DELAY_SECONDS):
                add_log("[SYSTEM] Area clear. Dismantling deterrent active state.")
                arduino.send_command("CLEAR")
                bird_detected_state = False
                laser_status = "DEACTIVATED"
                
        active_sighted = bird_detected_state
        
        # Thread-safe cache of latest frame
        with lock:
            output_frame = processed_frame.copy() if processed_frame is not None else None


def mjpeg_generator():
    """Compresses frames on-the-fly and generates multi-part HTTP MJPEG stream."""
    global output_frame
    while True:
        with lock:
            if output_frame is None:
                encoded_bytes = None
            else:
                success, buffer = cv2.imencode(".jpg", output_frame)
                encoded_bytes = buffer.tobytes() if success else None
                
        if encoded_bytes is None:
            time.sleep(0.05)
            continue
            
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + encoded_bytes + b"\r\n"
        )
        time.sleep(0.05)


@app.route("/")
def index():
    """Serves HUD Web Console page."""
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    """Bound route for direct live image stream ingestion."""
    return Response(
        mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/status")
def api_status():
    """REST endpoint delivering system metrics, hardware telemetry and latest event log lines."""
    uptime_seconds = int(time.time() - boot_time)
    uptime_str = str(timedelta(seconds=uptime_seconds))
    
    # Extract recent updates & reset queue to prevent duplicate notifications
    logs_slice = list(system_logs)
    system_logs.clear()
    
    payload = {
        "active_sighted": active_sighted,
        "total_detections": total_deterrents_fired,
        "laser_status": laser_status,
        "uptime": uptime_str,
        "fps": fps_measurement,
        "hardware": arduino.get_status(),
        "camera": camera.get_status() if camera else {"driver": "starting"},
        "logs": logs_slice
    }
    return jsonify(payload)


@app.route("/api/control", methods=["POST"])
def api_control():
    """Allows manual UI override trigger values."""
    global laser_status
    data = request.get_json() or {}
    action = data.get("action")
    
    if action == "BIRD":
        add_log("[USER OVERRIDE] Manual ALARM trigger submitted.")
        arduino.send_command("BIRD")
        laser_status = "ACTIVE"
        return jsonify({"success": True})
        
    elif action == "CLEAR":
        add_log("[USER OVERRIDE] Manual RESET cleared monitoring zones.")
        arduino.send_command("CLEAR")
        laser_status = "DEACTIVATED"
        return jsonify({"success": True})
        
    return jsonify({"success": False, "error": "Invalid target instruction."}), 400


if __name__ == "__main__":
    # Start vision processing background task
    monitor_thread = threading.Thread(
        target=video_processing_thread,
        daemon=True,
        name="VisionScanner"
    )
    monitor_thread.start()
    
    add_log(f"[SYSTEM] Init complete. Server listening on http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=False,
        threaded=True
    )
