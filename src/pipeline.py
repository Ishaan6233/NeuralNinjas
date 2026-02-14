from pathlib import Path

import cv2
import numpy as np

from src.compose import choose_best_batman_sprite, overlay_sprite
from src.decision import decide_hiding_spot
from src.detect import detect_objects
from src.depth import estimate_depth_map


def run_pipeline_on_image(
    frame: np.ndarray,
    sprites_folder: str = "batman_sprites",
    model_path: str = "yolov8n-seg.pt",
    conf: float = 0.25,
    batman_size: tuple[int, int] = (72, 92),
    use_midas: bool = True,
    random_jitter: float = 0.25,
) -> dict:
    """Core pipeline: YOLO -> hide spot -> sprite overlay. Depth optional."""
    objects = detect_objects(frame, model_path=model_path, conf=conf)
    if not objects:
        return {
            "rendered": frame.copy(),
            "objects": [],
            "best_object": None,
            "hide_xy": None,
            "sprite_choice": None,
            "batman_center_xy": None,
            "reason": None,
        }

    depth_map = None
    if use_midas:
        try:
            depth_map = estimate_depth_map(frame)
        except Exception:
            depth_map = None

    # Fresh RNG per call to encourage different placements across runs.
    rng = np.random.default_rng()

    best_object, hide_xy, hide_debug = decide_hiding_spot(
        image=frame,
        objects=objects,
        batman_size=batman_size,
        depth_map=depth_map,
        return_debug=True,
        random_jitter=random_jitter,
        rng=rng,
    )
    sprite_choice = choose_best_batman_sprite(
        image=frame,
        best_object=best_object,
        hide_xy=hide_xy,
        sprite_folder=sprites_folder,
        depth_map=depth_map,
    )

    rendered = frame.copy()
    batman_center_xy = None
    if sprite_choice is not None:
        rendered = overlay_sprite(
            image=rendered,
            sprite_path=sprite_choice["path"],
            top_left=sprite_choice["top_left"],
            size=sprite_choice["size"],
            object_mask=None if best_object is None else best_object.get("mask"),
        )
        x, y = sprite_choice["top_left"]
        w, h = sprite_choice["size"]
        batman_center_xy = (x + w // 2, y + h // 2)
    elif hide_xy is not None:
        batman_center_xy = hide_xy

    return {
        "rendered": rendered,
        "objects": objects,
        "best_object": best_object,
        "hide_xy": hide_xy,
        "sprite_choice": sprite_choice,
        "batman_center_xy": batman_center_xy,
        "reason": {
            "decision": hide_debug,
            "sprite": None
            if sprite_choice is None
            else {
                "visible_ratio": sprite_choice.get("visible_ratio"),
                "low_saliency_score": sprite_choice.get("low_saliency_score"),
                "partial_visibility_score": sprite_choice.get("partial_visibility_score"),
                "clutter_score": sprite_choice.get("clutter_score"),
            },
        },
    }


def read_image(image_path: str | Path) -> np.ndarray:
    frame = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if frame is None:
        raise FileNotFoundError(f"Could not decode image: {image_path}")
    return frame
