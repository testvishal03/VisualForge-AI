"""Turn a pasted page (Markdown, notes or a production script) into narration, keeping the author's words.

This is formatting conversion, not writing. Two layouts are understood:

- A page or notes: headings become scenes and are read as a lead sentence, list items become
  sentences, numbered steps gain "First / Next / Finally", and bare example lines are read as
  quoted examples.
- A production script (sections with **Voiceover** / **Visual** labels): only the voiceover is
  read, "Scene N — Title" headings are scene breaks rather than narration, and visual notes,
  metadata and code or diagram blocks are skipped.

Symbols a voice would read aloud (emoji, arrows, Markdown marks) are removed. The result goes to
the script editor for review before anything is generated.
"""
import re

ORDINALS = ['First', 'Next', 'Then', 'After that', 'Finally']
SYMBOLS = {'&': ' and ', '→': ' to ', '->': ' to ', '=>': ' to ', '←': ' from ', '=': ' is ', '+': ' plus ', '%': ' percent'}
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-➿️‍⬀-⯿]')
MIN_SECTION_WORDS = 8
SPOKEN_LABELS = {'voiceover', 'voice over', 'vo', 'narration', 'narrator', 'script', 'audio', 'speaker'}
SILENT_LABELS = {'visual', 'visuals', 'on-screen text', 'on screen text', 'onscreen text', 'b-roll', 'broll', 'graphics',
                 'animation', 'screen', 'scene', 'shot', 'camera', 'music', 'sfx', 'sound', 'note', 'notes', 'direction', 'duration'}
LABEL = re.compile(r'^\*\*([^*]{1,30})\*\*:?\s*$|^([A-Za-z][A-Za-z /-]{1,25}):\s*$')
LIST_ITEM = re.compile(r'^(?:[-*+•]\s+|\d+[.)]\s+|\*\*\s*\d+[.)])')
SENTENCE_END = re.compile(r'[.!?:]["\'”’)*]*\\?\s*$')


def clean(text):
    """Plain spoken text from Markdown."""
    text = EMOJI.sub('', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)               # images
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)            # links keep their words
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'^\s*>\s?', '', text)                            # block quotes
    # "**Label**rest" and "**Label**\"quote\"" were written as a label followed by its text.
    text = re.sub(r'\*\*([^*]+)\*\*(?=[^\s*.,!?])', lambda m: m[1].rstrip(':.') + ': ', text)
    text = re.sub(r'(\*\*|__|\*|_)(\S[^*_]*?\S|\S)\1', r'\2', text)  # emphasis marks
    text = text.replace('\\|', '|').replace('\\', ' ').replace('“', '"').replace('”', '"').replace('’', "'")
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


def label_of(line):
    """A known speaker or production label on its own line; "A user asks:" is narration, not a label."""
    match = LABEL.match(line.strip())
    name = (match[1] or match[2]).strip().rstrip(':').lower() if match else None
    return name if name in SPOKEN_LABELS | SILENT_LABELS else None


def blocks(markdown):
    """Document order as [('heading', (level, text)) | ('label', name) | ('para', [lines]) | ('item', line)]."""
    result, para, fenced = [], [], False
    def flush():
        if para:
            result.append(('para', list(para)))
            para.clear()
    for raw in markdown.replace('\r\n', '\n').split('\n'):
        stripped = raw.strip()
        if stripped.startswith('```'):
            flush()
            fenced = not fenced   # code and ASCII diagrams are for the screen, not the voice
            continue
        if fenced:
            continue
        heading = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if heading:
            flush()
            result.append(('heading', (len(heading[1]), heading[2])))
        elif not stripped or re.fullmatch(r'[-*_=|:\s→>↓]+', stripped):
            flush()
        elif label_of(stripped) is not None:
            flush()
            result.append(('label', label_of(stripped)))
        elif LIST_ITEM.match(stripped):
            flush()
            result.append(('item', stripped))
        elif para and not SENTENCE_END.search(para[-1]):
            # A line that does not end a sentence continues on the next line (wrapped text).
            para[-1] = para[-1] + ' ' + stripped
        else:
            para.append(stripped)
    flush()
    return result


def production(parsed):
    """A production script labels what is spoken (Voiceover) apart from visual notes."""
    return any(kind == 'label' and value in SPOKEN_LABELS for kind, value in parsed)


def parse(markdown):
    """(title, scripted, [(spoken heading or None, [source lines])]) honouring speaker labels."""
    parsed = blocks(markdown)
    scripted = production(parsed)
    title, sections, current = None, [], [None, []]
    speaking, labelled, started = not scripted, False, False
    for kind, value in parsed:
        if kind == 'heading':
            level, text = value
            if level == 1 and title is None:
                title = clean(text).rstrip('.')
                continue
            if current[0] is not None or current[1]:
                sections.append(current)
            # Production headings ("Scene 3 — What Is a Vector Database?") break scenes but are not read.
            current = [None if scripted else clean(text), []]
            speaking, labelled, started = not scripted, False, True
            continue
        if kind == 'label':
            labelled = True
            speaking = value in SPOKEN_LABELS or (not scripted and value not in SILENT_LABELS)
            continue
        if scripted and not started:
            continue   # metadata between the title and the first scene ("Video 5 | Target duration ...")
        if speaking or (scripted and not labelled):
            current[1].extend(value if kind == 'para' else [value])
    if current[0] is not None or current[1]:
        sections.append(current)
    return title, scripted, sections


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
        # "A user asks:" followed by a quote, or "Examples include:" followed by a short item, is one sentence.
        if spoken and spoken[-1].endswith(':') and (text.startswith('"') and len(text.split()) <= 25 or len(text.split()) <= 6):
            spoken[-1] = spoken[-1] + ' ' + (text if re.search(r'[.!?]"?$', text) else text + '.')
            continue
        if numbered:
            word = ORDINALS[min(step, len(ORDINALS) - 1)]
            step += 1
            text = f'{word}, {text[0].lower() + text[1:]}' if not re.match(r'[A-Z]{2}', text) else f'{word}, {text}'
        # A label followed by its explanation reads naturally as two sentences.
        parts = [p for p in re.split(r'(?<=[a-z0-9)])\:\s+(?=[A-Z])', text) if p.strip()]
        for n, part in enumerate(parts):
            # A closing colon stays for now: a quote on the next line may complete it.
            spoken.append(part.strip() if n == len(parts) - 1 and part.rstrip().endswith(':') else sentence(part))
    spoken = [sentence(s) if s.endswith(':') else s for s in spoken]
    if step >= 2:
        # The last numbered step is announced as the final one.
        last = max(i for i, s in enumerate(spoken) if s.startswith(tuple(ORDINALS)))
        spoken[last] = re.sub(r'^(?:Next|Then|After that), ', 'Finally, ', spoken[last])
    return [s for s in spoken if s]


def looks_like_markdown(text):
    """Pasted Markdown (headings, label lines, fences, rules); two signals, so plain scripts are left alone."""
    lines = text.replace('\r\n', '\n').split('\n')
    signals = [
        any(re.match(r'^#{1,6}\s+\S', l.strip()) for l in lines),
        any(label_of(l) for l in lines) or sum(bool(re.fullmatch(r'\*\*[^*]+\*\*\s*', l.strip())) for l in lines) >= 2,
        any(l.strip().startswith('```') for l in lines),
        any(re.fullmatch(r'-{3,}|\*{3,}|_{3,}', l.strip()) for l in lines),
        sum(bool(re.match(r'^\s*[-*+]\s+\S', l)) for l in lines) >= 3,
        '**' in text and sum(l.count('**') for l in lines) >= 4,
    ]
    return sum(signals) >= 2


def page_to_script(markdown):
    """{'title', 'script' (one paragraph per section), 'scenes', 'words', 'notes'}."""
    if not isinstance(markdown, str) or not markdown.strip():
        raise ValueError('Paste a page or notes to convert.')
    title, scripted, sections = parse(markdown)
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
    if scripted:
        notes.append('Production script detected: only the Voiceover is read; scene headings, visual notes, metadata and diagrams are skipped.')
    if EMOJI.search(markdown):
        notes.append('Emoji were removed so the voice does not read them aloud.')
    if re.search(r'^\s*(?:\*\*)?\s*\d+[.)]', markdown, re.M):
        notes.append('Numbered steps are read as First / Next / Finally.')
    notes.append('Review the narration: the voice reads exactly this text.')
    return {'title': title, 'script': script, 'scenes': len(paragraphs), 'words': len(script.split()), 'notes': notes}
