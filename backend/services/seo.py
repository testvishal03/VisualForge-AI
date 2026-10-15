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
    if not isinstance(block, dict) or set(block) - {'titles', 'description', 'tags', 'hashtags'}:
        raise ValueError('expected {"titles": [...], "description": "...", "tags": [...], "hashtags": [...]}')
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
    return {'titles': titles, 'description': description.strip(), 'tags': tags, 'hashtags': hashtags}


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
