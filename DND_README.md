# D&D Campaign Generator 🎲

An AI-powered D&D campaign generator that creates rich, evolving campaigns from uploaded images using object detection and LLM generation.

## Features

- 📸 **Image Upload**: Upload images to seed campaign ideas
- 🤖 **Object Detection**: Uses YOLOv8 to detect objects in images
- ✨ **AI Campaign Generation**: Groq LLM creates complete D&D campaigns
- 📖 **Campaign Evolution**: Update campaigns with new images
- 💾 **Persistent Storage**: Campaigns saved as JSON files
- 🎨 **Beautiful UI**: Drag-and-drop interface with gradient design

## Generated Campaign Elements

Each campaign includes:
- **Title & Setting**: Evocative campaign name and world description
- **Story Hook**: Central conflict or mystery
- **NPCs**: 2-3 key characters with personalities
- **Locations**: Important places to explore
- **Quests**: Initial and evolving objectives
- **Encounters**: Combat and social encounters

## Installation

### 1. Install Dependencies

```bash
pip install -r dnd_requirements.txt
```

### 2. Get Groq API Key

1. Go to [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign up for a free account
3. Create an API key

### 3. Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="your-api-key-here"
```

**Windows (CMD):**
```cmd
set GROQ_API_KEY=your-api-key-here
```

**Linux/Mac:**
```bash
export GROQ_API_KEY="your-api-key-here"
```

## Usage

### 1. Start the Server

```bash
python main.py
```

The server will start at `http://localhost:5001`

**Note**: `main.py` checks for GROQ_API_KEY and provides helpful error messages if not set.

### 2. Open the Web Interface

Navigate to `http://localhost:5001` in your browser

### 3. Generate a Campaign

**Option A: Create New Campaign**
1. Drag & drop an image or click to browse
2. (Optional) Add description for context
3. Select "Create new campaign"
4. Click "Generate Campaign"

**Option B: Update Existing Campaign**
1. Upload a new image
2. Select "Update campaign"
3. Choose an existing campaign from dropdown
4. Click "Generate Campaign"

The AI will weave new objects into your existing story!

## Project Structure

```
├── main.py                    # Main entry point (run this!)
├── dnd_app.py                 # Flask API server
├── src/
│   ├── detect_objects.py       # YOLOv8 object detection
│   ├── campaign_generator.py   # Groq LLM integration
│   └── campaign_manager.py     # Campaign persistence
├── dnd-frontend/
│   ├── index.html              # Main UI with campaign browser
│   ├── styles.css              # Styling
│   └── script.js               # Frontend logic
├── campaigns/                  # Saved campaigns (JSON)
├── uploads/                    # Temporary uploads (auto-deleted)
└── dnd_requirements.txt       # Python dependencies
```

## API Endpoints

### `POST /api/upload`
Upload image and generate/update campaign

**Form Data:**
- `image`: Image file
- `campaign_id`: (optional) Existing campaign to update
- `description`: (optional) Image context

**Response:**
```json
{
  "campaign_id": "20240214_123456",
  "campaign": { /* campaign data */ },
  "objects": { "person": 2, "chair": 1 },
  "updated": false
}
```

### `GET /api/campaigns`
List all campaign IDs

### `GET /api/campaigns/<id>`
Get specific campaign data

## How It Works

1. **Image Upload**: User uploads an image via drag-and-drop
2. **Object Detection**: YOLOv8 detects and classifies objects
3. **Object Summary**: Creates count of detected objects
4. **LLM Generation**: Groq API (Llama 3.3 70B) generates campaign
5. **Storage**: Campaign saved as JSON with metadata
6. **Auto-Cleanup**: Uploaded image is automatically deleted after processing (saves space)
7. **Display**: Rich campaign rendered in UI

## Example Campaign Flow

**Upload 1**: Image of a forest with a deer
- Detected: tree, deer, grass
- Generated: "The Whispering Woods" - mysterious forest campaign

**Upload 2**: Image of a castle
- Detected: building, stone, tower
- Updated: Ancient castle discovered in the forest, new NPCs and quests added

## Technologies Used

- **Backend**: Flask (Python)
- **Object Detection**: YOLOv8 (Ultralytics)
- **LLM**: Groq API (Llama 3.3 70B)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Storage**: JSON files

## Configuration

### Change LLM Model

In `src/campaign_generator.py`:
```python
self.model = "llama-3.3-70b-versatile"  # Fast and creative
# Or use: "mixtral-8x7b-32768" for different style
```

### Adjust Object Detection Confidence

In `dnd_app.py`:
```python
detected_objects = detect_objects_for_campaign(
    str(filepath),
    conf=0.25  # Lower = more objects detected
)
```

## Troubleshooting

### "GROQ_API_KEY not found"
Make sure you've set the environment variable in your current terminal session.

### "No image displayed"
Check that uploads directory exists and has write permissions.

### "LLM response not JSON"
The model occasionally formats output incorrectly. The code handles markdown code blocks automatically.

## Future Enhancements

- [ ] Export campaigns as PDF
- [ ] Character sheet generation
- [ ] Map visualization
- [ ] Voice narration
- [ ] Multiplayer session management
- [ ] Integration with D&D Beyond

## License

MIT License - Feel free to use and modify!

## Credits

- **YOLOv8**: Ultralytics
- **LLM**: Groq (Meta Llama)
- **Icons**: Unicode emoji

---

Happy adventuring! 🐉
