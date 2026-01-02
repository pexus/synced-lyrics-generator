import re
from difflib import SequenceMatcher

try:
    from unidecode import unidecode
except ImportError:
    unidecode = None


MIN_FUZZY_TOKEN_LENGTH = 4
MIN_FUZZY_RATIO = 0.78


def normalize_token(token):
    token = token.strip().lower()
    token = token.replace("\u2019", "'").replace("\u2018", "'")
    if unidecode:
        token = unidecode(token)
    token = re.sub(r"[^\w']+", "", token, flags=re.UNICODE)
    return token


def tokens_match(token, candidate):
    if token == candidate:
        return True
    if not token or not candidate:
        return False
    if len(token) < MIN_FUZZY_TOKEN_LENGTH or len(candidate) < MIN_FUZZY_TOKEN_LENGTH:
        return False
    if abs(len(token) - len(candidate)) > 3:
        return False
    ratio = SequenceMatcher(None, token, candidate).ratio()
    return ratio >= MIN_FUZZY_RATIO


def find_token_index(token, transcript_tokens, start_idx, end_idx_limit):
    for idx in range(start_idx, end_idx_limit):
        if transcript_tokens[idx] == token:
            return idx
    for idx in range(start_idx, end_idx_limit):
        if tokens_match(token, transcript_tokens[idx]):
            return idx
    return None


def tokenize_line(line):
    raw_tokens = re.findall(r"[\w']+", line, flags=re.UNICODE)
    tokens = []
    for token in raw_tokens:
        normalized = normalize_token(token)
        if normalized:
            tokens.append(normalized)
    return tokens


def tokenize_lines(lines):
    tokens = []
    line_spans = []

    for line in lines:
        line_tokens = tokenize_line(line)
        start = len(tokens)
        tokens.extend(line_tokens)
        end = len(tokens) - 1
        line_spans.append((start, end))

    return tokens, line_spans


def find_line_match(
    line_tokens,
    transcript_tokens,
    transcript_words,
    start_idx,
    max_window_seconds=90,
    min_required=None,
):
    if not line_tokens or start_idx >= len(transcript_tokens) or not transcript_words:
        return None

    start_time = transcript_words[start_idx]['start']
    end_idx_limit = len(transcript_tokens)
    for idx in range(start_idx, len(transcript_words)):
        if transcript_words[idx]['start'] - start_time > max_window_seconds:
            end_idx_limit = idx
            break

    matched_indices = []
    t_idx = start_idx
    for token in line_tokens:
        found_idx = find_token_index(token, transcript_tokens, t_idx, end_idx_limit)
        if found_idx is None:
            continue
        matched_indices.append(found_idx)
        t_idx = found_idx + 1
        if t_idx >= end_idx_limit:
            break

    if min_required is None:
        min_required = 1 if len(line_tokens) < 3 else 2
    if len(matched_indices) >= min_required:
        return matched_indices[0], matched_indices[-1]

    return None


def align_sequences(lyrics_tokens, transcript_tokens, match_score=2, mismatch_score=-1, gap_score=-1):
    n = len(lyrics_tokens)
    m = len(transcript_tokens)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = i * gap_score
        back[i][0] = 'up'
    for j in range(1, m + 1):
        dp[0][j] = j * gap_score
        back[0][j] = 'left'

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diag = dp[i - 1][j - 1] + (
                match_score if lyrics_tokens[i - 1] == transcript_tokens[j - 1] else mismatch_score
            )
            up = dp[i - 1][j] + gap_score
            left = dp[i][j - 1] + gap_score

            best = max(diag, up, left)
            dp[i][j] = best
            if best == diag:
                back[i][j] = 'diag'
            elif best == up:
                back[i][j] = 'up'
            else:
                back[i][j] = 'left'

    alignment = [None] * n
    match_flags = [False] * n

    i = n
    j = m
    while i > 0 or j > 0:
        direction = back[i][j]
        if direction == 'diag':
            i -= 1
            j -= 1
            alignment[i] = j
            if lyrics_tokens[i] == transcript_tokens[j]:
                match_flags[i] = True
        elif direction == 'up':
            i -= 1
        elif direction == 'left':
            j -= 1
        else:
            break

    return alignment, match_flags


def interpolate_missing_times(times, max_gap_lines=3):
    if not times:
        return []

    filled = list(times)
    known_indices = [index for index, value in enumerate(filled) if value is not None]

    if not known_indices:
        return [None for _ in filled]

    for index in range(1, len(known_indices)):
        prev_index = known_indices[index - 1]
        current_index = known_indices[index]
        if filled[current_index] < filled[prev_index]:
            filled[current_index] = filled[prev_index]

    for index in range(1, len(known_indices)):
        start_index = known_indices[index - 1]
        end_index = known_indices[index]
        gap = end_index - start_index
        if gap > 1:
            missing = gap - 1
            if max_gap_lines is not None and missing > max_gap_lines:
                continue
            start = filled[start_index]
            end = filled[end_index]
            step = (end - start) / gap
            for offset in range(1, gap):
                filled[start_index + offset] = start + step * offset

    return filled


def _build_line_timings(lines, transcript_words, max_window_seconds, min_required):
    transcript_tokens = [normalize_token(word['word']) for word in transcript_words]

    line_times = []
    line_end_times = []
    cursor_idx = 0
    matched_lines = 0
    for line in lines:
        line_tokens = tokenize_line(line)
        if not line_tokens:
            line_times.append(None)
            line_end_times.append(None)
            continue

        match = find_line_match(
            line_tokens,
            transcript_tokens,
            transcript_words,
            cursor_idx,
            max_window_seconds=max_window_seconds,
            min_required=min_required,
        )
        if not match:
            line_times.append(None)
            line_end_times.append(None)
            continue

        first_match, last_match = match
        line_times.append(transcript_words[first_match]['start'])
        line_end_times.append(transcript_words[last_match]['end'])
        cursor_idx = last_match + 1
        matched_lines += 1

    line_times = interpolate_missing_times(line_times, max_gap_lines=3)
    adjusted_end_times = []
    for index, end_time in enumerate(line_end_times):
        start_time = line_times[index]
        if start_time is None:
            adjusted_end_times.append(None)
            continue
        if end_time is None or end_time < start_time:
            adjusted_end_times.append(None)
            continue
        adjusted_end_times.append(end_time)

    timings = [
        {
            'time': line_times[index],
            'end_time': adjusted_end_times[index],
        }
        for index in range(len(line_times))
    ]
    return timings, matched_lines


def build_line_timings(lines, transcript_words):
    timings, matched = _build_line_timings(
        lines,
        transcript_words,
        max_window_seconds=90,
        min_required=None,
    )
    if matched == 0:
        timings, _ = _build_line_timings(
            lines,
            transcript_words,
            max_window_seconds=180,
            min_required=1,
        )
    return timings
