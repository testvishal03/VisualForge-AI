"""YouTube title options, SEO description and tags written by Claude alongside the script.

Claude ends its answer with a block like

    ```publish
    {"titles": ["Machine Learning Explained Visually (No Math)", ...],
     "description": "Two hook lines with the main keyword...\n\nWhat you'll learn...",
     "tags": ["machine learning", "machine learning for beginners", ...],
     "hashtags": ["MachineLearning", "AI", "DataScience"]}
    ```

The block is never narrated. It is checked against YouTube's limits; the publish kit then
combines the description with chapter times measured from the finished video.
"""
import json
import re

FENCE = re.compile(r'^```\s*publish\s*\n(.*?)\n```\s*$', re.S | re.M | re.I)
BARE = re.compile(r'^[ \t]*publish[ \t]*\n(?=[ \t]*\{)', re.M | re.I)
TITLE_LIMIT, DESCRIPTION_LIMIT, TAGS_LIMIT = 100, 4500, 500   # YouTube: 100, 5000 (room for chapters), 500


def extract(text):
    """(text without the publish block, parsed block or None, error message or None)."""
    text = text.replace('\r\n', '\n')
    match = FENCE.search(text)
    if match:
        raw, start, end = match[1], match.start(), match.end()
    else:
        bare = BARE.search(text)
        if not bare:
            return text, None, None
        begin = bare.end() + len(text[bare.end():]) - len(text[bare.end():].lstrip(' \t'))
        try:
            _, stop = json.JSONDecoder().raw_decode(text, begin)
        except ValueError:
            closing = re.compile(r'^\}\s*$', re.M).search(text, begin)
            stop = closing.end() if closing else len(text)
        raw, start, end = text[begin:stop], bare.start(), stop
    rest = (text[:start].rstrip() + '\n\n' + text[end:].lstrip()).strip()
    try:
        return rest, validate(json.loads(raw)), None
    except ValueError as exc:
        return rest, None, f'Publish block: {exc}'


def validate(block):
    """A clean copy of the publish block, or ValueError naming the problem."""
    if not isinstance(block, dict) or set(block) - {'titles', 'description', 'tags', 'hashtags', 'thumbnail', 'shorts'}:
        raise ValueError('expected {"titles": [...], "description": "...", "tags": [...], "hashtags": [...], "thumbnail": {...}}')
    titles = block.get('titles', [])
    if not isinstance(titles, list) or not 1 <= len(titles) <= 8 or any(not isinstance(t, str) or not t.strip() for t in titles):
        raise ValueError('titles must list 1 to 8 titles')
    titles = [re.sub(r'\s+', ' ', t).strip() for t in titles]
    if any(len(t) > TITLE_LIMIT for t in titles):
        raise ValueError(f'titles must be at most {TITLE_LIMIT} characters (YouTube limit)')
    description = block.get('description', '')
    if not isinstance(description, str) or len(description) > DESCRIPTION_LIMIT:
        raise ValueError(f'description must be text of at most {DESCRIPTION_LIMIT} characters')
    if '<' in description or '>' in description:
        raise ValueError('YouTube does not allow < or > in descriptions')
    tags = block.get('tags', [])
    if not isinstance(tags, list) or any(not isinstance(t, str) or not t.strip() for t in tags):
        raise ValueError('tags must be a list of words or phrases')
    tags = list(dict.fromkeys(t.strip().strip('#') for t in tags if t.strip().strip('#')))
    while tags and len(','.join(tags)) > TAGS_LIMIT:
        tags.pop()  # YouTube counts at most 500 characters of tags; the least important come last
    hashtags = block.get('hashtags', [])
    if not isinstance(hashtags, list) or len(hashtags) > 15 or any(not isinstance(h, str) for h in hashtags):
        raise ValueError('hashtags must list up to 15 words')
    hashtags = [re.sub(r'[^\w]', '', h) for h in hashtags if re.sub(r'[^\w]', '', h)][:5]
    result = {'titles': titles, 'description': description.strip(), 'tags': tags, 'hashtags': hashtags}
    if 'thumbnail' in block:
        result['thumbnail'] = thumbnail(block['thumbnail'])
    if 'shorts' in block:
        result['shorts'] = shorts(block['shorts'])
    return result


def shorts(specs):
    """1-3 vertical Shorts: each 1-3 consecutive scenes, a hook line and an optional title."""
    if not isinstance(specs, list) or not 1 <= len(specs) <= 3:
        raise ValueError('shorts lists 1 to 3 shorts')
    clean = []
    for index, spec in enumerate(specs, 1):
        where = f'short {index}'
        if not isinstance(spec, dict) or set(spec) - {'scenes', 'hook', 'title'} or 'scenes' not in spec or 'hook' not in spec:
            raise ValueError(f'{where} is {{"scenes": [3, 4], "hook": "a punchy question or claim", "title": "..."}}')
        scenes = spec['scenes']
        if not isinstance(scenes, list) or not 1 <= len(scenes) <= 3 or any(type(n) is not int or n < 1 for n in scenes) \
                or scenes != list(range(scenes[0], scenes[0] + len(scenes))):
            raise ValueError(f'{where}: scenes must be 1 to 3 consecutive scene numbers')
        hook = spec['hook']
        if not isinstance(hook, str) or not 3 <= len(hook) <= 70:
            raise ValueError(f'{where}: hook must be 3 to 70 characters')
        row = {'scenes': scenes, 'hook': hook.strip()}
        if spec.get('title'):
            if not isinstance(spec['title'], str) or len(spec['title']) > TITLE_LIMIT:
                raise ValueError(f'{where}: title must be at most {TITLE_LIMIT} characters')
            row['title'] = spec['title'].strip()
        clean.append(row)
    return clean


def thumbnail(spec):
    """2-4 big cover words (one may be highlighted), the scene to show, and an optional badge."""
    if not isinstance(spec, dict) or set(spec) - {'text', 'highlight', 'scene', 'badge'} or 'text' not in spec or 'scene' not in spec:
        raise ValueError('thumbnail is {"text": "2-4 words", "highlight": "one of them", "scene": number, "badge": "EPISODE 1"}')
    text = spec['text']
    if not isinstance(text, str) or not 1 <= len(text.split()) <= 4 or len(text) > 28:
        raise ValueError('thumbnail text must be 1 to 4 words, at most 28 characters')
    if type(spec['scene']) is not int or spec['scene'] < 1:
        raise ValueError('thumbnail scene must be a scene number from 1')
    clean = {'text': text.strip(), 'scene': spec['scene']}
    if spec.get('highlight'):
        if not isinstance(spec['highlight'], str) or spec['highlight'].casefold() not in [w.casefold() for w in text.split()]:
            raise ValueError('thumbnail highlight must be one of the thumbnail words')
        clean['highlight'] = spec['highlight']
    if spec.get('badge'):
        if not isinstance(spec['badge'], str) or len(spec['badge']) > 20:
            raise ValueError('thumbnail badge must be at most 20 characters')
        clean['badge'] = spec['badge']
    return clean


def title_notes(title):
    """Quick click-through checks for a title, shown next to it in the publish kit."""
    notes = []
    if len(title) > 60:
        notes.append('may be cut off in search (over 60 characters)')
    if len(title) < 25:
        notes.append('short: room for a keyword or benefit')
    if title.isupper():
        notes.append('all capitals reads as spam')
    return notes
