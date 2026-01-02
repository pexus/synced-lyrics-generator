import glob
import os
import shutil
import subprocess
import tempfile

import requests
from flask import current_app


class TranscriptionError(Exception):
    pass


MAX_OPENAI_UPLOAD_BYTES = 25 * 1024 * 1024


def _require_ffmpeg():
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise TranscriptionError(
            'ffmpeg is required to split large audio files. Please install ffmpeg.'
        )


def _get_duration_seconds(audio_path):
    result = subprocess.run(
        [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise TranscriptionError(f'ffprobe failed: {result.stderr.strip()}')
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise TranscriptionError('Unable to parse audio duration from ffprobe.') from exc


def _split_audio(audio_path, segment_seconds=600):
    _require_ffmpeg()

    temp_dir = tempfile.TemporaryDirectory()
    output_pattern = os.path.join(temp_dir.name, 'segment_%03d.mp3')

    cmd = [
        'ffmpeg',
        '-y',
        '-i', audio_path,
        '-ac', '1',
        '-ar', '16000',
        '-b:a', '96k',
        '-f', 'segment',
        '-segment_time', str(segment_seconds),
        '-reset_timestamps', '1',
        output_pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        temp_dir.cleanup()
        raise TranscriptionError(f'ffmpeg failed to split audio: {result.stderr.strip()}')

    segment_paths = sorted(glob.glob(os.path.join(temp_dir.name, 'segment_*.mp3')))
    if not segment_paths:
        temp_dir.cleanup()
        raise TranscriptionError('ffmpeg did not produce any audio segments.')

    return temp_dir, segment_paths


def _transcribe_file(audio_path, prompt=None, timeout_seconds=120):
    api_key = current_app.config.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise TranscriptionError('OPENAI_API_KEY is not set.')

    with open(audio_path, 'rb') as audio_file:
        files = {
            'file': (os.path.basename(audio_path), audio_file),
        }
        data = {
            'model': 'whisper-1',
            'response_format': 'verbose_json',
            'timestamp_granularities[]': 'word',
        }
        if prompt:
            data['prompt'] = prompt

        headers = {
            'Authorization': f'Bearer {api_key}',
        }

        try:
            response = requests.post(
                'https://api.openai.com/v1/audio/transcriptions',
                headers=headers,
                data=data,
                files=files,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise TranscriptionError(f'OpenAI transcription request failed: {exc}') from exc

    if response.status_code != 200:
        raise TranscriptionError(
            f'OpenAI transcription failed with status {response.status_code}: {response.text}'
        )

    return response.json()


def transcribe_audio(audio_path, prompt=None, timeout_seconds=120):
    file_size = os.path.getsize(audio_path)
    if file_size <= MAX_OPENAI_UPLOAD_BYTES:
        return _transcribe_file(audio_path, prompt=prompt, timeout_seconds=timeout_seconds)

    temp_dir, segment_paths = _split_audio(audio_path)
    try:
        merged_words = []
        offset = 0.0

        for index, segment_path in enumerate(segment_paths):
            segment_prompt = prompt if index == 0 else None
            result = _transcribe_file(
                segment_path,
                prompt=segment_prompt,
                timeout_seconds=timeout_seconds,
            )
            segment_words = extract_word_timings(result)
            for word in segment_words:
                merged_words.append({
                    'word': word['word'],
                    'start': word['start'] + offset,
                    'end': word['end'] + offset,
                })

            offset += _get_duration_seconds(segment_path)

        return {'words': merged_words}
    finally:
        temp_dir.cleanup()


def extract_word_timings(transcription):
    words = []

    if isinstance(transcription, dict) and transcription.get('words'):
        words = transcription['words']
    else:
        for segment in transcription.get('segments', []):
            segment_words = segment.get('words', [])
            if segment_words:
                words.extend(segment_words)

    normalized = []
    for word in words:
        text = word.get('word') or word.get('text')
        start = word.get('start')
        end = word.get('end')
        if text is None or start is None or end is None:
            continue
        normalized.append({
            'word': str(text),
            'start': float(start),
            'end': float(end),
        })

    return normalized
