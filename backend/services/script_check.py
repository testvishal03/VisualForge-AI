"""Check a pasted script before Prepare: what the pipeline will make of it, and what will sound wrong.

The checker runs the same conversion, scene split and direction rules as Prepare (no model is
loaded), so scene counts and animations match the real result. Pronunciation warnings come from
the narration voice's own phonemizer: each listed hazard was confirmed by phonemizing it, and
acronyms are checked inside their sentence, since the voice spells "ANN" mid-sentence but reads
"or ANN." at the end of a sentence as the word "an".
"""
import re

from backend.schemas.video_schema import words
from backend.services.director import sentences

WORDS_PER_MINUTE = 140  # measured: 701 narrated words made 5:05 of video, including pauses
# Videos with more scenes than this use rule-based visuals; model planning would take ~40 s per scene.
MODEL_PLANNING_LIMIT = 16
# Longer videos get AI planning only for their weakest scenes, within this budget.
LONG_VIDEO_PLANNING_SECONDS = 300
SECONDS_PER_PLANNED_SCENE = 40  # measured: ~37 s per scene on a 4-core laptop
LONG_SENTENCE = 40
LONG_SCENE_SECONDS = 35
# Generation speed measured on a 4-core laptop with nothing else running: Kokoro needs 0.24 s per
# narrated word, rendering averages 23 frames/s including per-clip work (381 s for a 9,149-frame
# video), and bundling, checking and the thumbnail add about 45 s.
VOICE_SECONDS_PER_WORD = .24
RENDER_FRAMES_PER_SECOND = 23
FIXED_SECONDS = 45
BOOKEND_SECONDS = 8
MEASUREMENT_SECONDS = 20  # loading a model for measured explainers
MODEL_LOAD_SECONDS = 25   # starting the language model before planning


def generation_estimate(words, planned_scenes, measured):
    """Seconds each stage of a first generation should take on this computer; reruns reuse caches."""
    video = words / WORDS_PER_MINUTE * 60 + BOOKEND_SECONDS
    parts = {'planning': planned_scenes * SECONDS_PER_PLANNED_SCENE + (MODEL_LOAD_SECONDS if planned_scenes else 0), 'voice': words * VOICE_SECONDS_PER_WORD,
             'render': video * 30 / RENDER_FRAMES_PER_SECOND, 'other': FIXED_SECONDS + (MEASUREMENT_SECONDS if measured else 0)}
    parts = {k: round(v) for k, v in parts.items()}
    return {'seconds': sum(parts.values()), 'parts': parts}

# (pattern, what the voice does, what to write instead), each confirmed with the Kokoro phonemizer.
HAZARDS = [
    (r'\bhttps?://\S+|\bwww\.\S+', 'Web addresses are read character by character ("h t t p s colon slash slash")', 'say the site name instead'),
    (r'->|=>|→', 'Arrows are skipped by the voice', 'use words such as "becomes" or "leads to"'),
    (r'\be\.g\.', '"e.g." is read as the letters E G', 'write "for example"'),
    (r'\bi\.e\.', '"i.e." is read as the letters I E', 'write "that is"'),
    (r'\bvs\.?(?=\s|$)', '"vs." is read as the letters V S', 'write "versus"'),
    (r'#\d+', '"#1" is read as "hash one"', 'write "number one"'),
    (r'\$\d+(?:\.\d+)?', '"$5" is read as "dollar five"', 'write "5 dollars"'),
    (r'\b\d+(?:\.\d+)?[KMB]\b', '"10M" is read as "ten M"', 'write "10 million"'),
    (r'(?<![:/\w])[A-Za-z0-9]+/[A-Za-z0-9]+\b(?!\.\w)', 'Slashes are read aloud ("fifty slash fifty")', 'use "or", "per" or "to"'),
    (r'\[[^\]]{1,40}\]', 'Text in square brackets is spoken ("[pause]" is read as "pause")', 'remove stage directions'),
    (r'\((?:music|pause|beat|sfx|sound|laughs?|cut to|b-roll|on[- ]screen|visual|graphic|show)\b[^)]{0,40}\)', 'Stage directions in brackets are spoken', 'remove them'),
    (r'^(?:narrator|voice[- ]?over|vo|host|speaker|presenter|scene \d+)\s*:', 'Speaker labels are spoken ("Narrator:" is read aloud)', 'keep only the words to be narrated'),
]
ACRONYM = re.compile(r'\b[A-Z]{2,6}\b')
SCALE = {'k': 'thousand', 'm': 'million', 'b': 'billion'}


def rewrite(found):
    """The spoken-safe replacement for a flagged piece of text, or None when the right words depend
    on meaning (a web address, an arrow or a slash): those are left for the writer."""
    text = found.strip()
    lower = text.casefold()
    replacement = None
    if lower == 'e.g.':
        replacement = 'for example'
    elif lower == 'i.e.':
        replacement = 'that is'
    elif re.fullmatch(r'vs\.?', lower):
        replacement = 'versus'
    elif re.fullmatch(r'#\d+', text):
        replacement = 'number ' + text[1:]
    elif re.fullmatch(r'\$\d+(?:\.\d+)?', text):
        replacement = text[1:] + (' dollar' if text[1:] == '1' else ' dollars')
    elif re.fullmatch(r'\d+(?:\.\d+)?[KMB]', text, re.I):
        replacement = text[:-1] + ' ' + SCALE[text[-1].casefold()]
    elif re.fullmatch(r'\[[^\]]*\]|\([^)]*\)', text) or re.fullmatch(r'[A-Za-z][A-Za-z -]*\d*\s*:', text):
        replacement = ''  # stage directions and speaker labels are removed
    if replacement and text[:1].isupper():
        replacement = replacement[:1].upper() + replacement[1:]
    return replacement


def _phonemizer():
    try:
        from kokoro_onnx.tokenizer import Tokenizer
        tokenizer = Tokenizer()
        return lambda text: tokenizer.phonemize(text, 'en-us')
    except Exception:  # The voice package is optional for checking; acronym checks are skipped.
        return None


_PHONEMIZE = []


def phonemize(text):
    if not _PHONEMIZE:
        _PHONEMIZE.append(_phonemizer())
    return _PHONEMIZE[0](text) if _PHONEMIZE[0] else None


def read_as_word(acronym, sentence):
    """True when the voice reads `acronym` as a word in this sentence instead of spelling its letters."""
    spoken = phonemize(sentence)
    if spoken is None:
        return False
    spelled = phonemize(re.sub(rf'\b{acronym}\b', '-'.join(acronym), sentence))
    strip = lambda p: re.sub(r'[ˈˌ\s.,!?-]', '', p)
    return len(strip(spelled)) - len(strip(spoken)) >= len(acronym)


def _issue(level, message, scene=None, excerpt=None):
    row = {'level': level, 'message': message, 'scene': scene}
    if excerpt:
        row['excerpt'] = excerpt if len(excerpt) <= 90 else excerpt[:87].rstrip() + '...'
    return row


EXPLAINER_LABELS = {'next_token': 'Next-token odds', 'denoise': 'Noise-to-image', 'contrast': 'Sort vs. create',
                    'caveats': 'Caveat cards', 'steps': 'Learning steps', 'tokens': 'Tokenization',
                    'embedding_map': 'Meaning map', 'retrieval': 'Retrieval flow'}


def _explainer_note(kind):
    if kind in ('next_token', 'tokens'):
        return 'measured by the local language model'
    if kind == 'embedding_map':
        from backend.services import embeddings
        return 'measured with bge-small-en-v1.5' if embeddings.installed() else 'illustrative (embedding model not installed)'
    return 'illustrative'


def check(text, title=None):
    """Findings for a pasted script: counts, issues (error / warning / info) and planned animations."""
    from backend.services.page_script import looks_like_markdown, page_to_script
    issues, converted = [], False
    if not isinstance(text, str) or not text.strip():
        return {'words': 0, 'scenes': 0, 'minutes': 0, 'issues': [_issue('error', 'Paste the words you want narrated.')], 'highlights': []}
    if looks_like_markdown(text):
        result = page_to_script(text)
        text, title, converted = result['script'], title or result['title'], True
        issues.append(_issue('info', 'Formatted notes detected. Prepare converts them to narration: headings become scenes and labels are not read aloud.'))
    count = len(words(text))
    report = {'words': count, 'minutes': round(count / WORDS_PER_MINUTE, 1), 'converted': converted, 'scenes': 0, 'issues': issues, 'highlights': []}
    if count < 30:
        issues.insert(0, _issue('error', f'Only {count} words. Use at least 30 spoken words, in two or more paragraphs.'))
        return report
    from backend.services.director import build_direction, script_to_video
    from backend.services.editor_store import document_from_video
    from backend.services.explainers import plan as plan_explainer
    # Prepare treats a single short line as a possible file path; a newline (whitespace to the
    # splitter) keeps the checker from ever reading local files.
    safe = text if '\n' in text.strip() else text.strip().replace(' ', '\n', 1)
    try:
        video = script_to_video(title, safe)
    except ValueError as exc:
        issues.insert(0, _issue('error', str(exc)))
        return report
    document = document_from_video(video, build_direction(video))
    report.update(scenes=len(video.scenes), title=video.title)

    seen = {}
    for scene in video.scenes:
        n = scene.id
        for pattern, problem, fix in HAZARDS:
            for part in sentences(scene.narration):
                found = re.search(pattern, part, re.I | re.M)
                if found:
                    issue = _issue('warning', f'{problem}: {fix}.', n, found[0])
                    replacement = rewrite(found[0])
                    # Fixes edit the pasted text, so they are offered only when it was not converted.
                    if replacement is not None and not converted:
                        issue['fix'] = {'find': found[0], 'replace': replacement, 'sentence': part}
                    issues.append(issue)
        for part in sentences(scene.narration):
            size = len(words(part))
            if size > LONG_SENTENCE:
                issues.append(_issue('warning', f'Long sentence ({size} words). Shorter sentences give clearer captions and natural pauses.', n, part))
            for acronym in dict.fromkeys(ACRONYM.findall(part)):
                if read_as_word(acronym, part):
                    issue = _issue('info', f'"{acronym}" is read as a word here, not spelled out. If it should be spelled, write {"-".join(acronym)}.', n, part)
                    if not converted:
                        issue['fix'] = {'find': acronym, 'replace': '-'.join(acronym), 'sentence': part}
                    issues.append(issue)
            key = re.sub(r'\W+', ' ', part).casefold().strip()
            if size >= 6:
                if key in seen and seen[key] != n:
                    issues.append(_issue('warning', f'This sentence also appears in scene {seen[key]}. Repeated lines sound like a mistake.', n, part))
                seen.setdefault(key, n)
        straight, curly = scene.narration.count('"'), scene.narration.count('“') - scene.narration.count('”')
        if straight % 2 or curly:
            issues.append(_issue('warning', 'Unmatched quote mark. Quoted examples drive some animations, so close every quote.', n))
        seconds = len(words(scene.narration)) / WORDS_PER_MINUTE * 60
        if seconds > LONG_SCENE_SECONDS:
            issues.append(_issue('info', f'This scene runs about {round(seconds)} seconds on one visual. A blank line splits it into two scenes.', n, sentences(scene.narration)[0]))
    if len(video.scenes) > MODEL_PLANNING_LIMIT:
        issues.append(_issue('info', f'{len(video.scenes)} scenes: over {MODEL_PLANNING_LIMIT} scenes, the AI plans visuals only for the weakest '
                                     f'scenes (up to {LONG_VIDEO_PLANNING_SECONDS // 60} minutes); the rest use rule-based visuals.'))
    for number, row in enumerate(document['scenes'], 1):
        spec = None if row['visual'].get('worked') else plan_explainer(row)
        if spec:
            report['highlights'].append({'scene': number, 'kind': spec['kind'], 'label': EXPLAINER_LABELS.get(spec['kind'], spec['kind']),
                                         'note': _explainer_note(spec['kind'])})
    # The planner skips explainer scenes; long videos plan only their weakest scenes.
    if len(video.scenes) > MODEL_PLANNING_LIMIT:
        from backend.services.visual_quality import weak_scenes
        planned = len(weak_scenes(document, LONG_VIDEO_PLANNING_SECONDS // SECONDS_PER_PLANNED_SCENE))
    else:
        planned = len(video.scenes) - len(report['highlights'])
    measured = any(h['kind'] in ('next_token', 'tokens', 'embedding_map') for h in report['highlights'])
    report['estimate'] = generation_estimate(count, planned, measured)
    order = {'error': 0, 'warning': 1, 'info': 2}
    issues.sort(key=lambda row: (order[row['level']], row['scene'] or 0))
    return report
