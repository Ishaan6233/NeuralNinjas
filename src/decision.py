import cv2
import numpy as np


def decide_hiding_spot(image: np.ndarray, objects: list, batman_size: tuple):
    """
    image: full input image as a numpy array
    objects: list of dicts with keys "label", "box", "mask"
    batman_size: tuple (width, height) of the Batman sprite
    returns: (best_object, (hide_x, hide_y))
    """
    if image is None or image.size == 0:
        raise ValueError("image must be a non-empty numpy array")
    if not objects:
        raise ValueError("objects list cannot be empty")

    img_h, img_w = image.shape[:2]
    batman_w, batman_h = batman_size

    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
    success, saliency_map = saliency.computeSaliency(image)

    if not success or saliency_map is None:
        saliency_map = np.zeros((img_h, img_w), dtype=np.uint8)
    else:
        saliency_map = (saliency_map * 255).astype(np.uint8)

    image_area = float(img_w * img_h)
    best_score = float("-inf")
    best_object = None
    best_location = (0, 0)

    for obj in objects:
        x1, y1, x2, y2 = obj["box"]

        x1 = int(np.clip(x1, 0, img_w - 1))
        y1 = int(np.clip(y1, 0, img_h - 1))
        x2 = int(np.clip(x2, 1, img_w))
        y2 = int(np.clip(y2, 1, img_h))

        if x2 <= x1 or y2 <= y1:
            continue

        width = x2 - x1
        height = y2 - y1
        area_score = (width * height) / image_area

        region = saliency_map[y1:y2, x1:x2]
        mean_saliency = float(np.mean(region)) if region.size > 0 else 0.0
        low_saliency_score = 1.0 - (mean_saliency / 255.0)

        combined_score = area_score + low_saliency_score

        if combined_score > best_score:
            best_score = combined_score
            best_object = obj

            candidates = [
                (x2 - batman_w, y2 - batman_h),
                (x1, y2 - batman_h),
                (x2 - batman_w, y1),
                (x1, y1),
            ]

            hide_x, hide_y = 0, 0
            for cx, cy in candidates:
                cx = int(np.clip(cx, 0, max(0, img_w - batman_w)))
                cy = int(np.clip(cy, 0, max(0, img_h - batman_h)))
                if cx + batman_w <= img_w and cy + batman_h <= img_h:
                    hide_x, hide_y = cx, cy
                    break

            best_location = (hide_x, hide_y)

    return best_object, best_location
