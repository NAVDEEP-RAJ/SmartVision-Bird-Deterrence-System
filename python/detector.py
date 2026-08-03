"""
YOLOv8 Computer Vision interface for detecting birds in live camera frames.
"""

import cv2
import logging
from ultralytics import YOLO
from python import config

logger = logging.getLogger("BirdDetector")


class BirdDetector:
    def __init__(self):
        logger.info(f"Loading object detection model: {config.YOLO_MODEL_NAME}...")
        self.model = YOLO(config.YOLO_MODEL_NAME)
        self.target_class_id = config.TARGET_CLASS_ID
        self.conf_threshold = config.DETECTION_CONFIDENCE

    def process_frame(self, frame):
        """
        Scans a frame for bird objects.
        Draws professional antialiased HUD graphics on matches.

        Returns:
            tuple: (processed_frame, detected_bool, metadata_dict)
        """
        if frame is None:
            return None, False, {}

        # Run model inference (suppress stdout predictions)
        results = self.model(
            frame,
            conf=self.conf_threshold,
            verbose=False
        )

        detected = False
        metadata = {"targets": []}

        for result in results:
            if not result.boxes:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])

                if class_id == self.target_class_id:
                    detected = True
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2

                    metadata["targets"].append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": confidence,
                        "center": [cx, cy]
                    })

                    # Draw vibrant green bounding box
                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        (46, 204, 113),  # Emerald green (BGR)
                        2,
                        lineType=cv2.LINE_AA
                    )

                    # Bounding box center targeting dot
                    cv2.circle(
                        frame,
                        (cx, cy),
                        5,
                        (52, 152, 219),  # Vibrant blue center target (BGR)
                        -1,
                        lineType=cv2.LINE_AA
                    )

                    # Elegant text tag with filled background badge
                    label_text = f"BIRD DETECTED: {confidence:.0%}"
                    (w, h), base = cv2.getTextSize(
                        label_text,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        1
                    )
                    
                    # Boundary protection for top margin
                    label_y = max(y1 - 6, h + 6)
                    cv2.rectangle(
                        frame,
                        (x1, label_y - h - 4),
                        (x1 + w + 6, label_y + base - 2),
                        (46, 204, 113),
                        cv2.FILLED
                    )

                    # Dark caption text for maximum readability
                    cv2.putText(
                        frame,
                        label_text,
                        (x1 + 3, label_y - 2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (33, 33, 33),  # Dark charcoal text
                        1,
                        lineType=cv2.LINE_AA
                    )

        return frame, detected, metadata
