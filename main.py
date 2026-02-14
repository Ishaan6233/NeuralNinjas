"""Run YOLOv8 segmentation on an image and visualize masks."""

from pathlib import Path
import sys
from typing import Tuple

import cv2
import numpy as np

# Ensure we import the project modules from ./src
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.detect import detect_objects  # noqa: E402


def _color_for_label(label: str) -> Tuple[int, int, int]:
    """Deterministic BGR color for a label."""
    seed = abs(hash(label)) % (2**32)
    rng = np.random.default_rng(seed)
    return tuple(int(c) for c in rng.integers(0, 255, size=3))  # B, G, R


def main() -> int:
    # Allow an optional CLI argument; fall back to the provided living room image.
    default_image = Path(r"C:\Users\melri\OneDrive\Desktop\NeuralNinjas\living_room.jpeg")
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_image
    output_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else image_path.with_name(f"{image_path.stem}_segmented.png")
    )
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 1

    objects = detect_objects(str(image_path))

    if not objects:
        print("No objects detected.")
        return 0

    # Visualize masks and boxes
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Could not read image for visualization: {image_path}")
        return 1
    overlay = image.copy()

    for obj in objects:
        mask_shape = obj["mask"].shape if obj["mask"] is not None else None
        print(f"{obj['label']}: box={obj['box']}, mask_shape={mask_shape}")

        color = _color_for_label(obj["label"])
        if obj["mask"] is not None:
            mask = obj["mask"].astype(bool)
            overlay[mask] = color  # fill mask
        # Draw bounding box and label
        x1, y1, x2, y2 = obj["box"]
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            image,
            obj["label"],
            (x1, max(y1 - 5, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    # Blend overlay (masks) with original
    blended = cv2.addWeighted(image, 0.6, overlay, 0.4, 0)
    cv2.imwrite(str(output_path), blended)
    print(f"Saved visualization to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
