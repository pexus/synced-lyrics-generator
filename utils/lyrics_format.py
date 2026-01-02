def normalize_lyrics_data(lyrics_data):
    normalized = []
    for item in lyrics_data or []:
        if item.get('time') is None:
            continue
        normalized_item = {
            'text': item.get('text', ''),
            'time': float(item['time']),
        }
        if item.get('end_time') is not None:
            normalized_item['end_time'] = float(item['end_time'])
        normalized.append(normalized_item)
    return normalized


def build_lrc_content(lyrics_data):
    valid_lyrics_data = normalize_lyrics_data(lyrics_data)
    lrc_content = ''
    for item in valid_lyrics_data:
        minutes = int(item['time'] / 60)
        seconds = int(item['time'] % 60)
        hundredths = int((item['time'] * 100) % 100)
        lrc_content += f'[{minutes:02d}:{seconds:02d}.{hundredths:02d}]{item["text"]}\n'
    return lrc_content


def build_srt_content(lyrics_data):
    valid_lyrics_data = normalize_lyrics_data(lyrics_data)
    srt_content = ''
    for i, item in enumerate(valid_lyrics_data):
        start_time = item['time']
        end_time = item.get('end_time')
        if end_time is None:
            end_time = (
                valid_lyrics_data[i + 1]['time']
                if i + 1 < len(valid_lyrics_data)
                else start_time + 2
            )
        if end_time < start_time:
            end_time = start_time + 0.1
        start_h = int(start_time / 3600)
        start_m = int(start_time / 60) % 60
        start_s = int(start_time) % 60
        start_ms = int(start_time * 1000) % 1000
        end_h = int(end_time / 3600)
        end_m = int(end_time / 60) % 60
        end_s = int(end_time) % 60
        end_ms = int(end_time * 1000) % 1000
        srt_content += (
            f'{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} '
            f'--> {end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n'
        )
        srt_content += f'{item["text"]}\n\n'
    return srt_content


def ensure_srt_indices(srt_content):
    if not srt_content:
        return srt_content
    lines = srt_content.splitlines()
    first_non_empty = None
    for line in lines:
        if line.strip():
            first_non_empty = line.strip()
            break
    if first_non_empty and first_non_empty.isdigit():
        return srt_content
    blocks = []
    current = []
    for line in lines:
        if line.strip() == '':
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    numbered_lines = []
    for index, block in enumerate(blocks, start=1):
        numbered_lines.append(str(index))
        numbered_lines.extend(block)
        numbered_lines.append('')
    return '\n'.join(numbered_lines).rstrip() + '\n'


def parse_srt_timestamp(timestamp):
    if not timestamp:
        return None
    normalized = timestamp.replace(',', '.')
    parts = normalized.split(':')
    if len(parts) != 3:
        return None
    seconds_part = parts[2].split('.')
    if len(seconds_part) != 2:
        return None
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(seconds_part[0])
        milliseconds = int(seconds_part[1])
    except ValueError:
        return None
    return (hours * 3600) + (minutes * 60) + seconds + (milliseconds / 1000.0)


def parse_srt_content(srt_content):
    if not srt_content:
        return []
    lines = srt_content.splitlines()
    cues = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        if line.isdigit():
            idx += 1
            if idx >= len(lines):
                break
            line = lines[idx].strip()
        if '-->' not in line:
            idx += 1
            continue
        parts = line.split('-->')
        if len(parts) < 2:
            idx += 1
            continue
        start = parse_srt_timestamp(parts[0].strip())
        end = parse_srt_timestamp(parts[1].strip())
        idx += 1
        text_lines = []
        while idx < len(lines) and lines[idx].strip():
            text_lines.append(lines[idx].strip())
            idx += 1
        text = ' '.join(text_lines).strip()
        cues.append({
            'start': start,
            'end': end,
            'text': text,
        })
    return cues
