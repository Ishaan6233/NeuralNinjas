"""CLI: detect objects in an image and generate a story with an LLM."""

from pathlib import Path
import sys
import os

from dotenv import load_dotenv

from src.detect import detect_objects
from src.story import generate_story


def main() -> int:
    load_dotenv()
    if len(sys.argv) < 2:
        print("Usage: python story_from_image.py <image_path> [extra_note]")
        return 1

    image_path = Path(sys.argv[1])
    extra = sys.argv[2] if len(sys.argv) > 2 else None
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 1

    hf_model = os.getenv("HF_MODEL", "HuggingFaceH4/zephyr-7b-beta")

    objects = detect_objects(str(image_path))
    print(f"Detected {len(objects)} objects")
    story = generate_story(
        objects,
        extra_note=extra,
        provider="huggingface",  # use HF Inference API client
        hf_model=hf_model,
    )
    print("\n--- Story ---")
    print(story)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
