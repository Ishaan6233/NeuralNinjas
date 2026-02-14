"""Monocular depth estimation using MiDaS via torch hub."""

from functools import lru_cache
from typing import Tuple

import cv2
import numpy as np
import torch


@lru_cache(maxsize=1)
def _load_midas(model_type: str = "DPT_Hybrid") -> Tuple[torch.nn.Module, object]:
    """
    Load MiDaS and its preprocessing transform.
    model_type options: "DPT_Large", "DPT_Hybrid", "MiDaS_small".
    """
    midas = torch.hub.load("intel-isl/MiDaS", model_type)
    midas.eval()
    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    transform = (
        midas_transforms.dpt_transform
        if model_type.startswith("DPT")
        else midas_transforms.small_transform
    )
    return midas, transform


def estimate_depth_map(
    frame_bgr: np.ndarray,
    model_type: str = "DPT_Hybrid",
    device: str | None = None,
) -> np.ndarray:
    """
    Returns depth normalized to [0,1] with shape (H, W).
    """
    if frame_bgr is None or frame_bgr.size == 0:
        raise ValueError("frame_bgr must be non-empty")

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    midas, transform = _load_midas(model_type)
    midas.to(device)

    img_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    input_batch = transform(img_rgb).to(device)

    with torch.no_grad():
        prediction = midas(input_batch)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img_rgb.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()

    depth = prediction.cpu().numpy().astype(np.float32)
    d_min, d_max = float(depth.min()), float(depth.max())
    if d_max <= d_min:
        return np.zeros_like(depth, dtype=np.float32)
    return (depth - d_min) / (d_max - d_min)
