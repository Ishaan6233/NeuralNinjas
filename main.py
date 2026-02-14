import numpy as np

import cv2

from src.compose import choose_best_batman_sprite, overlay_sprite
from src.decision import decide_hiding_spot


def build_test_scene():
    """Create a synthetic image and detections for a quick smoke test."""
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    depth_map = np.full((240, 320), 0.45, dtype=np.float32)

    # Bright patch to simulate a salient region.
    image[40:90, 40:90] = 255

    objects = [
        {"label": "chair", "box": [20, 20, 160, 180], "mask": None},
        {"label": "table", "box": [170, 60, 300, 210], "mask": None},
        {"label": "lamp", "box": [30, 30, 70, 70], "mask": None},
    ]

    # Simulate depth: table is farther, with nearer context around it (occlusion-friendly).
    depth_map[60:210, 170:300] = 0.25
    depth_map[55:215, 165:305] = np.maximum(depth_map[55:215, 165:305], 0.75)

    batman_size = (48, 48)
    return image, objects, batman_size, depth_map


def main():
    image, objects, batman_size, depth_map = build_test_scene()
    best_object, (hide_x, hide_y) = decide_hiding_spot(image, objects, batman_size, depth_map)

    print("Decision test result")
    print("--------------------")
    if best_object is None:
        print("Best object: None")
    else:
        print(f"Best object label: {best_object['label']}")
        print(f"Best object box: {best_object['box']}")
    print(f"Hide coordinate: ({hide_x}, {hide_y})")

    sprite_choice = choose_best_batman_sprite(
        image=image,
        best_object=best_object,
        hide_xy=(hide_x, hide_y),
        sprite_folder="batman_sprites",
        depth_map=depth_map,
    )
    if sprite_choice is None:
        print("Best sprite: None (add PNGs to ./batman_sprites)")
    else:
        print(f"Best sprite path: {sprite_choice['path']}")
        print(f"Sprite score: {sprite_choice['score']:.3f}")
        print(f"Sprite fit ratio: {sprite_choice['fit_ratio']:.3f}")
        print(f"Sprite draw top-left: {sprite_choice['top_left']}")
        composed = overlay_sprite(
            image=image,
            sprite_path=sprite_choice["path"],
            top_left=sprite_choice["top_left"],
            size=sprite_choice["size"],
        )
        output_path = "output.png"
        cv2.imwrite(output_path, composed)
        print(f"Saved composed image: {output_path}")


if __name__ == "__main__":
    main()
