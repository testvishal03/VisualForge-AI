"""Turn a pasted page (Markdown or plain notes) into narration, keeping the author's words.

This is formatting conversion, not writing: headings become scenes, list items become spoken
sentences, numbered steps gain "First / Next / Finally", and quoted examples stay verbatim.
Symbols a voice would read aloud (emoji, arrows, Markdown marks) are removed. The result goes
to the script editor for review before anything is generated.
"""
import re

ORDINALS = ['First', 'Next', 'Then', 'After that', 'Finally']
SYMBOLS = {'&': ' and ', '→': ' to ', '->': ' to ', '=>': ' to ', '←': ' from ', '=': ' is ', '+': ' plus ', '%': ' percent'}
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-➿️‍⬀-⯿]')
MIN_SECTION_WORDS = 8


def clean(text):
    """Plain spoken text from one Markdown line."""
    text = EMOJI.sub('', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)               # images
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)            # links keep their words
    text = re.sub(r'`([^`]*)`', r'\1', text)
    # "**Label**rest" and "**Label**\"quote\"" were written as a label followed by its text.
    text = re.sub(r'\*\*([^*]+)\*\*(?=\S)', lambda m: m[1].rstrip(':.') + ': ', text)
    text = re.sub(r'(\*\*|__|\*|_)(\S[^*_]*?\S|\S)\1', r'\2', text)  # emphasis marks
    text = text.replace('\\', ' ').replace('“', '"').replace('”', '"').replace('’', "'")
    for symbol, word in SYMBOLS.items():
        text = text.replace(symbol, word)
    text = re.sub(r'\s+([,.!?:;])', r'\1', re.sub(r'\s+', ' ', text)).strip(' -*#>|')
    return text


def sentence(text):
    """Close a fragment as a spoken sentence; a trailing colon or dash becomes a full stop."""
    text = text.strip().rstrip(':;-,').strip()
    if not text:
        return ''
    text = text[0].upper() + text[1:]
    return text if re.search(r'[.!?]["\')]?$', text) else text + '.'


def parse(markdown):
    """[(heading or None, [lines])] in document order, plus the page title."""
    title, sections, current = None, [], [None, []]
    for raw in markdown.replace('\r\n', '\n').split('\n'):
        line = raw.strip()
        heading = re.match(r'^(#{1,6})\s+(.*)$', line)
        if heading and len(heading[1]) == 1 and title is None:
            title = clean(heading[2]).rstrip('.')
            continue
        if heading:
            if current[0] is not None or current[1]:
                sections.append(current)
            current = [clean(heading[2]), []]
            continue
        if line and not re.fullmatch(r'[-*_=|:\s→>]+', line):
            current[1].append(line)
    if current[0] is not None or current[1]:
        sections.append(current)
    return title, sections


def narrate(lines):
    """Spoken sentences for a section; numbered steps are read in order with ordinal words."""
    spoken, step = [], 0
    for line in lines:
        # "**1. Feed it**Billions of texts" is a numbered label followed by its explanation.
        line = re.sub(r'^\*\*\s*(\d+[.)])\s*([^*]+?)\*\*\s*', lambda m: f'{m[1]} {m[2].rstrip(":.")}: ', line)
        numbered = re.match(r'^(\d+)[.)]\s+(.*)$', line)
        bullet = re.match(r'^[-*+•]\s+(.*)$', line)
        text = clean(numbered[2] if numbered else bullet[1] if bullet else line)
        if not re.search(r'[A-Za-z]', text):
            continue
        # A bare lowercase fragment with no punctuation is an example being shown, not a sentence.
        if not numbered and not bullet and re.fullmatch(r"[a-z][\w\s'-]{2,60}", text) and len(text.split()) <= 10:
            spoken.append(f'For example, "{text}".')
            continue
        if numbered:
            word = ORDINALS[min(step, len(ORDINALS) - 1)]
            step += 1
            text = f'{word}, {text[0].lower() + text[1:]}' if not re.match(r'[A-Z]{2}', text) else f'{word}, {text}'
        # A label followed by its explanation reads naturally as two sentences.
        parts = [p for p in re.split(r'(?<=[a-z0-9)])\:\s+(?=[A-Z])', text) if p.strip()]
        spoken.extend(sentence(p) for p in parts)
    if step >= 2:
        # The last numbered step is announced as the final one.
        last = max(i for i, s in enumerate(spoken) if s.startswith(tuple(ORDINALS)))
        spoken[last] = re.sub(r'^(?:Next|Then|After that), ', 'Finally, ', spoken[last])
    return [s for s in spoken if s]


def page_to_script(markdown):
    """(title, narration script with one paragraph per section, notes about what changed)."""
    if not isinstance(markdown, str) or not markdown.strip():
        raise ValueError('Paste a page or notes to convert.')
    title, sections = parse(markdown)
    paragraphs, notes, carry = [], [], []
    for heading, lines in sections:
        spoken = narrate(lines)
        if heading:
            spoken = [sentence(heading)] + spoken
        words = sum(len(s.split()) for s in spoken)
        if words < MIN_SECTION_WORDS:
            # Too short to be its own scene; it joins the next section.
            carry.extend(spoken)
            continue
        paragraphs.append(' '.join(carry + spoken))
        carry = []
    if carry:
        if paragraphs:
            paragraphs[-1] += ' ' + ' '.join(carry)
        else:
            paragraphs.append(' '.join(carry))
    if not paragraphs:
        raise ValueError('No readable text was found in the page.')
    script = '\n\n'.join(paragraphs)
    if EMOJI.search(markdown):
        notes.append('Emoji were removed so the voice does not read them aloud.')
    if re.search(r'^\s*(?:\*\*)?\s*\d+[.)]', markdown, re.M):
        notes.append('Numbered steps are read as First / Next / Finally.')
    notes.append('Review the narration: the voice reads exactly this text.')
    return {'title': title, 'script': script, 'scenes': len(paragraphs), 'words': len(script.split()), 'notes': notes}
