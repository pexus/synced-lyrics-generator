# Synced Lyrics Generator

A web-based tool to create, manage, and edit synchronized lyrics files (LRC and SRT) for audio tracks.

![Synced Lyrics Generator](https://i.imgur.com/2XbEXEh.png)

## Features

- Upload and manage audio files (MP3, WAV) with their corresponding lyrics
- Browser-based editing interface for creating synchronized lyrics
- Simple and intuitive UI for manually syncing lyrics with audio playback
- Generate both LRC and SRT format synchronized lyrics files
- View and download the generated files directly from the browser
- Mobile-friendly responsive design

## Prerequisites

- Python 3.6+
- Flask

## Installation

1. Clone the repository:
```bash
git clone https://github.com/pexus/synced-lyrics-generator.git
cd synced-lyrics-generator
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install the requirements:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

## Usage

### Uploading Songs

1. In the "Upload New Song" section, upload both an audio file (MP3/WAV) and its corresponding lyrics file (TXT)
2. Click "Upload Song" to add it to the library

### Adding Lyrics to Existing Songs

1. For songs without lyrics, click the "Browse/Upload Lyrics" button
2. Select a text file containing the lyrics for the song

### Creating Synchronized Lyrics

1. Click the "View/Edit" button for a song with lyrics
2. Play the audio using the play button
3. When a line starts playing, hold down the SPACEBAR
4. Release the SPACEBAR when the line ends
5. Continue this process for each line in the lyrics
6. The synchronized files (LRC and SRT) will be automatically saved when all lines are processed

### Viewing and Downloading

1. Click the "LRC" or "SRT" buttons to view the generated files
2. Use the "Download" button to save the files to your computer

## Project Structure

```
synced-lyrics-generator/
│
├── app.py                 # Flask application 
├── requirements.txt       # Python dependencies
│
├── static/                # Static files
│   └── audio/             # Audio files served to the browser
│
├── templates/             # HTML templates
│   ├── index.html         # Main page template
│   └── editor.html        # Lyrics editor template
│
├── audio_input/           # Original uploaded audio files
├── lyrics_input/          # Plain text lyrics files
├── lrc_output/            # Generated LRC files
└── srt_output/            # Generated SRT files
```

## Tips for Better Results

- Try to be as precise as possible when syncing lyrics
- If you make a mistake, press the DELETE key to go back one line
- To start over completely, click the "Reset" link in the editor
- For best results, use high-quality audio with clear vocals
- Format your lyrics file with one line per verse for easier syncing
- After syncing, you'll see a summary showing how many lines were successfully synced

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Development Process

This project was created using ["vibe coding"](https://en.wikipedia.org/wiki/Vibe_coding) with GitHub Copilot, leveraging various AI models available. Vibe coding embraces a collaborative approach between human and AI to create software through iterative, conversational development.

## Acknowledgments

- [WaveSurfer.js](https://wavesurfer-js.org/) for the audio waveform visualization
- Flask for the web framework
- GitHub Copilot for AI-assisted development

## Future Roadmap

This project is in active development. We will continue to add test cases and security controls as the project matures and include more automated technologies for synced lyrics generation as they become available.

See [FUTURE.md](FUTURE.md) for our planned enhancements and roadmap.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
