# Contributing to Synced Lyrics Generator

Thank you for considering contributing to the Synced Lyrics Generator project! Here's how you can help.

## How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

## Development Setup

1. Clone the repository
2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
3. Run the application:
```bash
python app.py
```

## Project Structure

- `app.py` - Main Flask application
- `templates/` - HTML templates
- `static/` - Static assets
- `audio_input/` - Uploaded audio files
- `lyrics_input/` - Uploaded lyrics files
- `lrc_output/` - Generated LRC files
- `srt_output/` - Generated SRT files

## Code Style

- Follow PEP 8 guidelines for Python code
- Use 4 spaces for indentation

## Testing

- Test your changes thoroughly before submitting a pull request

## Pull Request Process

1. Ensure your code is well-tested and doesn't break existing functionality
2. Update the README.md with details of changes if applicable
3. Your pull request will be reviewed by maintainers, who may request changes
4. Once approved, your pull request will be merged

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
