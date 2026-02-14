from pathlib import Path

import cv2
import numpy as np


def _compute_saliency_map(image: np.ndarray) -> np.ndarray:
    saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
    ok, saliency_map = saliency.computeSaliency(image)
    if not ok or saliency_map is None:
        return np.zeros(image.shape[:2], dtype=np.uint8)
    return (saliency_map * 255).astype(np.uint8)


def _alpha_mask(sprite: np.ndarray) -> np.ndarray:
    if sprite.ndim == 3 and sprite.shape[2] == 4:
        return sprite[:, :, 3] > 0
    gray = cv2.cvtColor(sprite, cv2.COLOR_BGR2GRAY)
    return gray > 10


def _resize_sprite(sprite: np.ndarray, max_w: int, max_h: int) -> np.ndarray | None:
    h, w = sprite.shape[:2]
    if h <= 0 or w <= 0 or max_w <= 0 or max_h <= 0:
        return None
    scale = min(max_w / w, max_h / h)
    scale = max(scale, 1e-3)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(sprite, (new_w, new_h), interpolation=cv2.INTER_AREA)


def choose_best_batman_sprite(
    image: np.ndarray,
    best_object: dict,
    hide_xy: tuple[int, int],
    sprite_folder: str,
    depth_map: np.ndarray | None = None,
) -> dict | None:
    """
    Pick the sprite that best fits the hiding location.
    Uses sprite alpha as segmentation and scores fit + visibility.
    """
    if image is None or image.size == 0:
        raise ValueError("image must be non-empty")
    if best_object is None:
        return None

    img_h, img_w = image.shape[:2]
    x1, y1, x2, y2 = best_object["box"]
    x1 = int(np.clip(x1, 0, img_w - 1))
    y1 = int(np.clip(y1, 0, img_h - 1))
    x2 = int(np.clip(x2, 1, img_w))
    y2 = int(np.clip(y2, 1, img_h))
    if x2 <= x1 or y2 <= y1:
        return None

    box_w = x2 - x1
    box_h = y2 - y1
    box_area = float(box_w * box_h)
    saliency_map = _compute_saliency_map(image)

    depth_norm = None
    if depth_map is not None:
        if depth_map.shape[:2] != (img_h, img_w):
            raise ValueError("depth_map must match image height/width")
        d = depth_map.astype(np.float32)
        d_min, d_max = float(np.min(d)), float(np.max(d))
        depth_norm = np.zeros_like(d) if d_max <= d_min else (d - d_min) / (d_max - d_min)

    folder = Path(sprite_folder)
    if not folder.exists():
        return None

    best = None
    for sprite_path in sorted(folder.glob("*.png")):
        sprite = cv2.imread(str(sprite_path), cv2.IMREAD_UNCHANGED)
        if sprite is None:
            continue

        resized = _resize_sprite(sprite, box_w, box_h)
        if resized is None:
            continue

        mask = _alpha_mask(resized)
        mask_px = int(np.count_nonzero(mask))
        if mask_px == 0:
            continue

        sh, sw = resized.shape[:2]
        hx, hy = hide_xy
        draw_x = int(np.clip(hx, 0, max(0, img_w - sw)))
        draw_y = int(np.clip(hy, 0, max(0, img_h - sh)))
        sx1, sy1, sx2, sy2 = draw_x, draw_y, draw_x + sw, draw_y + sh

        yy, xx = np.where(mask)
        abs_x = xx + draw_x
        abs_y = yy + draw_y

        in_object = (abs_x >= x1) & (abs_x < x2) & (abs_y >= y1) & (abs_y < y2)
        fit_ratio = float(np.count_nonzero(in_object)) / mask_px
        coverage = float(mask_px) / box_area

        sal_vals = saliency_map[abs_y, abs_x]
        low_saliency_score = 1.0 - float(np.mean(sal_vals)) / 255.0

        occlusion_score = 0.0
        if depth_norm is not None:
            inside_depth = depth_norm[abs_y, abs_x]
            inside_mean = float(np.mean(inside_depth)) if inside_depth.size > 0 else 0.0
            margin = max(3, min(sw, sh) // 8)
            ox1 = max(0, sx1 - margin)
            oy1 = max(0, sy1 - margin)
            ox2 = min(img_w, sx2 + margin)
            oy2 = min(img_h, sy2 + margin)
            ring = depth_norm[oy1:oy2, ox1:ox2]
            ring_mask = np.ones(ring.shape, dtype=bool)
            ring_mask[sy1 - oy1 : sy2 - oy1, sx1 - ox1 : sx2 - ox1] = False
            ring_vals = ring[ring_mask]
            outside_mean = float(np.mean(ring_vals)) if ring_vals.size > 0 else inside_mean
            occlusion_score = float(np.clip(outside_mean - inside_mean, 0.0, 1.0))

        score = 1.4 * fit_ratio + 0.6 * coverage + 1.0 * low_saliency_score + 0.8 * occlusion_score

        candidate = {
            "path": str(sprite_path),
            "score": score,
            "top_left": (draw_x, draw_y),
            "size": (sw, sh),
            "fit_ratio": fit_ratio,
            "coverage": coverage,
            "low_saliency_score": low_saliency_score,
            "occlusion_score": occlusion_score,
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate

    return best


def overlay_sprite(
    image: np.ndarray, sprite_path: str, top_left: tuple[int, int], size: tuple[int, int]
) -> np.ndarray:
    """Overlay a PNG sprite onto an image using alpha blending."""
    if image is None or image.size == 0:
        raise ValueError("image must be non-empty")

    base = image.copy()
    img_h, img_w = base.shape[:2]
    sprite = cv2.imread(sprite_path, cv2.IMREAD_UNCHANGED)
    if sprite is None:
        raise ValueError(f"could not load sprite: {sprite_path}")

    sw, sh = size
    if sw <= 0 or sh <= 0:
        raise ValueError("size must be positive")

    sprite = cv2.resize(sprite, (sw, sh), interpolation=cv2.INTER_AREA)
    x, y = top_left
    x = int(np.clip(x, 0, img_w - 1))
    y = int(np.clip(y, 0, img_h - 1))
    x2 = int(np.clip(x + sw, 0, img_w))
    y2 = int(np.clip(y + sh, 0, img_h))
    if x2 <= x or y2 <= y:
        return base

    sprite = sprite[: y2 - y, : x2 - x]
    roi = base[y:y2, x:x2]

    if sprite.ndim == 3 and sprite.shape[2] == 4:
        fg = sprite[:, :, :3].astype(np.float32)
        alpha = (sprite[:, :, 3:4].astype(np.float32)) / 255.0
    else:
        fg = sprite[:, :, :3].astype(np.float32)
        alpha = np.ones((fg.shape[0], fg.shape[1], 1), dtype=np.float32)

    bg = roi.astype(np.float32)
    out = fg * alpha + bg * (1.0 - alpha)
    base[y:y2, x:x2] = out.astype(np.uint8)
    return base
