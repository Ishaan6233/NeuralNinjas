"""
Object detection using YOLOv8 for D&D campaign generation.
"""
import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Union
from pathlib import Path


def detect_objects_for_campaign(
    image_path: Union[str, Path],
    model_path: str = "yolov8n.pt",
    conf: float = 0.25,
) -> List[Dict[str, any]]:
    """
    Detect objects in an image for D&D campaign generation.

    Args:
        image_path: Path to the image file
        model_path: Path to YOLO model weights
        conf: Confidence threshold for detection

    Returns:
        List of detected objects with labels and confidence scores
    """
    # Load YOLO model
    model = YOLO(model_path)

    # Run detection
    results = model(image_path, conf=conf, verbose=False)

    detected_objects = []

    for result in results:
        boxes = result.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            conf_score = float(box.conf[0])
            label = result.names[cls_id]

            detected_objects.append({
                "label": label,
                "confidence": conf_score,
                "bbox": box.xyxy[0].tolist()
            })

    return detected_objects


def get_object_summary(detected_objects: List[Dict]) -> Dict[str, int]:
    """
    Create a summary of detected objects (counts by label).

    Args:
        detected_objects: List of detected objects

    Returns:
        Dictionary mapping object labels to counts
    """
    summary = {}
    for obj in detected_objects:
        label = obj["label"]
        summary[label] = summary.get(label, 0) + 1

    return summary
