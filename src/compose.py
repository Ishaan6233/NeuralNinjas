from pathlib import Path

import cv2
import numpy as np


def _compute_saliency_map(image: np.ndarray) -> np.ndarray:
    try:
        saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
        ok, saliency_map = saliency.computeSaliency(image)
        if ok and saliency_map is not None:
            return (saliency_map * 255).astype(np.uint8)
    except AttributeError:
        pass

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(grad_x, grad_y)
    saliency_map = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    if saliency_map is None:
        return np.zeros(image.shape[:2], dtype=np.uint8)
    return saliency_map.astype(np.uint8)


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
    object_mask = best_object.get("mask") if isinstance(best_object, dict) else None
    has_object_mask = (
        isinstance(object_mask, np.ndarray) and object_mask.shape[:2] == (img_h, img_w)
    )
    box_area = float(box_w * box_h)
    saliency_map = _compute_saliency_map(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edge_band = np.abs(cv2.Laplacian(gray, cv2.CV_32F))

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

        # Slight oversize encourages partial occlusion near object boundaries.
        resized = _resize_sprite(sprite, int(box_w * 1.2), int(box_h * 1.2))
        if resized is None:
            continue

        mask = _alpha_mask(resized)
        mask_px = int(np.count_nonzero(mask))
        if mask_px == 0:
            continue

        sh, sw = resized.shape[:2]
        hx, hy = hide_xy
        offsets = [-0.35, -0.2, 0.0, 0.2, 0.35]
        anchors = [
            (hx, hy),
            (x1 - int(0.3 * sw), y1 - int(0.3 * sh)),
            (x2 - int(0.8 * sw), y1 - int(0.3 * sh)),
            (x1 - int(0.3 * sw), y2 - int(0.8 * sh)),
            (x2 - int(0.8 * sw), y2 - int(0.8 * sh)),
        ]

        for ax, ay in anchors:
            for ox in offsets:
                for oy in offsets:
                    draw_x = int(np.clip(ax + ox * sw, 0, max(0, img_w - sw)))
                    draw_y = int(np.clip(ay + oy * sh, 0, max(0, img_h - sh)))
                    sx1, sy1, sx2, sy2 = draw_x, draw_y, draw_x + sw, draw_y + sh

                    yy, xx = np.where(mask)
                    abs_x = xx + draw_x
                    abs_y = yy + draw_y

                    in_object = (abs_x >= x1) & (abs_x < x2) & (abs_y >= y1) & (abs_y < y2)
                    fit_ratio = float(np.count_nonzero(in_object)) / mask_px
                    coverage = float(mask_px) / box_area
                    partial_visibility_score = 0.4
                    visible_ratio = 1.0
                    visible_selector = np.ones_like(abs_x, dtype=bool)
                    if has_object_mask:
                        occluded = object_mask[abs_y, abs_x]
                        visible_selector = ~occluded
                        visible_ratio = float(np.count_nonzero(visible_selector)) / mask_px
                        partial_visibility_score = 1.0 - min(abs(visible_ratio - 0.33) / 0.33, 1.0)
                    if np.count_nonzero(visible_selector) == 0:
                        continue

                    vis_x = abs_x[visible_selector]
                    vis_y = abs_y[visible_selector]
                    sal_vals = saliency_map[vis_y, vis_x]
                    low_saliency_score = 1.0 - float(np.mean(sal_vals)) / 255.0

                    edge_mag = edge_band[vis_y, vis_x]
                    clutter_score = float(np.clip(np.mean(edge_mag) / 32.0, 0.0, 1.0))

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

                    score = (
                        0.8 * fit_ratio
                        + 0.5 * coverage
                        + 1.25 * low_saliency_score
                        + 0.8 * occlusion_score
                        + 1.5 * partial_visibility_score
                        + 0.9 * clutter_score
                    )

                    candidate = {
                        "path": str(sprite_path),
                        "score": score,
                        "top_left": (draw_x, draw_y),
                        "size": (sw, sh),
                        "fit_ratio": fit_ratio,
                        "coverage": coverage,
                        "visible_ratio": visible_ratio,
                        "partial_visibility_score": partial_visibility_score,
                        "low_saliency_score": low_saliency_score,
                        "occlusion_score": occlusion_score,
                        "clutter_score": clutter_score,
                    }
                    if best is None or candidate["score"] > best["score"]:
                        best = candidate

    return best


def overlay_sprite(
    image: np.ndarray,
    sprite_path: str,
    top_left: tuple[int, int],
    size: tuple[int, int],
    object_mask: np.ndarray | None = None,
    saliency_map: np.ndarray | None = None,
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

    # Feather sprite boundary so cut edges are less obvious.
    sigma = max(0.8, min(sw, sh) / 42.0)
    alpha = cv2.GaussianBlur(alpha, (0, 0), sigmaX=sigma, sigmaY=sigma)
    if alpha.ndim == 2:
        alpha = alpha[:, :, None]

    # Use object mask as foreground occluder so Batman appears behind object.
    if object_mask is not None and object_mask.shape[:2] == (img_h, img_w):
        obj_crop = object_mask[y:y2, x:x2].astype(np.float32)
        alpha *= (1.0 - obj_crop[:, :, None])

    # Color harmonization with local background to avoid "sticker look".
    alpha_2d = alpha[:, :, 0] > 0.03
    if np.any(alpha_2d):
        fg_mean = fg[alpha_2d].mean(axis=0)
        bg_mean = roi.astype(np.float32)[alpha_2d].mean(axis=0)
        shift = (bg_mean - fg_mean) * 0.55
        fg = np.clip(fg + shift, 0, 255)
        gray = np.mean(fg, axis=2, keepdims=True)
        fg = np.clip(0.82 * fg + 0.18 * gray, 0, 255)

    bg = roi.astype(np.float32)
    out = fg * alpha + bg * (1.0 - alpha)
    base[y:y2, x:x2] = out.astype(np.uint8)
    return base
