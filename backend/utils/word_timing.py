"""Word timings from Kokoro's per-phoneme durations, aligned to whitespace words."""
import re

# Kokoro keeps these marks in its phoneme stream; they carry pauses, not speech.
PUNCTUATION = set(';:,.!?¡¿—…"«»“”()[]\'-')


def text_words(text):
    """Caption words are whitespace tokens, so joining them reproduces the sentence."""
    return text.split()


# Bump when alignment improves so cached sentences that had to be estimated are measured again.
ALIGNMENT_VERSION = 2

# Stress marks have durations in the stream but are not sounds to match against.
STRESS = set('ˈˌ')
# espeak joins at most a few short function words ("on the", "does not") into one group.
MAX_JOINED = 4


def phoneme_words(timings):
    """Group (phoneme, start, end) rows at spaces into spoken words, keeping each voiced row.

    Punctuation rows are dropped, as are groups made only of punctuation.
    """
    groups, current = [], []
    for row in [*timings, (' ', None, None)]:
        if row[0] == ' ':
            voiced = [r for r in current if r[0] not in PUNCTUATION]
            if voiced:
                groups.append(voiced)
            current = []
        else:
            current.append(row)
    return groups


def bare(phonemes):
    """Phoneme sounds only, for comparing a word spoken alone with the same word in context."""
    return ''.join(p for p in phonemes if p not in PUNCTUATION and p not in STRESS and not p.isspace())


def spoken_count(phonemes):
    """How many spoken words a word's own phoneme string contains."""
    return sum(1 for part in phonemes.split() if bare(part))


def _split_group(group, lengths):
    """Divide one joined phoneme group among words by their share of its sounds."""
    sounds = [r for r in group if r[0] not in STRESS] or group
    total = sum(lengths) or 1
    spans, consumed = [], 0
    for length in lengths:
        first = round(consumed * len(sounds) / total)
        consumed += length
        last = max(first, round(consumed * len(sounds) / total) - 1)
        first, last = min(first, len(sounds) - 1), min(last, len(sounds) - 1)
        spans.append((sounds[first][1], sounds[last][2]))
    return spans


def _align(words, spoken, phonemize_word):
    """Pair text words with spoken groups; returns [(start, end) | None] per word, or None.

    `words` holds (text, spoken count, bare sounds) per word. Each word normally takes as
    many groups as it produces alone (numbers expand). Where espeak joined words, several
    words share one group, but only when their sounds match it exactly, either as spoken
    alone or as espeak speaks the phrase in context ("for a" becomes "fɚɹɚ"). Anything
    else is left to the caller's estimate rather than guessed. Silent words map to None.
    """
    memo = {}

    def joined_sounds(i, size):
        yield ''.join(s for _, _, s in words[i:i + size])
        following = words[i + size:i + size + 1]
        # Reduction depends on the following word ("the" before a vowel), so ask with and without it.
        for extra in ([], following):
            parts = [p for p in phonemize_word(' '.join(w for w, _, _ in words[i:i + size] + extra)).split() if bare(p)]
            # Only evidence when espeak really joined the phrase into one leading group.
            if len(parts) == 1 + sum(c for _, c, _ in extra):
                yield bare(parts[0])

    def options(i, j):
        _, count, _ = words[i]
        if count == 0:
            yield 1, 0, [None]
        elif j + count <= len(spoken):
            yield 1, count, [(spoken[j][0][1], spoken[j + count - 1][-1][2])]
        if count == 1 and j < len(spoken):
            target = bare(r[0] for r in spoken[j])
            for size in range(2, MAX_JOINED + 1):
                joined = words[i:i + size]
                if len(joined) < size or any(c != 1 for _, c, _ in joined):
                    break
                if target in joined_sounds(i, size):
                    yield size, 1, _split_group(spoken[j], [len(s) for _, _, s in joined])

    def solve(i, j):
        if i == len(words):
            return [] if j == len(spoken) else None
        if (i, j) in memo:
            return memo[(i, j)]
        result = None
        for taken, used, spans in options(i, j):
            rest = solve(i + taken, j + used)
            if rest is not None:
                result = spans + rest
                break
        memo[(i, j)] = result
        return result

    return solve(0, 0)


def estimate_words(text, start, end):
    """Fallback: spread words over a span by their letter count."""
    words = text_words(text)
    weights = [max(1, len(re.sub(r'\W', '', w))) for w in words]
    total, consumed, rows = sum(weights), 0, []
    for word, weight in zip(words, weights):
        begin = start + (end - start) * consumed / total
        consumed += weight
        rows.append({'text': word, 'start': begin, 'end': start + (end - start) * consumed / total})
    return rows


def align_words(text, timings, phonemize_word):
    """Map model phoneme timings onto the text's whitespace words.

    Each text word is phonemized alone to learn what it sounds like and how many
    spoken words it produces. Returns (rows, measured); when no alignment exists,
    the words are estimated inside the voiced span and measured is False.
    """
    words = text_words(text)
    spoken = phoneme_words(timings)
    if not spoken:
        end = max((t[2] for t in timings), default=0.0)
        return estimate_words(text, 0.0, end), False
    alone = [phonemize_word(word) for word in words]
    spans = _align([(w, spoken_count(p), bare(p)) for w, p in zip(words, alone)], spoken, phonemize_word)
    if spans is None:
        return estimate_words(text, spoken[0][0][1], spoken[-1][-1][2]), False
    rows, previous = [], spoken[0][0][1]
    for word, span in zip(words, spans):
        # Silent tokens such as a free-standing dash sit at the preceding word's end.
        start, end = span or (previous, previous)
        rows.append({'text': word, 'start': start, 'end': end})
        previous = end
    return rows, True


def offset_words(rows, offset, limit):
    """Shift sentence-local word times into scene time, clamped to the sentence audio."""
    shifted, previous = [], offset
    for row in rows:
        start = min(max(round(offset + row['start'], 6), previous), limit)
        end = min(max(round(offset + row['end'], 6), start), limit)
        shifted.append({'text': row['text'], 'start': start, 'end': end})
        previous = start
    return shifted


# Visuals appear slightly before their word so the eye arrives as the ear does.
LEAD_SECONDS = 0.15


def _normal(word):
    return re.sub(r'\W', '', word.casefold())


def phrase_time(beat, phrase):
    """Start of the first spoken occurrence of a phrase in a beat, or None without word timing.

    The final phrase word may carry a short inflection ("tokenizer" matches "tokenizer's", "token"
    matches "tokens" but not "tokenizer"); an exact match is preferred.
    """
    words = [_normal(w['text']) for w in beat.get('words') or []]
    target = [t for t in (_normal(p) for p in phrase.split()) if t]
    if not words or not target:
        return None
    for exact in (True, False):
        for i in range(len(words) - len(target) + 1):
            head, last = words[i:i+len(target)-1], words[i+len(target)-1]
            inflected = last.startswith(target[-1]) and len(last) - len(target[-1]) <= 3
            if head == target[:-1] and (last == target[-1] if exact else inflected):
                return beat['words'][i]['start']
    return None


def pattern_time(beat, pattern):
    """Start of the first spoken word matching a regular expression, or None."""
    for word in beat.get('words') or []:
        if re.search(pattern, word['text'], re.I):
            return word['start']
    return None


def cue_time(beat, spoken=None):
    """A visual cue inside its sentence: shortly before the spoken word, else the sentence start."""
    if spoken is None:
        return beat['start']
    return min(max(beat['start'], round(spoken - LEAD_SECONDS, 6)), beat['end'] - 0.001)


def validate_words(words, text, start, end):
    if not isinstance(words, list) or [w.get('text') for w in words] != text_words(text):
        raise ValueError('Invalid word timing text')
    previous = start
    for word in words:
        if not previous <= word['start'] <= word['end'] <= end:
            raise ValueError('Invalid word timing range')
        previous = word['start']
