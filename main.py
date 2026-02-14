import numpy as np

from src.decision import decide_hiding_spot


def build_test_scene():
    """Create a synthetic image and detections for a quick smoke test."""
    image = np.zeros((240, 320, 3), dtype=np.uint8)

    # Bright patch to simulate a salient region.
    image[40:90, 40:90] = 255

    objects = [
        {"label": "chair", "box": [20, 20, 160, 180], "mask": None},
        {"label": "table", "box": [170, 60, 300, 210], "mask": None},
        {"label": "lamp", "box": [30, 30, 70, 70], "mask": None},
    ]

    batman_size = (48, 48)
    return image, objects, batman_size


def main():
    image, objects, batman_size = build_test_scene()
    best_object, (hide_x, hide_y) = decide_hiding_spot(image, objects, batman_size)

    print("Decision test result")
    print("--------------------")
    if best_object is None:
        print("Best object: None")
    else:
        print(f"Best object label: {best_object['label']}")
        print(f"Best object box: {best_object['box']}")
    print(f"Hide coordinate: ({hide_x}, {hide_y})")


if __name__ == "__main__":
    main()
