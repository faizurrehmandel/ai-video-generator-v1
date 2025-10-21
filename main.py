```python
# main.py

# --- Standard Library Imports ---
import os
import uuid
import logging

# --- Third-Party Imports ---
from flask import Flask, request, jsonify, url_for
from flask_cors import CORS
from dotenv import load_dotenv

# --- Local Application/Library Specific Imports ---
# These are placeholder imports. In a real project, these modules would
# contain the logic for interacting with their respective services.
# e.g., 'services/gemini_client.py', 'services/video_creator.py', etc.
try:
    from services import gemini_client
    from services import elevenlabs_client
    from services import pexels_client
    from services import video_creator
except ImportError:
    # This block allows the app to run even if the service modules are not yet created.
    # In a real scenario, these modules must be implemented.
    print("Warning: Service modules (gemini, elevenlabs, pexels, video_creator) not found. Using mock functions.")
    from utils import mock_services
    gemini_client = mock_services
    elevenlabs_client = mock_services
    pexels_client = mock_services
    video_creator = mock_services


# ==============================================================================
# INITIALIZATION & CONFIGURATION
# ==============================================================================

# Load environment variables from a .env file for security and configuration.
load_dotenv()

# Configure logging to provide visibility into the application's operations.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
)

# Initialize the Flask application.
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS) to allow the frontend
# hosted on a different domain to interact with this API.
CORS(app)

# Define and create necessary directories for storing generated files.
# Using 'exist_ok=True' prevents an error if the directories already exist.
VIDEO_DIR = os.path.join('static', 'videos')
TEMP_DIR = os.path.join('static', 'temp')
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def cleanup_temp_files(file_paths):
    """
    Deletes a list of temporary files generated during the video creation process.
    This is crucial for managing disk space.

    Args:
        file_paths (list): A list of absolute paths to the files to be deleted.
    """
    logging.info(f"Attempting to clean up {len(file_paths)} temporary files.")
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logging.info(f"Successfully cleaned up temp file: {os.path.basename(path)}")
        except OSError as e:
            logging.error(f"Error cleaning up file {path}: {e}")


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.route('/api/generate', methods=['POST'])
def generate_video_endpoint():
    """
    The main API endpoint for generating a video. It orchestrates the entire
    process from script generation to final video assembly.

    Request Body (JSON):
        {
            "topic": "The history of the Roman Empire"
        }

    Returns:
        JSON response with either a link to the generated video or an error message.
    """
    # 1. --- Input Validation ---
    if not request.is_json:
        return jsonify({"success": False, "error": "Invalid input: Request body must be JSON"}), 400

    data = request.get_json()
    topic = data.get('topic')

    if not topic or not isinstance(topic, str) or len(topic.strip()) < 3:
        return jsonify({"success": False, "error": "'topic' is required and must be a non-empty string"}), 400

    # Generate a unique ID for this request to avoid filename conflicts.
    request_id = str(uuid.uuid4())
    logging.info(f"[{request_id}] Received video generation request for topic: '{topic}'")

    temp_files_to_clean = []

    try:
        # 2. --- AI Script Generation (Gemini) ---
        logging.info(f"[{request_id}] Generating script from topic...")
        script_scenes = gemini_client.generate_script_from_topic(topic)
        if not script_scenes or not isinstance(script_scenes, list):
            raise ValueError("Failed to generate a valid script. The result was empty or malformed.")
        logging.info(f"[{request_id}] Script generated with {len(script_scenes)} scenes.")

        # 3. --- Asset Generation (Voiceover & Footage) for each scene ---
        scene_assets = []
        for i, scene in enumerate(script_scenes):
            scene_num = i + 1
            logging.info(f"[{request_id}] Processing scene {scene_num}/{len(script_scenes)}...")

            # --- Voiceover Synthesis (ElevenLabs) ---
            narration_text = scene.get('narration')
            audio_path = None
            if narration_text:
                audio_filename = f"{request_id}_scene_{scene_num}.mp3"
                audio_path = os.path.join(TEMP_DIR, audio_filename)
                elevenlabs_client.generate_and_save_audio(narration_text, audio_path)
                temp_files_to_clean.append(audio_path)
                logging.info(f"[{request_id}] Generated audio for scene {scene_num}.")
            else:
                logging.warning(f"[{request_id}] Scene {scene_num} has no narration. Skipping audio generation.")

            # --- Stock Footage Sourcing (Pexels) ---
            keywords = scene.get('keywords')
            if not keywords:
                raise ValueError(f"Script for scene {scene_num} is missing 'keywords'.")

            video_filename = f"{request_id}_scene_{scene_num}.mp4"
            video_path = os.path.join(TEMP_DIR, video_filename)
            pexels_client.download_video_for_keywords(keywords, video_path)
            temp_files_to_clean.append(video_path)
            logging.info(f"[{request_id}] Downloaded video for scene {scene_num}.")

            scene_assets.append({"video_path": video_path, "audio_path": audio_path})

        # 4. --- Video Assembly (moviepy) ---
        logging.info(f"[{request_id}] Assembling final video from {len(scene_assets)} scenes...")
        output_filename = f"{request_id}.mp4"
        output_video_path = os.path.join(VIDEO_DIR, output_filename)

        video_creator.assemble_video(scene_assets, output_video_path)
        logging.info(f"[{request_id}] Final video successfully created: {output_video_path}")

        # 5. --- Generate Response ---
        # Create a public-facing URL for the generated video.
        final_video_url = url_for('static', filename=f'videos/{output_filename}', _external=True)

        return jsonify({
            "success": True,
            "message": "Video generated successfully!",
            "video_url": final_video_url
        }), 201  # 201 Created is a more appropriate status code for successful resource creation.

    except Exception as e:
        # Catch-all for any errors during the process for robust error handling.
        logging.error(f"[{request_id}] An error occurred during video generation: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An internal server error occurred. Please check the logs for details."
        }), 500

    finally:
        # 6. --- Cleanup ---
        # This block ensures that temporary files are deleted regardless of
        # whether the process succeeded or failed.
        if temp_files_to_clean:
            cleanup_temp_files(temp_files_to_clean)


@app.route('/')
def index():
    """
    A simple root endpoint to confirm that the API is running.
    """
    return "<h1>AI Video Generator API</h1><p>The API is up and running. Use the /api/generate endpoint to create a video.</p>"


# ==============================================================================
# APPLICATION ENTRY POINT
# ==============================================================================

if __name__ == '__main__':
    # Get port from environment variables or default to 5000
    port = int(os.environ.get("PORT", 5000))
    # Run the Flask app. 'host="0.0.0.0"' makes it accessible on the local network.
    # 'debug=True' is suitable for development but should be 'False' in production.
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1'])
```