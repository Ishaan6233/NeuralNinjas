from argparse import ArgumentParser
from pathlib import Path

import cv2
import numpy as np

from src.detect import detect_objects
from src.pipeline import read_image, run_pipeline_on_image


ROOT = Path(__file__).resolve().parent


def _draw_debug(frame: np.ndarray, objects: list[dict], best_object: dict | None) -> None:
    for obj in objects:
        x1, y1, x2, y2 = obj["box"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (70, 70, 70), 1)
        cv2.putText(
            frame,
            obj["label"],
            (x1, max(12, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (70, 70, 70),
            1,
            cv2.LINE_AA,
        )
    if best_object is not None:
        x1, y1, x2, y2 = best_object["box"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)


def run_image_mode(args) -> int:
    image_path = Path(args.image) if args.image else ROOT / "batman_PNG13.png"
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 1

    frame = read_image(image_path)
    result = run_pipeline_on_image(
        frame=frame,
        sprites_folder=args.sprites,
        model_path=args.model,
        conf=args.conf,
        batman_size=(args.batman_w, args.batman_h),
    )
    rendered = result["rendered"]
    objects = result["objects"]
    best_object = result["best_object"]
    sprite_choice = result["sprite_choice"]
    if not objects:
        print("No objects detected.")
        cv2.imwrite(args.output, rendered)
        print(f"Saved: {args.output}")
        return 0
    if sprite_choice is not None:
        print(f"Sprite: {sprite_choice['path']}")
        print(f"Score: {sprite_choice['score']:.3f}")
    else:
        print("No valid sprite found in folder.")

    _draw_debug(rendered, objects, best_object)
    cv2.imwrite(args.output, rendered)
    print(f"Saved: {args.output}")
    return 0


def run_realtime_mode(args) -> int:
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Cannot open camera index {args.camera}")
        return 1

    smoothed_xy = None
    selected_sprite = None
    cached_objects = []
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_idx % args.detect_every == 0:
            cached_objects = detect_objects(frame, model_path=args.model, conf=args.conf)

        rendered = frame.copy()
        if cached_objects:
            result = run_pipeline_on_image(
                frame=frame,
                sprites_folder=args.sprites,
                model_path=args.model,
                conf=args.conf,
                batman_size=(args.batman_w, args.batman_h),
            )
            best_object = result["best_object"]
            sprite_choice = result["sprite_choice"]
            rendered = result["rendered"]
            if sprite_choice is not None:
                selected_sprite = sprite_choice
                tx, ty = sprite_choice["top_left"]
                if smoothed_xy is None:
                    smoothed_xy = (float(tx), float(ty))
                else:
                    sx, sy = smoothed_xy
                    smoothed_xy = (sx + 0.2 * (tx - sx), sy + 0.2 * (ty - sy))
            _draw_debug(rendered, result["objects"], best_object)

        cv2.putText(
            rendered,
            "Press q to quit",
            (10, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.imshow("Batman Hider (Realtime)", rendered)
        frame_idx += 1

        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


def main() -> int:
    parser = ArgumentParser(description="Integrated Batman hiding pipeline")
    parser.add_argument("--mode", choices=["image", "realtime"], default="image")
    parser.add_argument("--image", default=str(ROOT / "batman_PNG13.png"))
    parser.add_argument("--output", default="output.png")
    parser.add_argument("--sprites", default="batman_sprites")
    parser.add_argument("--model", default="yolov8n-seg.pt")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--batman-w", type=int, default=72)
    parser.add_argument("--batman-h", type=int, default=92)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--detect-every", type=int, default=5)
    args = parser.parse_args()

    if args.mode == "image":
        return run_image_mode(args)
    return run_realtime_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
