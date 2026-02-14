import cv2
import numpy as np


def _normalize_depth(depth_map: np.ndarray) -> np.ndarray:
    """Scale a depth map to [0,1]; only used if a depth_map is provided."""
    depth = depth_map.astype(np.float32)
    min_val = float(np.min(depth))
    max_val = float(np.max(depth))
    if max_val <= min_val:
        return np.zeros_like(depth, dtype=np.float32)
    return (depth - min_val) / (max_val - min_val)


def _safe_mean(region: np.ndarray) -> float:
    """Mean that won't NaN on empty slices; returns 0.0 if region is empty."""
    return float(np.mean(region)) if region.size > 0 else 0.0


def _object_mask_potential(obj: dict, img_h: int, img_w: int) -> float:
    """
    Estimate how well an object's shape could hide Batman.
    - Requires a full-image mask aligned to (img_h, img_w).
    - Scores irregular edges (Canny density) and a medium fill ratio.
    """
    mask = obj.get("mask")
    if not isinstance(mask, np.ndarray) or mask.shape[:2] != (img_h, img_w):
        return 0.0
    x1, y1, x2, y2 = obj["box"]
    crop = mask[y1:y2, x1:x2]
    if crop.size == 0:
        return 0.0
    mask_u8 = (crop.astype(np.uint8) * 255)
    edge = cv2.Canny(mask_u8, 64, 128)
    edge_density = float(np.count_nonzero(edge)) / float(edge.size)
    fill_ratio = float(np.count_nonzero(crop)) / float(crop.size)
    # Best hiding occluders are irregular edges with moderate fill.
    fill_score = 1.0 - min(abs(fill_ratio - 0.55) / 0.55, 1.0)
    return 0.7 * edge_density + 0.3 * fill_score


def _compute_saliency_map(image: np.ndarray) -> np.ndarray:
    """
    Clutter/contrast map via local standard deviation.
    High values = busy/edgy regions; low values = smooth areas.
    We prefer low-saliency regions for hiding, so this steers Batman toward smoother occluders.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)

    k = 11  # window size; tune 7–21 depending on texture scale
    mean = cv2.boxFilter(gray, ddepth=-1, ksize=(k, k))
    mean_sq = cv2.boxFilter(gray * gray, ddepth=-1, ksize=(k, k))
    var = cv2.max(mean_sq - mean * mean, 0)
    std = cv2.sqrt(var)

    saliency_map = cv2.normalize(std, None, 0, 255, cv2.NORM_MINMAX)
    return saliency_map.astype(np.uint8) if saliency_map is not None else np.zeros_like(gray, dtype=np.uint8)


def decide_hiding_spot(
    image: np.ndarray,
    objects: list,
    batman_size: tuple,
    depth_map: np.ndarray | None = None,
    return_debug: bool = False,
    random_jitter: float = 0.35,
    rng: np.random.Generator | None = None,
):
    """
    image: full input image as a numpy array
    objects: list of dicts with keys "label", "box", "mask"
    batman_size: tuple (width, height) of the Batman sprite
    random_jitter: stddev of Gaussian noise added to break ties/stochastic placement
    rng: optional numpy Generator (for reproducibility)
    returns: (best_object, (hide_x, hide_y))
    """
    if image is None or image.size == 0:
        raise ValueError("image must be a non-empty numpy array")
    if not objects:
        raise ValueError("objects list cannot be empty")

    rng = rng or np.random.default_rng()
    img_h, img_w = image.shape[:2]
    batman_w, batman_h = batman_size

    saliency_map = _compute_saliency_map(image)

    image_area = float(img_w * img_h)
    depth_norm = None
    if depth_map is not None:
        if depth_map.shape[:2] != (img_h, img_w):
            raise ValueError("depth_map must have same height/width as image")
        depth_norm = _normalize_depth(depth_map)

    best_score = float("-inf")
    best_object = None
    best_location = (0, 0)
    best_debug = {}

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
        norm_sal = mean_saliency / 255.0
        target = 0.4  # prefer medium-low contrast, not the absolute smoothest
        low_saliency_score = 1.0 - min(abs(norm_sal - target) / target, 1.0)
        mask_potential = _object_mask_potential(obj, img_h, img_w)

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

        combined_score = (
            (0.20 * area_score)
            + (0.40 * low_saliency_score)
            + (1.10 * occlusion_score)
            + (1.00 * mask_potential)
        )
        # Add small noise to avoid deterministic ties / repeated placement.
        if random_jitter > 0:
            combined_score += float(rng.normal(0.0, random_jitter))

        if combined_score > best_score:
            best_score = combined_score
            best_object = obj

            # Sample multiple anchors across the box (corners, edges, center) with jitter.
            anchors = [
                (0.05, 0.05), (0.5, 0.5), (0.95, 0.95),
                (0.05, 0.95), (0.95, 0.05), (0.5, 0.1),
                (0.5, 0.9), (0.1, 0.5), (0.9, 0.5)
            ]
            ranked = []
            for fx, fy in anchors:
                cx = int(x1 + fx * width - batman_w * 0.5)
                cy = int(y1 + fy * height - batman_h * 0.5)
                if random_jitter > 0:
                    cx += int(rng.normal(0, batman_w * 0.15))
                    cy += int(rng.normal(0, batman_h * 0.15))
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

                        out_x1 = int(np.clip(cx - px, 0, img_w))
                        out_y1 = int(np.clip(cy - py, 0, img_h))
                        out_x2 = int(np.clip(cx + batman_w + px, 0, img_w))
                        out_y2 = int(np.clip(cy + batman_h + py, 0, img_h))
                        outside_patch = depth_norm[out_y1:out_y2, out_x1:out_x2]
                        outside_mask = np.ones(outside_patch.shape, dtype=bool)
                        inside_w = in_x2 - in_x1
                        inside_h = in_y2 - in_y1
                        outside_mask[
                            (cy - out_y1) : (cy - out_y1 + inside_h),
                            (cx - out_x1) : (cx - out_x1 + inside_w),
                        ] = False
                        outside_vals = outside_patch[outside_mask]
                        outside_mean = float(np.mean(outside_vals)) if outside_vals.size > 0 else inside_mean
                        local_occ = float(np.clip(outside_mean - inside_mean, 0.0, 1.0))
                    if random_jitter > 0:
                        local_occ += float(rng.normal(0.0, random_jitter))
                    ranked.append((local_occ, cx, cy))

            if ranked:
                ranked.sort(key=lambda item: item[0], reverse=True)
                _, hide_x, hide_y = ranked[0]
                best_location = (hide_x, hide_y)
            else:
                best_location = (0, 0)
            best_debug = {
                "area_score": area_score,
                "low_saliency_score": low_saliency_score,
                "occlusion_score": occlusion_score,
                "mask_potential": mask_potential,
                "combined_score": combined_score,
            }

    if return_debug:
        return best_object, best_location, best_debug
    return best_object, best_location
