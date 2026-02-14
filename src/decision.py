import cv2
import numpy as np


def _normalize_depth(depth_map: np.ndarray) -> np.ndarray:
    depth = depth_map.astype(np.float32)
    min_val = float(np.min(depth))
    max_val = float(np.max(depth))
    if max_val <= min_val:
        return np.zeros_like(depth, dtype=np.float32)
    return (depth - min_val) / (max_val - min_val)


def _safe_mean(region: np.ndarray) -> float:
    return float(np.mean(region)) if region.size > 0 else 0.0


def decide_hiding_spot(
    image: np.ndarray, objects: list, batman_size: tuple, depth_map: np.ndarray | None = None
):
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
    depth_norm = None
    if depth_map is not None:
        if depth_map.shape[:2] != (img_h, img_w):
            raise ValueError("depth_map must have same height/width as image")
        depth_norm = _normalize_depth(depth_map)

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
        mean_saliency = _safe_mean(region)
        low_saliency_score = 1.0 - (mean_saliency / 255.0)

        occlusion_score = 0.0
        if depth_norm is not None:
            margin = max(4, min(width, height) // 8)
            ox1 = max(0, x1 - margin)
            oy1 = max(0, y1 - margin)
            ox2 = min(img_w, x2 + margin)
            oy2 = min(img_h, y2 + margin)

            outside = depth_norm[oy1:oy2, ox1:ox2]
            outside_mask = np.ones(outside.shape, dtype=bool)
            outside_mask[y1 - oy1 : y2 - oy1, x1 - ox1 : x2 - ox1] = False
            outside_vals = outside[outside_mask]

            inside_mean = _safe_mean(depth_norm[y1:y2, x1:x2])
            outside_mean = float(np.mean(outside_vals)) if outside_vals.size > 0 else inside_mean
            occlusion_score = float(np.clip(outside_mean - inside_mean, 0.0, 1.0))

        combined_score = area_score + low_saliency_score + 0.8 * occlusion_score

        if combined_score > best_score:
            best_score = combined_score
            best_object = obj

            candidates = [
                ("br", x2 - batman_w, y2 - batman_h),
                ("bl", x1, y2 - batman_h),
                ("tr", x2 - batman_w, y1),
                ("tl", x1, y1),
            ]

            ranked = []
            for corner, cx, cy in candidates:
                cx = int(np.clip(cx, 0, max(0, img_w - batman_w)))
                cy = int(np.clip(cy, 0, max(0, img_h - batman_h)))
                if cx + batman_w <= img_w and cy + batman_h <= img_h:
                    local_occ = 0.0
                    if depth_norm is not None:
                        px = max(4, batman_w // 4)
                        py = max(4, batman_h // 4)
                        in_x1 = int(np.clip(cx, 0, img_w))
                        in_y1 = int(np.clip(cy, 0, img_h))
                        in_x2 = int(np.clip(cx + px, 0, img_w))
                        in_y2 = int(np.clip(cy + py, 0, img_h))
                        inside_patch = depth_norm[in_y1:in_y2, in_x1:in_x2]
                        inside_mean = _safe_mean(inside_patch)

                        dx = -px if corner.endswith("r") else px
                        dy = -py if corner.startswith("b") else py
                        out_x1 = int(np.clip(cx + dx, 0, img_w))
                        out_y1 = int(np.clip(cy + dy, 0, img_h))
                        out_x2 = int(np.clip(out_x1 + px, 0, img_w))
                        out_y2 = int(np.clip(out_y1 + py, 0, img_h))
                        outside_patch = depth_norm[out_y1:out_y2, out_x1:out_x2]
                        outside_mean = _safe_mean(outside_patch)
                        local_occ = float(np.clip(outside_mean - inside_mean, 0.0, 1.0))
                    ranked.append((local_occ, cx, cy))

            if ranked:
                ranked.sort(key=lambda item: item[0], reverse=True)
                _, hide_x, hide_y = ranked[0]
                best_location = (hide_x, hide_y)
            else:
                best_location = (0, 0)

    return best_object, best_location
