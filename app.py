from flask import Flask
from routes import register_blueprints
import logging
import os
import datetime

app = Flask(__name__)

# Register the file_exists Jinja filter
@app.template_filter('file_exists')
def file_exists_filter(filename, folder):
    filepath = os.path.join(folder, filename)
    return os.path.exists(filepath) and os.path.getsize(filepath) > 0

# Register the timestamp_to_datetime Jinja filter
@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# Configuration
AUDIO_INPUT_FOLDER = 'audio_input'
LYRICS_INPUT_FOLDER = 'lyrics_input'
LRC_OUTPUT_FOLDER = 'lrc_output'
SRT_OUTPUT_FOLDER = 'srt_output'
PROCESSED_FILES_DB = 'processed_files.txt'

app.config['AUDIO_INPUT_FOLDER'] = AUDIO_INPUT_FOLDER
app.config['LYRICS_INPUT_FOLDER'] = LYRICS_INPUT_FOLDER
app.config['LRC_OUTPUT_FOLDER'] = LRC_OUTPUT_FOLDER
app.config['SRT_OUTPUT_FOLDER'] = SRT_OUTPUT_FOLDER

# Create folders if they don't exist
for folder in [AUDIO_INPUT_FOLDER, LYRICS_INPUT_FOLDER, LRC_OUTPUT_FOLDER, SRT_OUTPUT_FOLDER, os.path.join('static', 'audio')]:
    if not os.path.exists(folder):
        os.makedirs(folder)

register_blueprints(app)

if __name__ == '__main__':
    app.run(debug=True)
