from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import logging
import time  # Added for time functions
from math import ceil

app = Flask(__name__)

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

def get_processed_files():
    if not os.path.exists(PROCESSED_FILES_DB):
        return set()
    with open(PROCESSED_FILES_DB, 'r') as f:
        return set(f.read().splitlines())

def add_to_processed_files(filename):
    with open(PROCESSED_FILES_DB, 'a') as f:
        f.write(filename + '\n')

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    processed_basenames = get_processed_files()
    all_audio_files = sorted([f for f in os.listdir(AUDIO_INPUT_FOLDER) if f.endswith(('.mp3', '.wav'))])
    lyrics_files_set = set(os.listdir(LYRICS_INPUT_FOLDER))

    total_songs = len(all_audio_files)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_audio_files = all_audio_files[start:end]

    all_audio_statuses = []
    for audio_file in paginated_audio_files:
        base_name = os.path.splitext(audio_file)[0]
        lyrics_file = base_name + '.txt'
        all_audio_statuses.append({
            'audio': audio_file,
            'basename': base_name,
            'lyrics': lyrics_file,
            'has_lyrics': lyrics_file in lyrics_files_set,
            'is_processed': base_name in processed_basenames
        })

    total_pages = ceil(total_songs / per_page)

    return render_template('index.html', 
                           all_audio_statuses=all_audio_statuses,
                           page=page,
                           total_pages=total_pages)

@app.route('/lyrics/<filename>')
def get_lyrics(filename):
    try:
        return send_from_directory(app.config['LYRICS_INPUT_FOLDER'], filename)
    except FileNotFoundError:
        return "File not found", 404

@app.route('/save_lyrics', methods=['POST'])
def save_lyrics():
    data = request.get_json()
    filename = data['filename']
    content = data['content']
    filepath = os.path.join(app.config['LYRICS_INPUT_FOLDER'], filename)
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        app.logger.debug("Upload request received")
        # Check if files are in the request
        if 'audio_file' not in request.files or 'lyrics_file' not in request.files:
            app.logger.error("Missing audio or lyrics files in request")
            return "Missing audio or lyrics files", 400
        
        audio_file = request.files['audio_file']
        lyrics_file = request.files['lyrics_file']
        
        if audio_file.filename == '' or lyrics_file.filename == '':
            app.logger.error("Empty filename in uploaded files")
            return "No files selected", 400
        
        # Check file types
        if not (audio_file.filename.lower().endswith(('.mp3', '.wav'))):
            app.logger.error(f"Invalid audio file type: {audio_file.filename}")
            return "Invalid audio file type. Please use MP3 or WAV files.", 400
            
        if not lyrics_file.filename.lower().endswith('.txt'):
            app.logger.error(f"Invalid lyrics file type: {lyrics_file.filename}")
            return "Invalid lyrics file type. Please use TXT files.", 400
        
        # Save audio file
        audio_path = os.path.join(app.config['AUDIO_INPUT_FOLDER'], audio_file.filename)
        audio_file.save(audio_path)
        app.logger.debug(f"Saved audio file to {audio_path}")
        
        # Get base name and save lyrics with matching name
        base_name = os.path.splitext(audio_file.filename)[0]
        lyrics_filename = base_name + '.txt'
        lyrics_path = os.path.join(app.config['LYRICS_INPUT_FOLDER'], lyrics_filename)
        lyrics_file.save(lyrics_path)
        app.logger.debug(f"Saved lyrics file to {lyrics_path}")
        
        app.logger.debug("File upload successful")
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error in upload_file: {str(e)}")
        return f"Error uploading files: {str(e)}", 500

@app.route('/upload_lyrics_for/<basename>', methods=['POST'])
def upload_lyrics_for(basename):
    if 'lyrics_file' in request.files:
        file = request.files['lyrics_file']
        if file.filename != '':
            lyrics_filename = basename + '.txt'
            file.save(os.path.join(app.config['LYRICS_INPUT_FOLDER'], lyrics_filename))
    return redirect(url_for('index'))

@app.route('/editor/<audio_file>/<lyrics_file>')
def editor(audio_file, lyrics_file):
    lyrics_path = os.path.join(LYRICS_INPUT_FOLDER, lyrics_file)
    if not os.path.exists(lyrics_path):
        # Handle case where lyrics file might be missing
        return "Lyrics file not found.", 404
    with open(lyrics_path, 'r') as f:
        lyrics_lines = f.read().splitlines()
    basename = os.path.splitext(audio_file)[0]
    return render_template('editor.html', audio_file=audio_file, lyrics_lines=lyrics_lines, lyrics_file=lyrics_file, basename=basename)

@app.route('/save_synced_lyrics', methods=['POST'])
def save_synced_lyrics():
    data = request.get_json()
    audio_file = data['audio_file']
    lyrics_data = data['lyrics_data']
    base_name = os.path.splitext(audio_file)[0]

    # Filter out entries with null timestamps
    valid_lyrics_data = [item for item in lyrics_data if item['time'] is not None]
    
    # Check if we have any valid lyrics with timestamps
    if not valid_lyrics_data:
        app.logger.warning(f"No valid timestamps found for {base_name}. Cannot create synced lyrics.")
        return {'status': 'error', 'message': 'No valid timestamps found. Please try syncing the lyrics again.'}

    # Generate and save LRC file
    lrc_content = ''
    for item in valid_lyrics_data:
        minutes = int(item['time'] / 60)
        seconds = int(item['time'] % 60)
        hundredths = int((item['time'] * 100) % 100)
        lrc_content += f'[{minutes:02d}:{seconds:02d}.{hundredths:02d}]{item["text"]}\n'
    
    lrc_path = os.path.join(LRC_OUTPUT_FOLDER, base_name + '.lrc')
    with open(lrc_path, 'w') as f:
        f.write(lrc_content)
    
    app.logger.debug(f"Saved LRC file for {base_name} with {len(valid_lyrics_data)} timestamps, size: {len(lrc_content)} bytes")

    # Generate and save SRT file
    srt_content = ''
    for i, item in enumerate(valid_lyrics_data):
        start_time = item['time']
        end_time = valid_lyrics_data[i+1]['time'] if i + 1 < len(valid_lyrics_data) else start_time + 2
        
        start_h, start_m, start_s, start_ms = int(start_time/3600), int(start_time/60)%60, int(start_time)%60, int(start_time*1000)%1000
        end_h, end_m, end_s, end_ms = int(end_time/3600), int(end_time/60)%60, int(end_time)%60, int(end_time*1000)%1000

        srt_content += f'{i+1}\n'
        srt_content += f'{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> {end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n'
        srt_content += f'{item["text"]}\n\n'

    srt_path = os.path.join(SRT_OUTPUT_FOLDER, base_name + '.srt')
    with open(srt_path, 'w') as f:
        f.write(srt_content)
    
    app.logger.debug(f"Saved SRT file for {base_name} with {len(valid_lyrics_data)} entries, size: {len(srt_content)} bytes")

    # Only mark as processed if we have actual content
    if lrc_content.strip() and srt_content.strip():
        add_to_processed_files(base_name)
        return {'status': 'success'}
    else:
        app.logger.error(f"Generated empty files for {base_name} despite having valid timestamps")
        return {'status': 'error', 'message': 'Generated files are empty. Please try again.'}

@app.route('/download_lrc/<basename>')
def download_lrc(basename):
    return send_from_directory(app.config['LRC_OUTPUT_FOLDER'], basename + '.lrc', as_attachment=True)

@app.route('/download_srt/<basename>')
def download_srt(basename):
    return send_from_directory(app.config['SRT_OUTPUT_FOLDER'], basename + '.srt', as_attachment=True)

@app.route('/view_lrc/<basename>')
def view_lrc(basename):
    try:
        app.logger.debug(f"Viewing LRC for {basename}")
        lrc_path = os.path.join(app.config['LRC_OUTPUT_FOLDER'], basename + '.lrc')
        
        if not os.path.exists(lrc_path):
            app.logger.error(f"LRC file not found: {lrc_path}")
            return f"LRC file not found for {basename}", 404
        
        with open(lrc_path, 'r') as f:
            content = f.read()
        
        app.logger.debug(f"Successfully read LRC file, size: {len(content)} bytes")
        
        # Add CORS headers to ensure the browser doesn't block the response
        response_headers = {
            'Content-Type': 'text/plain; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        return content, 200, response_headers
    except Exception as e:
        app.logger.error(f"Error in view_lrc: {str(e)}")
        return f"Error: {str(e)}", 500, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/view_srt/<basename>')
def view_srt(basename):
    try:
        app.logger.debug(f"Viewing SRT for {basename}")
        srt_path = os.path.join(app.config['SRT_OUTPUT_FOLDER'], basename + '.srt')
        
        if not os.path.exists(srt_path):
            app.logger.error(f"SRT file not found: {srt_path}")
            return f"SRT file not found for {basename}", 404
        
        with open(srt_path, 'r') as f:
            content = f.read()
        
        app.logger.debug(f"Successfully read SRT file, size: {len(content)} bytes")
        
        # Add CORS headers to ensure the browser doesn't block the response
        response_headers = {
            'Content-Type': 'text/plain; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        return content, 200, response_headers
    except Exception as e:
        app.logger.error(f"Error in view_srt: {str(e)}")
        return f"Error: {str(e)}", 500, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/delete_song/<basename>', methods=['DELETE'])
def delete_song(basename):
    try:
        # Find and delete files, ignoring errors if they don't exist
        audio_file = os.path.join(app.config['AUDIO_INPUT_FOLDER'], basename + '.mp3')
        if not os.path.exists(audio_file):
            audio_file = os.path.join(app.config['AUDIO_INPUT_FOLDER'], basename + '.wav')
        if os.path.exists(audio_file):
            os.remove(audio_file)

        lyrics_file = os.path.join(app.config['LYRICS_INPUT_FOLDER'], basename + '.txt')
        if os.path.exists(lyrics_file):
            os.remove(lyrics_file)

        lrc_file = os.path.join(app.config['LRC_OUTPUT_FOLDER'], basename + '.lrc')
        if os.path.exists(lrc_file):
            os.remove(lrc_file)

        srt_file = os.path.join(app.config['SRT_OUTPUT_FOLDER'], basename + '.srt')
        if os.path.exists(srt_file):
            os.remove(srt_file)

        # Remove from processed list
        processed_files = get_processed_files()
        if basename in processed_files:
            processed_files.remove(basename)
            with open(PROCESSED_FILES_DB, 'w') as f:
                for item in processed_files:
                    f.write(item + '\n')

        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(app.config['AUDIO_INPUT_FOLDER'], filename)

@app.route('/debug/lrc/<basename>')
def debug_lrc(basename):
    """A simple debug endpoint that shows LRC content directly in browser"""
    try:
        app.logger.debug(f"Debug viewing LRC for {basename}")
        lrc_path = os.path.join(app.config['LRC_OUTPUT_FOLDER'], basename + '.lrc')
        
        if not os.path.exists(lrc_path):
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>LRC Error for {basename}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                    .error {{ color: red; background: #ffeeee; padding: 15px; border: 1px solid #ffcccc; }}
                    .btn {{ display: inline-block; margin-top: 20px; padding: 10px 15px;
                           background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <h1>LRC Error</h1>
                <div class="error">
                    <p>The LRC file for <strong>{basename}</strong> was not found.</p>
                    <p>Please generate the LRC file first using the editor.</p>
                </div>
                <a class="btn" href="/">Back to home</a>
            </body>
            </html>
            """, 404
        
        with open(lrc_path, 'r') as f:
            content = f.read()
        
        # Check if the file is empty
        if not content.strip():
            stats = os.stat(lrc_path)
            file_size = stats.st_size
            created_time = stats.st_ctime
            modified_time = stats.st_mtime
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Empty LRC File for {basename}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                    .warning {{ color: #856404; background: #fff3cd; padding: 15px; border: 1px solid #ffeeba; margin-bottom: 20px; }}
                    .file-info {{ background: #f8f9fa; padding: 15px; border: 1px solid #ddd; margin-bottom: 20px; }}
                    .btn {{ display: inline-block; margin-top: 10px; margin-right: 10px; padding: 10px 15px;
                           background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                    .btn-warning {{ background: #ffc107; }}
                </style>
            </head>
            <body>
                <h1>LRC File for {basename}</h1>
                <div class="warning">
                    <h2>⚠️ Empty File Warning</h2>
                    <p>The LRC file exists but appears to be empty (no content).</p>
                    <p>This usually happens if the synced lyrics were not properly generated or saved.</p>
                </div>
                <div class="file-info">
                    <h2>File Information:</h2>
                    <ul>
                        <li><strong>File size:</strong> {file_size} bytes</li>
                        <li><strong>Created:</strong> {time.ctime(created_time)}</li>
                        <li><strong>Last modified:</strong> {time.ctime(modified_time)}</li>
                        <li><strong>Path:</strong> {lrc_path}</li>
                    </ul>
                </div>
                <div>
                    <h2>Suggested Actions:</h2>
                    <p>You should re-generate the synced lyrics for this song:</p>
                    <a class="btn" href="/">Back to home</a>
                    <a class="btn btn-warning" href="/editor/{basename}.mp3/{basename}.txt">Re-generate Synced Lyrics</a>
                    <a class="btn" href="/download_lrc/{basename}" download="{basename}.lrc">Download Empty LRC File</a>
                </div>
            </body>
            </html>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LRC Content for {basename}</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h1 {{ color: #333; }}
                pre {{ background: #f5f5f5; padding: 10px; border: 1px solid #ddd; overflow-x: auto; line-height: 1.5; }}
                .download {{ display: inline-block; margin-top: 20px; margin-right: 10px; padding: 10px 15px;
                           background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                .back {{ color: #007bff; display: inline-block; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1>LRC Content for {basename}</h1>
            <pre>{content}</pre>
            <a class="download" href="/download_lrc/{basename}" download="{basename}.lrc">Download LRC</a>
            <a class="download" style="background: #28a745;" href="/">Back to home</a>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        app.logger.error(f"Error in debug_lrc: {str(e)}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                .error {{ color: red; background: #ffeeee; padding: 15px; border: 1px solid #ffcccc; }}
                pre {{ background: #f5f5f5; padding: 10px; border: 1px solid #ddd; overflow-x: auto; }}
                .btn {{ display: inline-block; margin-top: 20px; padding: 10px 15px;
                       background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>Error</h1>
            <div class="error">An error occurred while trying to display the LRC file:</div>
            <pre>{str(e)}</pre>
            <a class="btn" href="/">Back to home</a>
        </body>
        </html>
        """, 500

@app.route('/debug/srt/<basename>')
def debug_srt(basename):
    """A simple debug endpoint that shows SRT content directly in browser"""
    try:
        app.logger.debug(f"Debug viewing SRT for {basename}")
        srt_path = os.path.join(app.config['SRT_OUTPUT_FOLDER'], basename + '.srt')
        
        if not os.path.exists(srt_path):
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>SRT Error for {basename}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                    .error {{ color: red; background: #ffeeee; padding: 15px; border: 1px solid #ffcccc; }}
                    .btn {{ display: inline-block; margin-top: 20px; padding: 10px 15px;
                           background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <h1>SRT Error</h1>
                <div class="error">
                    <p>The SRT file for <strong>{basename}</strong> was not found.</p>
                    <p>Please generate the SRT file first using the editor.</p>
                </div>
                <a class="btn" href="/">Back to home</a>
            </body>
            </html>
            """, 404
        
        with open(srt_path, 'r') as f:
            content = f.read()
        
        # Check if the file is empty
        if not content.strip():
            stats = os.stat(srt_path)
            file_size = stats.st_size
            created_time = stats.st_ctime
            modified_time = stats.st_mtime
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Empty SRT File for {basename}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                    .warning {{ color: #856404; background: #fff3cd; padding: 15px; border: 1px solid #ffeeba; margin-bottom: 20px; }}
                    .file-info {{ background: #f8f9fa; padding: 15px; border: 1px solid #ddd; margin-bottom: 20px; }}
                    .btn {{ display: inline-block; margin-top: 10px; margin-right: 10px; padding: 10px 15px;
                           background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                    .btn-warning {{ background: #ffc107; }}
                </style>
            </head>
            <body>
                <h1>SRT File for {basename}</h1>
                <div class="warning">
                    <h2>⚠️ Empty File Warning</h2>
                    <p>The SRT file exists but appears to be empty (no content).</p>
                    <p>This usually happens if the synced lyrics were not properly generated or saved.</p>
                </div>
                <div class="file-info">
                    <h2>File Information:</h2>
                    <ul>
                        <li><strong>File size:</strong> {file_size} bytes</li>
                        <li><strong>Created:</strong> {time.ctime(created_time)}</li>
                        <li><strong>Last modified:</strong> {time.ctime(modified_time)}</li>
                        <li><strong>Path:</strong> {srt_path}</li>
                    </ul>
                </div>
                <div>
                    <h2>Suggested Actions:</h2>
                    <p>You should re-generate the synced lyrics for this song:</p>
                    <a class="btn" href="/">Back to home</a>
                    <a class="btn btn-warning" href="/editor/{basename}.mp3/{basename}.txt">Re-generate Synced Lyrics</a>
                    <a class="btn" href="/download_srt/{basename}" download="{basename}.srt">Download Empty SRT File</a>
                </div>
            </body>
            </html>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SRT Content for {basename}</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h1 {{ color: #333; }}
                pre {{ background: #f5f5f5; padding: 10px; border: 1px solid #ddd; overflow-x: auto; line-height: 1.5; }}
                .download {{ display: inline-block; margin-top: 20px; margin-right: 10px; padding: 10px 15px;
                           background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                .back {{ color: #007bff; display: inline-block; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1>SRT Content for {basename}</h1>
            <pre>{content}</pre>
            <a class="download" href="/download_srt/{basename}" download="{basename}.srt">Download SRT</a>
            <a class="download" style="background: #28a745;" href="/">Back to home</a>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        app.logger.error(f"Error in debug_srt: {str(e)}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                .error {{ color: red; background: #ffeeee; padding: 15px; border: 1px solid #ffcccc; }}
                pre {{ background: #f5f5f5; padding: 10px; border: 1px solid #ddd; overflow-x: auto; }}
                .btn {{ display: inline-block; margin-top: 20px; padding: 10px 15px;
                       background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>Error</h1>
            <div class="error">An error occurred while trying to display the SRT file:</div>
            <pre>{str(e)}</pre>
            <a class="btn" href="/">Back to home</a>
        </body>
        </html>
        """, 500

if __name__ == '__main__':
    app.run(debug=True)
