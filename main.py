"""
Main entry point for D&D Campaign Generator.

This is the file you run to start the application.
"""
import os
import sys

# Check for GROQ_API_KEY
if not os.getenv("GROQ_API_KEY"):
    print("=" * 60)
    print("⚠️  ERROR: GROQ_API_KEY not set!")
    print("=" * 60)
    print("\nPlease set your Groq API key:")
    print("\nPowerShell:")
    print('  $env:GROQ_API_KEY="your-api-key-here"')
    print("\nLinux/Mac:")
    print('  export GROQ_API_KEY="your-api-key-here"')
    print("\nGet your free API key at: https://console.groq.com/keys")
    print("=" * 60)
    sys.exit(1)

# Import and run the Flask app
from dnd_app import app

if __name__ == '__main__':
    print("=" * 60)
    print("🎲 D&D Campaign Generator")
    print("=" * 60)
    print("\n✅ GROQ_API_KEY is set")
    print("🚀 Starting server at http://localhost:5001")
    print("\n📖 Features:")
    print("  - Upload images to generate campaigns")
    print("  - Browse and view existing campaigns")
    print("  - Update campaigns with new images")
    print("  - Images auto-deleted after processing")
    print("\n🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    app.run(debug=True, host='0.0.0.0', port=5001)
