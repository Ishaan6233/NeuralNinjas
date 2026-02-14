from functools import lru_cache
from typing import List, Dict, Tuple, Union
import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover
    YOLO = None

ImageLike = Union[str, np.ndarray]

@lru_cache(maxsize=1)
def _load_model(weights: str):
    if YOLO is None:
        raise ImportError(
            "ultralytics is not installed. Run: python -m pip install ultralytics"
        )
    return YOLO(weights)

def _to_image_array(image: ImageLike) -> np.ndarray:
    if isinstance(image, str):
        arr = cv2.imread(image, cv2.IMREAD_COLOR)
        if arr is None:
            raise FileNotFoundError(f"Could not read image at {image}")
        return arr
    if isinstance(image, np.ndarray):
        return image
    raise TypeError("image must be a file path or a numpy array")

def detect_objects(
    image: ImageLike,
    model_path: str = "yolov8n-seg.pt",
    conf: float = 0.25,
) -> List[Dict[str, object]]:
    """
    Run YOLOv8 segmentation and return a list of objects with label, box, and mask.
    box -> (x1, y1, x2, y2) ints in pixel coords
    mask -> boolean np.ndarray aligned to the input image (H, W)
    """
    frame = _to_image_array(image)
    h, w = frame.shape[:2]

    model = _load_model(model_path)
    result = model.predict(frame, conf=conf, verbose=False)[0]

    boxes = result.boxes
    masks = result.masks
    names = getattr(model.model, "names", None) or model.names

    objects = []
    if boxes is None:
        return objects

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
        cls_id = int(box.cls)
        label = names[cls_id] if names and cls_id in names else str(cls_id)

        mask_bool = None
        if masks is not None and len(masks.data) > i:
            mask_np = masks.data[i].cpu().numpy()
            # Resize to original frame size if needed
            if mask_np.shape[:2] != (h, w):
                mask_np = cv2.resize(mask_np, (w, h), interpolation=cv2.INTER_LINEAR)
            mask_bool = mask_np > 0.5

        objects.append(
            {
                "label": label,
                "box": (int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))),
                "mask": mask_bool,
            }
        )
    return objects

if __name__ == "__main__":
    img = "sample.jpg"
    objs = detect_objects(img)
    for o in objs:
        print(o["label"], o["box"], o["mask"].shape if o["mask"] is not None else None)
