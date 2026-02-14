from pathlib import Path
from uuid import uuid4

import cv2
from flask import Flask, jsonify, request, send_from_directory

from src.pipeline import read_image, run_pipeline_on_image


ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "uploads"
OUTPUT_DIR = ROOT / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="front-end", static_url_path="/")


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/outputs/<path:filename>")
def outputs(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


@app.post("/api/process")
def process_upload():
    if "image" not in request.files:
        return jsonify({"error": "missing image upload field"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "empty filename"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return jsonify({"error": "unsupported image format"}), 400

    uid = uuid4().hex
    upload_path = UPLOAD_DIR / f"{uid}{ext}"
    output_name = f"{uid}_output.png"
    output_path = OUTPUT_DIR / output_name
    file.save(upload_path)

    frame = read_image(upload_path)
    result = run_pipeline_on_image(
        frame=frame,
        sprites_folder="batman_sprites",
        model_path="yolov8n-seg.pt",
        conf=0.25,
        batman_size=(72, 92),
    )
    cv2.imwrite(str(output_path), result["rendered"])

    h, w = frame.shape[:2]
    center = result["batman_center_xy"]
    if center is None:
        center = (w // 2, h // 2)
    reason = result.get("reason")

    return jsonify(
        {
            "output_image_url": f"/outputs/{output_name}",
            "batman": {
                "x_norm": center[0] / max(1, w),
                "y_norm": center[1] / max(1, h),
                "radius": 42,
            },
            "objects_detected": len(result["objects"]),
            "best_object": None if result["best_object"] is None else result["best_object"]["label"],
            "reason": reason,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
