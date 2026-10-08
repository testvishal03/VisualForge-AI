"""Scene canvases: a hand-designed 2D animation for each scene, written alongside the script.

A script may follow any narration paragraph with a fenced block that describes what the scene
shows, for example

    Without guardrails, one bad answer can lead to real damage for a company.

    ```visual
    {"elements": [
      {"id": "model", "type": "box", "x": 960, "y": 240, "w": 360, "h": 140, "text": "AI MODEL", "color": "yellow", "at": 0},
      {"id": "facts", "type": "box", "x": 480, "y": 520, "text": "Made-up facts", "color": "red", "at": 1},
      {"type": "arrow", "from": "model", "to": "facts", "color": "red", "at": 1, "delay": 0.2}
    ]}
    ```

The block is never narrated. Coordinates are on a 1920x1080 frame (the caption sits below
y=960). `at` is the sentence (0-based) whose start reveals the element, `delay` adds seconds,
and `word` lands it on a spoken word in that sentence instead. Everything is validated before
rendering; an invalid block is reported with its scene and the scene keeps the normal visuals.
"""
import json
import math
import re

from backend.utils.word_timing import cue_time

COLORS = {'yellow', 'cyan', 'pink', 'green', 'red', 'muted', 'white', 'line', 'purple', 'orange'}
SIZES = {'title', 'h2', 'body', 'small'}
TYPES = {
    # type: (required fields, optional fields)
    'box': ({'x', 'y'}, {'w', 'h', 'text', 'sub', 'color', 'fill', 'icon'}),
    'arrow': ({'from', 'to'}, {'color', 'dashed', 'label', 'curve'}),
    'bubble': ({'x', 'y', 'text'}, {'w', 'color', 'mono', 'side'}),
    'pill': ({'x', 'y', 'text'}, {'color'}),
    'check': ({'x', 'y'}, {'r', 'color'}),
    'cross': ({'x', 'y'}, {'r', 'color'}),
    'stamp': ({'x', 'y', 'text'}, {'color'}),
    'text': ({'x', 'y', 'text'}, {'size', 'color', 'align'}),
    'headline': ({'text'}, {'color', 'y'}),
    'bracket': ({'x1', 'x2', 'y'}, {'color', 'label'}),
    'ring': ({'x', 'y', 'r'}, {'color', 'text'}),
    'bar': ({'x', 'y', 'w', 'h'}, {'color', 'text'}),
    'icon': ({'x', 'y', 'name'}, {'size', 'color'}),
    'mover': ({'from', 'to'}, {'text', 'color', 'dur'}),
    'line': ({'points'}, {'color', 'dashed'}),
}
COMMON = {'id', 'type', 'at', 'delay', 'word', 'out', 'pulse'}
MAX_ELEMENTS = 40
FENCE = re.compile(r'^```\s*visual\s*\n(.*?)\n```\s*$', re.S | re.M)


class CanvasError(ValueError):
    pass


def extract(text):
    """Split a script into narration and per-paragraph canvas blocks.

    Returns (narration, specs, errors): narration has the blocks removed, `specs[i]` is the parsed
    block for narration paragraph i (or None), and `errors` lists unparseable blocks as
    (paragraph number, message). Text without blocks returns specs == [].
    """
    text = text.replace('\r\n', '\n')
    if not FENCE.search(text):
        return text, [], []
    paragraphs, specs, errors = [], [], []
    position = 0
    for match in FENCE.finditer(text):
        before = [p.strip() for p in re.split(r'\n\s*\n', text[position:match.start()]) if p.strip()]
        for paragraph in before:
            paragraphs.append(paragraph)
            specs.append(None)
        if not paragraphs:
            errors.append((1, 'A visual block must follow the paragraph it illustrates.'))
        else:
            try:
                specs[-1] = json.loads(match[1])
            except ValueError as exc:
                errors.append((len(paragraphs), f'The visual block is not valid JSON ({exc.msg} at line {exc.lineno}).'))
        position = match.end()
    for paragraph in [p.strip() for p in re.split(r'\n\s*\n', text[position:]) if p.strip()]:
        paragraphs.append(paragraph)
        specs.append(None)
    return '\n\n'.join(paragraphs), specs, errors


def _number(value, low, high, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise CanvasError(f'{name} must be a number from {low} to {high}')
    return value


def _text(value, name, limit=140):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise CanvasError(f'{name} must be text of at most {limit} characters')
    return value


def _point(value, ids, name):
    if isinstance(value, str):
        if value not in ids:
            raise CanvasError(f'{name} refers to unknown element "{value}"')
        return value
    if isinstance(value, list) and len(value) == 2:
        return [_number(value[0], 0, 1920, f'{name} x'), _number(value[1], 0, 1080, f'{name} y')]
    raise CanvasError(f'{name} must be an element id or [x, y]')


def validate(spec, sentences):
    """A clean copy of a canvas block, or CanvasError naming the first problem."""
    if not isinstance(spec, dict) or not isinstance(spec.get('elements'), list) or set(spec) - {'elements'}:
        raise CanvasError('A visual block is {"elements": [...]}')
    elements = spec['elements']
    if not 1 <= len(elements) <= MAX_ELEMENTS:
        raise CanvasError(f'Use 1 to {MAX_ELEMENTS} elements')
    ids = {e.get('id') for e in elements if isinstance(e, dict) and isinstance(e.get('id'), str)}
    if len(ids) != sum(isinstance(e, dict) and isinstance(e.get('id'), str) for e in elements):
        raise CanvasError('Element ids must be unique')
    clean = []
    for index, element in enumerate(elements, 1):
        where = f'element {index}'
        if not isinstance(element, dict) or element.get('type') not in TYPES:
            raise CanvasError(f'{where}: type must be one of {", ".join(sorted(TYPES))}')
        required, optional = TYPES[element['type']]
        missing, unknown = required - set(element), set(element) - required - optional - COMMON
        if missing or unknown:
            raise CanvasError(f'{where} ({element["type"]}): ' + (f'missing {", ".join(sorted(missing))}' if missing else f'unknown {", ".join(sorted(unknown))}'))
        row = {'type': element['type']}
        if 'id' in element:
            row['id'] = _text(element['id'], f'{where} id', 40)
        at = element.get('at', 0)
        if type(at) is not int or at < 0:
            raise CanvasError(f'{where}: "at" must be a sentence number from 0')
        row['at'] = min(at, len(sentences) - 1)  # a shortened paragraph keeps its visuals
        row['delay'] = _number(element.get('delay', 0), 0, 10, f'{where} delay')
        if 'word' in element:
            row['word'] = _text(element['word'], f'{where} word', 40)
        if 'out' in element:
            out = element['out']
            if not isinstance(out, dict) or set(out) - {'at', 'delay'} or type(out.get('at', 0)) is not int:
                raise CanvasError(f'{where}: "out" is {{"at": sentence, "delay": seconds}}')
            row['out'] = {'at': min(out.get('at', 0), len(sentences) - 1), 'delay': _number(out.get('delay', 0), 0, 10, f'{where} out delay')}
        if 'pulse' in element:
            row['pulse'] = min(int(_number(element['pulse'], 0, 50, f'{where} pulse')), len(sentences) - 1)
        for key in (required | optional) & set(element):
            value = element[key]
            if key in ('x', 'x1', 'x2', 'w'):
                row[key] = _number(value, 0, 1920, f'{where} {key}')
            elif key in ('y', 'h', 'r'):
                row[key] = _number(value, 0, 1080, f'{where} {key}')
            elif key in ('size',) and element['type'] == 'icon':
                row[key] = _number(value, 16, 400, f'{where} size')
            elif key == 'size':
                if value not in SIZES:
                    raise CanvasError(f'{where}: size must be one of {", ".join(sorted(SIZES))}')
                row[key] = value
            elif key == 'color':
                if value not in COLORS:
                    raise CanvasError(f'{where}: color must be one of {", ".join(sorted(COLORS))}')
                row[key] = value
            elif key == 'fill':
                if value not in ('panel', 'tint', 'solid', 'none'):
                    raise CanvasError(f'{where}: fill must be panel, tint, solid or none')
                row[key] = value
            elif key == 'align':
                if value not in ('left', 'center', 'right'):
                    raise CanvasError(f'{where}: align must be left, center or right')
                row[key] = value
            elif key == 'side':
                if value not in ('left', 'right'):
                    raise CanvasError(f'{where}: side must be left or right')
                row[key] = value
            elif key in ('mono', 'dashed'):
                if type(value) is not bool:
                    raise CanvasError(f'{where}: {key} must be true or false')
                row[key] = value
            elif key == 'curve':
                row[key] = _number(value, -400, 400, f'{where} curve')
            elif key == 'dur':
                row[key] = _number(value, .2, 10, f'{where} dur')
            elif key in ('from', 'to'):
                row[key] = value  # checked below, once every id is known
            elif key == 'points':
                if not isinstance(value, list) or not 2 <= len(value) <= 12:
                    raise CanvasError(f'{where}: points must list 2 to 12 [x, y] pairs')
                row[key] = [_point(p, set(), f'{where} point') for p in value]
            elif key in ('text', 'sub', 'label'):
                row[key] = _text(value, f'{where} {key}', 160 if element['type'] == 'bubble' else 80)
            elif key in ('name', 'icon'):
                row[key] = _text(value, f'{where} {key}', 40)
        clean.append(row)
    for index, row in enumerate(clean, 1):
        for key in ('from', 'to'):
            if key in row:
                row[key] = _point(row[key], ids, f'element {index} {key}')
    return {'elements': clean}


def timed(spec, beats):
    """Replace sentence cues with seconds from the scene start, landing on spoken words when named."""
    def moment(at, delay, word=None):
        beat = beats[min(at, len(beats) - 1)]
        spoken = None
        if word:
            target = re.sub(r'\W', '', word).casefold()
            spoken = next((w['start'] for w in beat.get('words') or [] if re.sub(r'\W', '', w['text']).casefold().startswith(target)), None)
        return round(cue_time(beat, spoken) + delay, 3)
    elements = []
    for row in spec['elements']:
        timed_row = {k: v for k, v in row.items() if k not in ('at', 'delay', 'word', 'out', 'pulse')}
        timed_row['t'] = moment(row['at'], row['delay'], row.get('word'))
        if 'out' in row:
            timed_row['tOut'] = moment(row['out']['at'], row['out']['delay'])
        if 'pulse' in row:
            timed_row['tPulse'] = moment(row['pulse'], 0)
        elements.append(timed_row)
    return {'elements': elements}
