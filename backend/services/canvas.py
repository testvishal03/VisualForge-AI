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
    # Machine-learning visuals. Elements that name a "plot" use that plot's data coordinates.
    'plot': ({'x', 'y', 'w', 'h'}, {'xRange', 'yRange', 'xLabel', 'yLabel', 'grid', 'color'}),
    'points': ({'plot', 'data'}, {'classes', 'r', 'stagger'}),
    'curve': ({'plot'}, {'data', 'shape', 'start', 'color', 'dashed', 'dur'}),
    'dot': (set(), {'plot', 'x', 'y', 'path', 'color', 'r', 'label', 'dur'}),
    'segments': ({'plot', 'segments'}, {'color', 'dashed'}),
    'region': ({'plot', 'polygon'}, {'color'}),
    'table': ({'x', 'y', 'rows'}, {'colWidth', 'rowHeight', 'header', 'highlight', 'color', 'stagger'}),
    'network': ({'x', 'y', 'w', 'h', 'layers'}, {'color', 'labels'}),
    'counter': ({'x', 'y', 'value'}, {'begin', 'prefix', 'suffix', 'decimals', 'size', 'color', 'dur'}),
}
COMMON = {'id', 'type', 'at', 'delay', 'word', 'out', 'pulse'}
ML_KEYS = {'xRange', 'yRange', 'xLabel', 'yLabel', 'grid', 'plot', 'data', 'classes', 'stagger', 'shape', 'start', 'path',
           'segments', 'polygon', 'rows', 'colWidth', 'rowHeight', 'header', 'highlight', 'layers', 'labels', 'value', 'begin',
           'prefix', 'suffix', 'decimals'}
SAMPLES = 60  # points used to draw a curve given by a formula
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


def _pairs(value, name, low=2, high=300, width=2):
    """A list of [x, y] (or [x, y, class]) number rows."""
    if not isinstance(value, list) or not low <= len(value) <= high:
        raise CanvasError(f'{name} must list {low} to {high} entries')
    rows = []
    for item in value:
        if not isinstance(item, list) or len(item) not in (width, width + 1) or \
                any(type(v) not in (int, float) or not math.isfinite(v) for v in item):
            raise CanvasError(f'{name} entries must be [x, y]' + (' or [x, y, class]' if width == 2 else ''))
        rows.append(list(item))
    return rows


def _ml_value(key, value, where, element_type):
    """Validate one machine-learning field; plot references and formulas are resolved later."""
    if key in ('xRange', 'yRange'):
        if not isinstance(value, list) or len(value) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in value) or value[0] >= value[1]:
            raise CanvasError(f'{where}: {key} must be [low, high] with low < high')
        return list(value)
    if key in ('xLabel', 'yLabel', 'prefix', 'suffix'):
        return _text(value, f'{where} {key}', 40) if key in ('xLabel', 'yLabel') else (value if isinstance(value, str) and len(value) <= 12 else _text('', f'{where} {key}', 12))
    if key in ('grid', 'header'):
        if type(value) is not bool:
            raise CanvasError(f'{where}: {key} must be true or false')
        return value
    if key == 'plot':
        return _text(value, f'{where} plot', 40)
    if key == 'data':
        return _pairs(value, f'{where} data')
    if key == 'start':
        return _pairs(value, f'{where} start')
    if key == 'path':
        return _pairs(value, f'{where} path', 1, 30)
    if key == 'polygon':
        return _pairs(value, f'{where} polygon', 3, 40)
    if key == 'segments':
        return _pairs(value, f'{where} segments', 1, 120, width=4)
    if key == 'classes':
        if not isinstance(value, list) or not 1 <= len(value) <= 8 or any(c not in COLORS for c in value):
            raise CanvasError(f'{where}: classes must list 1 to 8 colours')
        return value
    if key == 'stagger':
        return _number(value, 0, 1, f'{where} stagger')
    if key == 'shape':
        kinds = {'line': {'slope', 'intercept'}, 'sigmoid': {'k', 'x0'}, 'poly': {'coefficients'}}
        if not isinstance(value, dict) or value.get('type') not in kinds or set(value) - {'type'} - kinds[value['type']]:
            raise CanvasError(f'{where}: shape is {{"type": "line", "slope", "intercept"}}, {{"type": "sigmoid", "k", "x0"}} or {{"type": "poly", "coefficients": [...]}}')
        for name, number in value.items():
            if name == 'type':
                continue
            numbers = number if name == 'coefficients' else [number]
            if not isinstance(numbers, list) or not 1 <= len(numbers) <= 8 or any(type(v) not in (int, float) or not math.isfinite(v) for v in numbers):
                raise CanvasError(f'{where}: shape {name} must be a number' + (' list' if name == 'coefficients' else ''))
        return dict(value)
    if key == 'rows':
        if not isinstance(value, list) or not 1 <= len(value) <= 12 or any(not isinstance(r, list) or not 1 <= len(r) <= 8 for r in value):
            raise CanvasError(f'{where}: rows must be 1 to 12 rows of 1 to 8 cells')
        cells = [[str(cell) for cell in row] for row in value]
        if any(len(cell) > 24 for row in cells for cell in row):
            raise CanvasError(f'{where}: table cells are at most 24 characters')
        return cells  # an empty cell is fine (the corner of a confusion matrix)
    if key in ('colWidth', 'rowHeight'):
        return _number(value, 30, 900, f'{where} {key}')
    if key == 'highlight':
        if not isinstance(value, list) or len(value) > 96:
            raise CanvasError(f'{where}: highlight lists [row, column, colour] cells')
        cells = []
        for cell in value:
            if not isinstance(cell, list) or len(cell) != 3 or type(cell[0]) is not int or type(cell[1]) is not int or cell[2] not in COLORS:
                raise CanvasError(f'{where}: highlight cells are [row, column, colour]')
            cells.append(cell)
        return cells
    if key == 'layers':
        if not isinstance(value, list) or not 2 <= len(value) <= 6 or any(type(n) is not int or not 1 <= n <= 8 for n in value):
            raise CanvasError(f'{where}: layers lists 2 to 6 neuron counts from 1 to 8')
        return value
    if key == 'labels':
        if not isinstance(value, list) or len(value) > 6:
            raise CanvasError(f'{where}: labels lists one short name per layer')
        return [_text(v, f'{where} label', 24) for v in value]
    if key in ('value', 'begin'):
        return _number(value, -1e9, 1e9, f'{where} {key}')
    if key == 'decimals':
        if type(value) is not int or not 0 <= value <= 4:
            raise CanvasError(f'{where}: decimals must be 0 to 4')
        return value
    raise CanvasError(f'{where}: unknown {key}')


def _expand(shape, x_range):
    """Points of a formula curve across the plot's x range."""
    low, high = x_range
    xs = [low + (high - low) * i / (SAMPLES - 1) for i in range(SAMPLES)]
    if shape['type'] == 'line':
        return [[x, shape.get('slope', 1) * x + shape.get('intercept', 0)] for x in xs]
    if shape['type'] == 'sigmoid':
        k, x0 = shape.get('k', 1), shape.get('x0', 0)
        return [[x, 1 / (1 + math.exp(max(-60, min(60, -k * (x - x0)))))] for x in xs]
    return [[x, sum(c * x ** n for n, c in enumerate(shape['coefficients']))] for x in xs]


def _resolve_plots(clean):
    """Check plot references, fill default ranges and turn formula curves into points."""
    plots = {row['id']: row for row in clean if row['type'] == 'plot' and 'id' in row}
    for index, row in enumerate(clean, 1):
        if row['type'] == 'plot':
            row.setdefault('xRange', [0, 10])
            row.setdefault('yRange', [0, 10])
        if 'plot' in row:
            if row['plot'] not in plots:
                raise CanvasError(f'element {index}: plot "{row["plot"]}" must be the id of a plot element')
            plot = plots[row['plot']]
            if row['type'] == 'curve':
                if 'shape' in row:
                    row['data'] = _expand(row.pop('shape'), plot.get('xRange', [0, 10]))
                if 'data' not in row:
                    raise CanvasError(f'element {index}: a curve needs data points or a shape')
                if 'start' in row and len(row['start']) != len(row['data']):
                    raise CanvasError(f'element {index}: start must have as many points as the curve')
        elif row['type'] in ('dot',) and ('x' not in row or 'y' not in row) and 'path' not in row:
            raise CanvasError(f'element {index}: a dot needs x and y, or a path')
        if row['type'] == 'dot' and 'plot' in row and ('x' not in row or 'y' not in row) and 'path' not in row:
            raise CanvasError(f'element {index}: a dot needs x and y, or a path')
        if row['type'] == 'table':
            columns = max(len(r) for r in row['rows'])
            for r, c, _ in row.get('highlight', []):
                if not (0 <= r < len(row['rows']) and 0 <= c < columns):
                    raise CanvasError(f'element {index}: highlight cell [{r}, {c}] is outside the table')


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
            if key in ML_KEYS:
                row[key] = _ml_value(key, value, where, element['type'])
            elif key in ('x', 'y') and 'plot' in element:
                row[key] = _number(value, -1e9, 1e9, f'{where} {key}')  # data coordinates on its plot
            elif key in ('x', 'x1', 'x2', 'w'):
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
    _resolve_plots(clean)
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
