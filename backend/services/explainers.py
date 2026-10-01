"""Animated explainer templates chosen from what the narration says.

Each template is a reusable animation (next-token prediction, noise-to-image, a
judge-versus-create contrast, limitation cards). The narration decides which one
applies and when each moment plays: every cue is tied to a spoken sentence and,
when words were measured, to the word that names it. Text shown on screen is the
narration's own words, short fixed headings, or an example the narration quotes.
Nothing claims to be a measured model output.
"""
import re

from backend.services.director import sentences
from backend.utils.word_timing import cue_time, pattern_time

NEXT_TOKEN = r'\bnext[- ](?:word|token|piece)s?\b|\bpredict\w*\b.{0,30}\bnext\b|\bautocomplete\b|\bguess\w*\b.{0,30}\bnext\b'
NOISE = r'\b(?:noise|static|noisy)\b'
IMAGE = r'\b(?:image|images|picture|pictures|pic|pics|art|artwork|diffusion|photo|photos)\b'
OLD_AI = r'\b(?:old[- ]school|traditional|classic|older|discriminative|regular)\s+(?:AI|models?|machine learning)\b'
GEN_AI = r'\b(?:generative AI|gen AI|generative models?)\b'
CAVEATS = [
    ('wrong', 'Can be wrong', r'\b(?:hallucinat\w*|wrong|made[- ]up|making (?:stuff|things) up|invent\w*|errors?)\b'),
    ('bias', 'Copies bias', r'\bbias\w*\b'),
    ('editor', 'Check its work', r'\b(?:fact[- ]check\w*|editor|verify|double[- ]check\w*|review)\b'),
    ('privacy', 'Mind your data', r'\b(?:privacy|private|sensitive data|personal data)\b'),
]
# Ordered steps: sentences opening with an ordinal become numbered cards.
ORDINAL = r'^(?:first(?:ly)?|second(?:ly)?|third(?:ly)?|next|then|finally|lastly|step \d+)\b[,:]?\s*'
STEP_KINDS = [
    ('feed', 'Feed it', r'\b(?:fe[ed]d?|feeds|data|dataset|texts?|examples|train\w*|collect\w*)\b'),
    ('patterns', 'Find patterns', r'\b(?:patterns?|dials?|parameters?|weights?|tun\w*|adjust\w*)\b'),
    ('prompt', 'Prompt it', r'\b(?:prompt\w*|ask\w*|query|request|type)\b'),
]
# Shapes the noise can resolve into, named by the narration.
SHAPES = ['heart', 'star', 'sun', 'smile', 'moon', 'flower', 'tree', 'house', 'cat']
# Only this built-in example carries illustrative candidate words; it is labelled as an example.
EXAMPLE_PROMPT = 'the cat sat on the'
EXAMPLE_CANDIDATES = ['mat', 'floor', 'sofa']
QUOTE = r'["“‘]([^"”’]{3,60})["”’]'


def first(parts, pattern):
    return next((i for i, part in enumerate(parts) if re.search(pattern, part, re.I)), None)


def quoted(text):
    return [q.strip(' .?!,') for q in re.findall(QUOTE, text)]


def plan(scene):
    """The explainer this narration calls for, or None. Cues are sentence indices plus spoken patterns."""
    # Opening and closing cards keep their own treatment, even when they echo a lesson's key phrase.
    if scene.get('visual', {}).get('kind') in {'title', 'takeaway'}:
        return None
    text, parts = scene['narration'], sentences(scene['narration'])
    if re.search(NEXT_TOKEN, text, re.I):
        prompt = next((q for q in quoted(text) if 2 <= len(q.split()) <= 8 and not q.endswith('?')), None)
        builtin = prompt is None or prompt.casefold() == EXAMPLE_PROMPT
        return {'kind': 'next_token', 'prompt': prompt or EXAMPLE_PROMPT, 'source': 'narration' if prompt else 'example',
                'candidates': EXAMPLE_CANDIDATES if builtin else [],
                'cues': {'type': (first(parts, NEXT_TOKEN) or 0, None),
                         'guess': (first(parts, NEXT_TOKEN) or 0, r'^(?:next\w*|guess\w*|predict\w*|picks?|chooses?|likely)$'),
                         'repeat': (first(parts, r'\b(?:repeat\w*|again|loop\w*|thousands|over and over)\b'), r'^(?:repeat\w*|again|loop\w*|thousands)$')}}
    if re.search(NOISE, text, re.I) and re.search(IMAGE, text, re.I):
        subject = next((s for s in SHAPES if re.search(rf'\b{s}s?\b', text, re.I)), None)
        clean = first(parts, r'\b(?:clean\w*|step by step|remov\w*|denois\w*|refin\w*|sharpen\w*)\b')
        return {'kind': 'denoise', 'subject': subject or 'star', 'named': bool(subject),
                'cues': {'noise': (first(parts, NOISE), r'^(?:noise|static|noisy)$'),
                         'clean': (clean if clean is not None else first(parts, NOISE), r'^(?:clean\w*|step|remov\w*|denois\w*|refin\w*|sharpen\w*)$')}}
    old, new = first(parts, OLD_AI), first(parts, GEN_AI)
    if old is not None and new is not None:
        options = re.search(r'\b(?:a|an)\s+(\w+)\s+or\s+(?:a|an)\s+(\w+)\b', text, re.I)
        return {'kind': 'contrast',
                'left': {'title': re.search(OLD_AI, parts[old], re.I)[0], 'verb': 'sorts'},
                'right': {'title': re.search(GEN_AI, parts[new], re.I)[0], 'verb': 'creates'},
                'bins': [options[1], options[2]] if options else [],
                'hoodie': bool(re.search(r'\bhoodies?\b', text, re.I)),
                'cues': {'left': (old, r'^(?:old\w*|traditional|classic|sorts?|judges?|classif\w*)$'),
                         'right': (new, r'^(?:generative|gen|creates?|makes?|draws?)$')}}
    ordered = [(i, m) for i, part in enumerate(parts) if (m := re.match(ORDINAL, part, re.I))]
    if 2 <= len(ordered) <= 4:
        steps = []
        for i, match in ordered:
            rest = parts[i][match.end():].strip()
            # The narration's own words: the step's opening clause, before any comma or "by ...".
            detail = ' '.join(re.split(r',|;|\s+by\s+|\s+which\s+', rest, maxsplit=1)[0].split()[:6]).rstrip('.!?')
            # The step's own clause decides its icon; the rest of the sentence only breaks ties.
            key, title = next(((k, t) for source in (detail, parts[i]) for k, t, p in STEP_KINDS if re.search(p, source, re.I)),
                              ('step', f'Step {len(steps) + 1}'))
            steps.append({'key': key, 'title': title, 'detail': detail})
        # Only learning-style flows get these cards; other ordered scenes keep their process diagrams.
        if sum(s['key'] != 'step' for s in steps) >= 2 and len({s['key'] for s in steps}) >= 2:
            return {'kind': 'steps', 'steps': steps,
                    'cues': {f's{n}': (i, r'^(?:first|second|third|next|then|finally|lastly|step)$') for n, (i, _) in enumerate(ordered)}}
    cards = [(key, title, first(parts, pattern), pattern) for key, title, pattern in CAVEATS]
    cards = [c for c in cards if c[2] is not None]
    if len(cards) >= 2:
        cards.sort(key=lambda c: c[2])
        return {'kind': 'caveats', 'cards': [{'key': key, 'title': title} for key, title, _, _ in cards],
                'cues': {key: (index, pattern.replace(r'\b', '')) for key, _, index, pattern in cards}}
    return None


def word_cue(beat, pattern):
    """Start of the first spoken word that fully matches, so the animation lands on it."""
    if not pattern:
        return None
    for word in beat.get('words') or []:
        if re.search(pattern if pattern.startswith('^') else rf'^(?:{pattern})$', re.sub(r'\W', '', word['text']), re.I):
            return word['start']
    return pattern_time(beat, pattern) if not pattern.startswith('^') else None


def timed(spec, beats):
    """Replace sentence cues with measured times; cues whose sentence is absent are dropped."""
    times = {}
    for name, (sentence, pattern) in spec['cues'].items():
        if sentence is None or sentence >= len(beats):
            continue
        times[name] = cue_time(beats[sentence], word_cue(beats[sentence], pattern))
    return {**{k: v for k, v in spec.items() if k != 'cues'}, 'at': times, 'end': beats[-1]['end'] if beats else 0}
