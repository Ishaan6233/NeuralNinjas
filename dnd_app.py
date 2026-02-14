"""
Flask API for D&D Campaign Generator.
"""
import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pathlib import Path
import traceback

from src.detect_objects import detect_objects_for_campaign, get_object_summary
from src.campaign_generator import CampaignGenerator
from src.campaign_manager import CampaignManager


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}

# Initialize managers
campaign_manager = CampaignManager()
campaign_generator = None  # Initialize on first use (needs API key)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_generator():
    """Get or create campaign generator instance."""
    global campaign_generator
    if campaign_generator is None:
        campaign_generator = CampaignGenerator()
    return campaign_generator


@app.route('/')
def index():
    """Serve the frontend."""
    return send_from_directory('dnd-frontend', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    return send_from_directory('dnd-frontend', path)


@app.route('/api/upload', methods=['POST'])
def upload_image():
    """
    Upload an image and either create a new campaign or update an existing one.

    Form data:
        - image: Image file
        - campaign_id: (optional) Existing campaign ID to update
        - description: (optional) Text description of the image

    Returns:
        JSON with campaign data and ID
    """
    try:
        # Check if image was uploaded
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type"}), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        upload_dir = Path(app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(exist_ok=True)

        filepath = upload_dir / filename
        file.save(filepath)

        # Detect objects in the image
        detected_objects = detect_objects_for_campaign(str(filepath))
        object_summary = get_object_summary(detected_objects)

        print(f"[UPLOAD] Detected objects: {object_summary}")

        # Get optional parameters
        campaign_id = request.form.get('campaign_id')
        description = request.form.get('description', '')

        generator = get_generator()

        # Create new campaign or update existing
        if campaign_id and campaign_manager.campaign_exists(campaign_id):
            # Update existing campaign
            print(f"[UPLOAD] Updating campaign {campaign_id}")

            existing_campaign = campaign_manager.get_campaign(campaign_id)
            updated_campaign = generator.update_campaign(
                existing_campaign,
                object_summary,
                description
            )

            campaign_manager.update_campaign(campaign_id, updated_campaign)
            campaign_manager.add_image_to_campaign(campaign_id, str(filepath), object_summary)

            return jsonify({
                "campaign_id": campaign_id,
                "campaign": updated_campaign,
                "objects": object_summary,
                "updated": True
            })
        else:
            # Create new campaign
            print("[UPLOAD] Creating new campaign")

            campaign_data = generator.generate_initial_campaign(object_summary, description)
            campaign_id = campaign_manager.create_campaign(campaign_data)
            campaign_manager.add_image_to_campaign(campaign_id, str(filepath), object_summary)

            return jsonify({
                "campaign_id": campaign_id,
                "campaign": campaign_data,
                "objects": object_summary,
                "updated": False
            })

    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/campaigns', methods=['GET'])
def list_campaigns():
    """List all campaigns."""
    try:
        campaigns = campaign_manager.list_campaigns()
        return jsonify({"campaigns": campaigns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/campaigns/<campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    """Get a specific campaign by ID."""
    try:
        campaign = campaign_manager.get_campaign(campaign_id)

        if campaign is None:
            return jsonify({"error": "Campaign not found"}), 404

        return jsonify({"campaign": campaign})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Ensure GROQ_API_KEY is set
    if not os.getenv("GROQ_API_KEY"):
        print("WARNING: GROQ_API_KEY not set in environment variables")
        print("Get your free API key at: https://console.groq.com/keys")

    print("Starting D&D Campaign Generator...")
    print("Make sure to set GROQ_API_KEY environment variable")
    app.run(debug=True, host='0.0.0.0', port=5001)
