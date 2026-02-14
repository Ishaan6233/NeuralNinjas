"""Run YOLOv8 segmentation on an image (Batman by default)."""

from pathlib import Path
import sys

# Ensure we import the project modules from ./src
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.detect import detect_objects  # noqa: E402


def main() -> int:
    # Allow an optional CLI argument; fall back to the provided living room image.
    default_image = Path(r"C:\Users\melri\OneDrive\Desktop\NeuralNinjas\living_room.jpeg")
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_image
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 1

    objects = detect_objects(str(image_path))

    if not objects:
        print("No objects detected.")
        return 0

    for obj in objects:
        mask_shape = obj["mask"].shape if obj["mask"] is not None else None
        print(
            f"{obj['label']}: box={obj['box']}, mask_shape={mask_shape}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
