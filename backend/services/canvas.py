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
COMMON = {'id', 'type', 'at', 'delay', 'word', 'out', 'pulse', 'moveTo', 'dim', 'typing'}
ML_KEYS = {'xRange', 'yRange', 'xLabel', 'yLabel', 'grid', 'plot', 'data', 'classes', 'stagger', 'shape', 'start', 'path',
           'segments', 'polygon', 'rows', 'colWidth', 'rowHeight', 'header', 'highlight', 'layers', 'labels', 'value', 'begin',
           'prefix', 'suffix', 'decimals'}
SAMPLES = 60  # points used to draw a curve given by a formula
MAX_ELEMENTS = 40
FENCE = re.compile(r'^```\s*visual\s*\n(.*?)\n```\s*$', re.S | re.M)


class CanvasError(ValueError):
    pass


BARE = re.compile(r'^[ \t]*visual[ \t]*\n(?=[ \t]*\{)', re.I | re.M)


def fence_bare_blocks(text):
    """Copying from a chat window drops the ``` lines and leaves the word "visual" above the JSON;
    such blocks are fenced again so both forms work."""
    out, position = [], 0
    decoder = json.JSONDecoder()
    for match in BARE.finditer(text):
        if match.start() < position:
            continue
        start = match.end() + (len(text[match.end():]) - len(text[match.end():].lstrip(' \t')))
        try:
            _, end = decoder.raw_decode(text, start)
        except ValueError:
            # Unreadable JSON: fence it up to the closing brace line, so the error names the scene.
            closing = re.compile(r'^\}\s*$', re.M).search(text, start)
            end = closing.end() if closing else len(text)
        out.append(text[position:match.start()] + '```visual\n' + text[start:end].strip() + '\n```')
        position = end
    return ''.join(out) + text[position:]


def extract(text):
    """Split a script into narration and per-paragraph canvas blocks.

    Returns (narration, specs, errors): narration has the blocks removed, `specs[i]` is the parsed
    block for narration paragraph i (or None), and `errors` lists unparseable blocks as
    (paragraph number, message). Text without blocks returns specs == [].
    """
    text = fence_bare_blocks(text.replace('\r\n', '\n'))
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
    if not isinstance(spec, dict) or not isinstance(spec.get('elements'), list) or set(spec) - {'elements', 'camera'}:
        raise CanvasError('A visual block is {"elements": [...], "camera": [...] (optional)}')
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
        if 'moveTo' in element:
            move = element['moveTo']
            if not isinstance(move, dict) or set(move) - {'at', 'delay', 'x', 'y', 'dur'} or not {'x', 'y'} <= set(move) or type(move.get('at', 0)) is not int:
                raise CanvasError(f'{where}: "moveTo" is {{"at": sentence, "delay": seconds, "x": X, "y": Y, "dur": seconds}}')
            if 'plot' in element or 'x' not in element or 'y' not in element:
                raise CanvasError(f'{where}: only elements placed with x and y can move')
            row['moveTo'] = {'at': min(move.get('at', 0), len(sentences) - 1), 'delay': _number(move.get('delay', 0), 0, 10, f'{where} moveTo delay'),
                             'x': _number(move['x'], 0, 1920, f'{where} moveTo x'), 'y': _number(move['y'], 0, 1080, f'{where} moveTo y'),
                             'dur': _number(move.get('dur', .9), .2, 6, f'{where} moveTo dur')}
        if 'dim' in element:
            dim = element['dim']
            if not isinstance(dim, dict) or set(dim) - {'at', 'delay'} or type(dim.get('at', 0)) is not int:
                raise CanvasError(f'{where}: "dim" is {{"at": sentence, "delay": seconds}}')
            row['dim'] = {'at': min(dim.get('at', 0), len(sentences) - 1), 'delay': _number(dim.get('delay', 0), 0, 10, f'{where} dim delay')}
        if 'typing' in element:
            if type(element['typing']) is not bool or element['type'] not in ('bubble', 'text'):
                raise CanvasError(f'{where}: "typing": true works on bubble and text elements')
            row['typing'] = element['typing']
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
    result = {'elements': clean}
    if 'camera' in spec:
        result['camera'] = _camera(spec['camera'], sentences)
    return result


def _camera(moves, sentences):
    """Zooms into parts of the stage: [{"at", "delay", "x", "y", "zoom", "dur"}]; zoom 1 shows everything."""
    if not isinstance(moves, list) or not 1 <= len(moves) <= 8:
        raise CanvasError('camera lists 1 to 8 moves')
    clean = []
    for index, move in enumerate(moves, 1):
        where = f'camera move {index}'
        if not isinstance(move, dict) or set(move) - {'at', 'delay', 'x', 'y', 'zoom', 'dur'} or type(move.get('at', 0)) is not int:
            raise CanvasError(f'{where}: a move is {{"at": sentence, "delay": seconds, "x": X, "y": Y, "zoom": 1-3, "dur": seconds}}')
        clean.append({'at': min(move.get('at', 0), len(sentences) - 1), 'delay': _number(move.get('delay', 0), 0, 10, f'{where} delay'),
                      'x': _number(move.get('x', 960), 0, 1920, f'{where} x'), 'y': _number(move.get('y', 540), 0, 1080, f'{where} y'),
                      'zoom': _number(move.get('zoom', 1), 1, 3, f'{where} zoom'), 'dur': _number(move.get('dur', 1.2), .2, 6, f'{where} dur')})
    return clean


# ---- Layout check: estimates of what the renderer draws (renderer/src/canvas.ts uses the same sizes) ----
CHAR = .56                    # average bold character width, as a share of the font size
TEXT_SIZES = {'title': 140, 'h2': 64, 'body': 34, 'small': 28}
CAPTION_TOP = 945             # the caption bar starts here
# Overlays meant to sit on other elements: connectors, data drawn on plots, and small badges.
OVERLAYS = {'arrow', 'mover', 'line', 'points', 'curve', 'dot', 'segments', 'region'}
BADGES = {'check', 'cross', 'icon'}


def _lines(text, size, width):
    return max(1, math.ceil(len(text) * size * CHAR / max(1, width)))


def bounds(row):
    """(x0, y0, x1, y1) of a validated element, or None for overlays without a fixed footprint."""
    t, x, y = row['type'], row.get('x', 960), row.get('y', 540)
    if t in OVERLAYS:
        return None
    if t == 'box':
        w = row.get('w') or min(760, max(240, len(row.get('text', '')) * 40 * CHAR + 90))
        lines = _lines(row.get('text', ''), 40, w - 50)
        subs = _lines(row['sub'], 28, w - 50) if row.get('sub') else 0
        h = max(row.get('h') or 120, lines * 48 + (subs * 36.4 + 10 if subs else 0) + (70 if row.get('icon') else 0) + 56)
        return x - w / 2, y - h / 2, x + w / 2, y + h / 2
    if t in ('pill', 'stamp'):
        size = 34 if t == 'pill' else 64
        w, h = len(row['text']) * size * CHAR + (60 if t == 'pill' else 70), (68 if t == 'pill' else 110)
        return x - w / 2, y - h / 2, x + w / 2, y + h / 2
    if t == 'bubble':
        w = row.get('w', 900)
        h = _lines(row['text'], 34, w - 70) * 34 * 1.35 + 60
        return x, y, x + w, y + h
    if t in ('text', 'headline', 'counter'):
        size = TEXT_SIZES['h2' if t == 'headline' else row.get('size', 'h2' if t == 'counter' else 'body')]
        text = row.get('text') or f"{row.get('prefix', '')}{row.get('value', '')}{row.get('suffix', '')}"
        if t == 'headline':
            x, y = 960, row.get('y', 210)
        # Text that would leave the frame is drawn smaller to fit (renderer fitText), as is its estimate here.
        room = {'left': 1880 - x, 'right': x - 40}.get(row.get('align'), 2 * min(x - 40, 1880 - x))
        size = max(16, min(size, room / max(1, len(text) * CHAR)))
        w = len(text) * size * CHAR
        left = {'left': x, 'right': x - w}.get(row.get('align'), x - w / 2)
        return left, y - size / 2, left + w, y + size / 2
    if t in ('check', 'cross', 'ring'):
        r = row.get('r', 36 if t != 'ring' else 100)
        return x - r, y - r, x + r, y + r
    if t == 'icon':
        r = row.get('size', 96) / 2
        return x - r, y - r, x + r, y + r
    if t == 'bar':
        return x, y, x + row['w'], y + row['h']
    if t == 'bracket':
        return row['x1'], row['y'] - 50, row['x2'], row['y'] + (115 if row.get('label') else 0)
    if t == 'table':
        columns = max(len(r) for r in row['rows'])
        return x, y, x + columns * row.get('colWidth', 220), y + len(row['rows']) * row.get('rowHeight', 72)
    if t in ('plot', 'network'):
        w, h = row['w'], row['h']
        return x - w / 2, y - h / 2, x + w / 2, y + h / 2
    return None


def _name(row):
    return f'{row["type"]} "{row["text"]}"' if row.get('text') else row['type'] + (f' "{row["id"]}"' if row.get('id') else '')


def layout_issues(spec):
    """Warnings about elements that collide, leave the frame or sit under the caption bar."""
    rows = spec['elements']
    shown = []
    for row in rows:
        box = bounds(row)
        if box is None:
            continue
        start = (row['at'], row.get('delay', 0))
        end = (row['out']['at'], row['out'].get('delay', 0)) if 'out' in row else (10**6, 0)
        shown.append((row, box, start, end))
    issues = []
    for row, (x0, y0, x1, y1), _, _ in shown:
        if x0 < 0 or x1 > 1920 or y0 < 100:
            issues.append(f'{_name(row)} reaches past the edge of the frame')
        elif y1 > CAPTION_TOP + 10:
            issues.append(f'{_name(row)} reaches under the caption bar (keep it above y {CAPTION_TOP})')
    for i, (a, ba, sa, ea) in enumerate(shown):
        for b, bb, sb, eb in shown[i + 1:]:
            if ea <= sb or eb <= sa:
                continue  # never on screen together
            # One fading out as the other fades in, within the same sentence, is a hand-over, not a clash.
            if ea[0] == sb[0] and 0 <= ea[1] - sb[1] < .6 or eb[0] == sa[0] and 0 <= eb[1] - sa[1] < .6:
                continue
            if {a['type'], b['type']} & BADGES or 'plot' in {a['type'], b['type']} and {a['type'], b['type']} & {'text', 'counter', 'pill', 'stamp', 'bubble'}:
                continue  # badges and labels placed on a plot sit on other elements by design
            if ba == bb:
                continue  # the same footprint redrawn, e.g. to recolour a box
            overlap_w, overlap_h = min(ba[2], bb[2]) - max(ba[0], bb[0]), min(ba[3], bb[3]) - max(ba[1], bb[1])
            if overlap_w > 12 and overlap_h > 12:
                inside = lambda p, q: p[0] >= q[0] and p[1] >= q[1] and p[2] <= q[2] and p[3] <= q[3]
                if a['type'] == 'ring' and inside(bb, ba) or b['type'] == 'ring' and inside(ba, bb):
                    continue  # a label inside a ring
                issues.append(f'{_name(a)} overlaps {_name(b)}')
    return issues


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
        timed_row = {k: v for k, v in row.items() if k not in ('at', 'delay', 'word', 'out', 'pulse', 'moveTo', 'dim')}
        timed_row['t'] = moment(row['at'], row['delay'], row.get('word'))
        if 'out' in row:
            timed_row['tOut'] = moment(row['out']['at'], row['out']['delay'])
        if 'pulse' in row:
            timed_row['tPulse'] = moment(row['pulse'], 0)
        if 'moveTo' in row:
            move = row['moveTo']
            timed_row['move'] = {'t': moment(move['at'], move['delay']), 'x': move['x'], 'y': move['y'], 'dur': move['dur']}
        if 'dim' in row:
            timed_row['tDim'] = moment(row['dim']['at'], row['dim']['delay'])
        elements.append(timed_row)
    result = {'elements': elements}
    if spec.get('camera'):
        result['camera'] = [{'t': moment(m['at'], m['delay']), 'x': m['x'], 'y': m['y'], 'zoom': m['zoom'], 'dur': m['dur']} for m in spec['camera']]
    return result
