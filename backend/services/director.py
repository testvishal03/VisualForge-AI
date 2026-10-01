"""Extractive visual direction: authored narration stays authoritative.

Cues reference spoken sentence indices, not guessed timestamps. The audio stage
provides measured boundaries after synthesizing those exact sentences.
"""
import re
from backend.schemas.video_schema import VideoScript, Scene, words

ICONS = {'idea', 'book', 'database', 'chip', 'shield', 'clock', 'leaf', 'people', 'chart', 'sun', 'cloud', 'water', 'rain', 'network', 'gear', 'battery', 'globe'}


def sentences(text):
    # Protect common abbreviations and initials; decimal points lack following spaces.
    protected = re.sub(r'\b(?:Mr|Mrs|Ms|Dr|Prof|e\.g|i\.e|[A-Z])\.', lambda m: m[0].replace('.', '\u2024'), text)
    return [s.replace('\u2024', '.').strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\u201c])', protected) if s.strip()]


def short(text, limit=70):
    text = re.sub(r'^\s*(?:first|second|third|then|next|finally|in contrast|for example)[,:]?\s+', '', text, flags=re.I)
    if len(text) <= limit:
        return text
    return text[:limit-3].rsplit(' ', 1)[0].rstrip(' ,;:') + '...'


# Openers that add nothing to a headline: discourse fillers and step words.
HEADLINE_LEAD_IN = re.compile(r"^(?:(?:so|but|and|now|then|also|of course|in simple terms|in other words|think of|first|second|third|next|"
                              r"finally|lastly|here's the (?:secret|idea|key)|remember that)\b[,:]?\s*)+", re.I)
# A headline never ends on these: articles, prepositions, conjunctions, auxiliaries and loose modifiers.
DANGLING_END = set("""a an the and or but nor so yet of to in on at by for from with into onto over under about as than
that this these those which who whom whose what when where why how if is are was were be been being am do does did has have
had can could will would should may might must shall not no very even just only also too more most less least much many few
some any each every all both such same other own entire whole huge tiny little big small large great next last first second
third its their our your my his her we you they it i""".split())
# Cutting just before one of these keeps a whole phrase ("every document | to the language model").
PHRASE_BOUNDARY = set('to in on at for with by from into about that which who whose when whenever where while because and or but so than until as if'.split())


def ends_well(token):
    word = re.sub(r"[^\w'-]", '', token).lower()
    return bool(word) and word not in DANGLING_END and not word.endswith('ly')


def headline_for(sentence):
    """A short headline in the sentence's own words that ends at a natural boundary.

    Fillers are dropped; a sentence that fits is kept whole; otherwise its main clause, or the
    longest prefix ending on a content word, preferably right before a joining word.
    """
    text = sentence.strip().replace('\u2019', "'").rstrip('.!?').strip()
    text = HEADLINE_LEAD_IN.sub('', text).strip() or text
    if len(words(text)) > HEADLINE_WORDS:
        clause = re.split(r',\s+(?=[A-Za-z"\u201c])|;\s|:\s|\s(?:and|but|which|because|while|whereas|so that)\s', text, maxsplit=1)[0].strip()
        if 3 <= len(words(clause)) <= HEADLINE_WORDS:
            text = clause
        else:
            tokens = text.split()
            fits = lambda part: len(words(' '.join(part))) <= HEADLINE_WORDS and ends_well(part[-1])
            choice = next((tokens[:n] for n in range(len(tokens) - 1, 2, -1)
                           if fits(tokens[:n]) and tokens[n].lower().strip(',') in PHRASE_BOUNDARY), None)
            choice = choice or next((tokens[:n] for n in range(len(tokens), 1, -1) if fits(tokens[:n])), tokens[:2])
            text = ' '.join(choice)
    result = short(text, 76).rstrip('.,:;!?')
    return result[:1].upper() + result[1:]


# Nine words, leaving room for a " - N" duplicate suffix within the schema limit of ten.
HEADLINE_WORDS = 9
# Openings that introduce the video rather than name its subject.
FILLER_OPENING = re.compile(r"^(?:in (?:the|this|today's) (?:previous |last |next )?(?:video|lesson|episode)|welcome|hi|hello|hey|today|let's|so,|okay|alright)\b", re.I)


def title_for(paragraphs):
    """An untitled script is named after its opening, unless that opening is filler; then after the
    concept the narration repeats most (for example "Embeddings"), which is still the script's own word."""
    first = sentences(paragraphs[0])[0]
    if not FILLER_OPENING.match(first.strip()):
        return headline_for(first)
    from collections import Counter
    from backend.services.key_terms import candidates
    text = ' '.join(paragraphs)
    # Count every mention of each concept, singular and plural together ("embedding", "embeddings").
    stems = {re.sub(r'(?:es|s)$', '', phrase.casefold()) for phrase in candidates(text) if len(phrase) >= 5}
    counts = {stem: Counter(m.casefold() for m in re.findall(rf'\b{re.escape(stem)}(?:s|es)?\b', text, re.I)) for stem in stems}
    ranked = sorted(((sum(c.values()), len(stem), stem) for stem, c in counts.items()), reverse=True)
    if not ranked or ranked[0][0] < 3:
        return headline_for(first)
    form = counts[ranked[0][2]].most_common(1)[0][0]
    return form[:1].upper() + form[1:]


def headline_sentence(narration):
    """The first sentence with real words to headline a scene; a list of numbers makes a poor title."""
    parts = sentences(narration)
    readable = lambda part: len(re.findall(r'[A-Za-z]{3,}', part)) >= 3 and len(re.findall(r'\d', part)) * 3 < len(part)
    return next((part for part in parts if readable(part)), parts[0])


def script_to_video(title, script, max_words=None, max_scenes=120):
    if not isinstance(script, str) or not script.strip():
        raise ValueError('Paste a narration script.')
    # If script is passed as a file path, load from file automatically
    cleaned_path = script.strip(' "\'\t\r\n')
    if '\n' not in cleaned_path and len(cleaned_path) < 500:
        try:
            p = __import__('pathlib').Path(cleaned_path)
            if p.is_file():
                script = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            pass
    paragraphs = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', script.strip()) if p.strip()]
    title = title or title_for(paragraphs)
    count = len(words(' '.join(paragraphs)))
    if count < 1 or max_words is not None and count > max_words:
        raise ValueError(f'Use 30–{max_words} spoken words. Separate teaching points with blank lines.')
    from backend.services.scene_grouping import group_paragraphs
    chunks = group_paragraphs(paragraphs)
    if len(chunks) == 1:
        parts = sentences(chunks[0])
        for cut in range(1, len(parts)):
            a, b = ' '.join(parts[:cut]), ' '.join(parts[cut:])
            if min(len(words(a)), len(words(b))) >= 15:
                chunks = [a, b]
                break
    if not 1 <= len(chunks) <= max_scenes:
        raise ValueError(f'Use 2–{max_scenes} teaching paragraphs, each with 15–60 words.')
    scenes = []
    for index, narration in enumerate(chunks, 1):
        first = sentences(narration)[0]
        headline = (short(title, 76) if len(words(title)) <= HEADLINE_WORDS else headline_for(title)) if index == 1 else headline_for(headline_sentence(narration))
        if any(s['headline'].casefold() == headline.casefold() for s in scenes):
            headline = short(headline, 65) + f' — {index}'
        body = short(first, 180)
        if body == narration:
            body = short(first, min(120, max(25, len(first)//2)))
        if body == narration: body = 'Key idea'
        scenes.append(dict(id=index, headline=headline, body=body, narration=narration))
    return VideoScript.model_validate({'title': title, 'topic': title, 'scenes': scenes})


ICONS = {'sun', 'cloud', 'water', 'rain', 'network', 'gear', 'battery', 'globe', 'book',
         'database', 'chip', 'shield', 'clock', 'leaf', 'people', 'chart', 'idea',
         'brain', 'layers', 'lightning', 'math', 'code', 'atom', 'filter', 'token',
         'matrix', 'magnify', 'rocket', 'analog'}

ICON_PATTERNS = [
    (r'\btraining data\b|\bdata storage\b|\bdatabase\b', 'database'),
    (r'\b(tokens?|subwords?|characters?|vocabulary|bpe)\b', 'token'),
    (r'\b(context window|working space|container|capacity|buffer)\b', 'layers'),
    (r'\b(parameters|learned patterns|learned knowledge|weights|intelligence)\b', 'brain'),
    (r'\b(embedding|vector space|high-dimensional|matrix|lookup table)\b', 'matrix'),
    (r'\b(attention|transformers?|neural network|connections?|nodes?)\b', 'network'),
    (r'\b(retrieval|retrieve|rag|filter|selective|prun|trim)\b', 'filter'),
    (r'\b(search|locate|find|inspect|look up|catalog|zoom into)\b', 'magnify'),
    (r'\b(code|programming|python|script|syntax|operators?|variables?)\b', 'code'),
    (r'\b(compute|inference|speed|fast|performance|accelerat)\b', 'lightning'),
    (r'\b(math|numbers?|numerical|ids?|count|dimensions?)\b', 'math'),
    (r'\b(atomic|building blocks?|units?|pieces?)\b', 'atom'),
    (r'\b(knowledge base|documents?|library|storage)\b', 'database'),
    (r'\b(text|words?|sentences?|language|reading|books?)\b', 'book'),
    (r'\b(cost|usage|percent|growth|efficiency|billions?|millions?)\b', 'chart'),
    (r'\b(limits?|protect|safe|guardrail|error|exceed|boundary)\b', 'shield'),
    (r'\b(temporary|history|turns?|duration|time|schedule)\b', 'clock'),
    (r'\b(mechanism|pipeline|process|engine|system|machine)\b', 'gear'),
    (r'\b(user|human|chatbot|assistant|reader|people)\b', 'people'),
    (r'\b(world|universe|global|planet)\b', 'globe'),
    (r'\b(boost|advance|scale|future|rocket)\b', 'rocket'),
    (r'\b(analogy|compare|contrast|like a desk|like a container)\b', 'analog'),
    (r'\b(precipitation|rainfall|raindrops|rain)\b', 'rain'),
    (r'\b(cloud|condens)', 'cloud'),
    (r'\b(evapor|water|ocean|river)', 'water'),
    (r'\b(sun|solar)', 'sun'),
    (r'\b(batter|electric)', 'battery'),
    (r'\b(plant|leaf)', 'leaf'),
    (r'\b(concept|idea|insight|remember|principle)', 'idea'),
]

FALLBACK_ICONS = ['idea', 'book', 'gear', 'people', 'globe']

def choose_icon(text, recent=None):
    recent = list(recent or [])
    # Exact match for data in training data
    if re.search(r'\b(training data|data storage|database)\b', text, re.I):
        return 'database'
    scores = {}
    for pattern, icon in ICON_PATTERNS:
        matches = len(re.findall(pattern, text, re.I))
        if matches:
            penalty = 0
            if recent:
                if recent[-1] == icon: penalty += 1
                if len(recent) >= 2 and recent[-2] == icon: penalty += .5
                if icon in recent[-4:]: penalty += .25
            scores[icon] = matches * 3 - penalty
    if scores:
        candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    for cand in FALLBACK_ICONS:
        if not recent or cand != recent[-1]:
            return cand
    return 'idea'


def _extract_scene(scene, index, total, recent_icons=None):
    parts = sentences(scene.narration)
    text = scene.headline+' '+scene.narration
    numbered = [i for i, p in enumerate(parts) if re.match(r'(?:first|second|third|then|next|finally)\b', p, re.I)]
    contrast = next((i for i,p in enumerate(parts) if i and re.match(r'(?:whereas|however|in contrast|unlike|but)\b', p, re.I)), None)
    relation = re.search(r'\b(?:leads to|flows to|connects to|depends on|causes)\b', scene.narration, re.I)
    kind, items, cues = 'explanation', [], []
    if len(numbered) >= 3:
        kind, cues = 'process', numbered[:3]
        items = [short(parts[i]) for i in cues]
    elif contrast is not None:
        kind, cues = 'comparison', [0, contrast]
        items = [short(parts[i], 180) for i in cues]
    elif relation:
        for i, part in enumerate(parts):
            link = re.search(r'\b(?:leads to|flows to|connects to|depends on|causes)\b', part, re.I)
            if link and part[:link.start()].strip():
                kind, cues = 'relationship', [i, i]
                items = [short(part[:link.start()].strip()), short(part[link.start():])]
                break
    elif re.search(r'\b(?:example|case study)\b', scene.headline, re.I) or re.search(r'\b(?:for example|imagine|such as)\b', scene.narration, re.I):
        kind = 'example'
    elif index == 0:
        kind = 'title'
    elif index == total-1 or re.search(r'takeaway|summary|remember', text, re.I):
        kind = 'takeaway'

    if kind == 'explanation':
        if re.search(r'\b(simplified flow looks like|complete simplified flow|recap everything|flow looks like this|text\.\s*tokenizer\.\s*tokens)\b', text, re.I):
            kind = 'cycle'
            items = ['Text Input', 'Tokenizer', 'Tokens & IDs', 'Context Window']
            cues = list(range(min(len(items), max(1, len(parts)))))
        elif re.search(r'\b(retrieval-augmented|rag|knowledge base|retrieves? (?:only|a few)|searches the knowledge base)\b', text, re.I):
            kind = 'process'
            items = ['Knowledge Base Search', 'Retrieve Relevant Context', 'Generate Grounded Answer']
            cues = [0, min(1, len(parts)-1), min(2, len(parts)-1)]
        elif re.search(r'\b(mapped to a token id|mapped to numerical ids|text.*broken into.*tokens|tokenization gives the model|the tokenizer might break)\b', text, re.I):
            kind = 'process'
            items = ['Raw Text Input', 'Tokenizer Subwords', 'Numerical Token IDs']
            cues = [0, min(1, len(parts)-1), min(2, len(parts)-1)]
        elif re.search(r'\b(context becomes too large|older messages.*removed|trimming.*summarizing|handle this in different ways)\b', text, re.I):
            kind = 'process'
            items = ['Message Trimming', 'History Summarization', 'Selective Retrieval']
            cues = [0, min(1, len(parts)-1), min(2, len(parts)-1)]
        elif re.search(r'\b(tell me about python|who created it|follow a conversation|you ask one question.*assistant replies)\b', text, re.I):
            kind = 'timeline'
            items = ['Turn 1: Question', 'Turn 2: Answer', 'Turn 3: Pronoun Resolution']
            cues = list(range(min(len(items), max(1, len(parts)))))

        elif re.search(r'\b(entire word.*part of a word.*punctuation|token might be an entire word)\b', text, re.I):
            kind = 'components'
            items = ["Whole Words", "Subword Chunks", "Punctuation & Spaces"]
            cues = list(range(min(len(items), max(1, len(parts)))))
        elif re.search(r'\b(context can include|working space.*receive|inside that working space|container with a limited|system instructions take some space)\b', text, re.I):
            kind = 'components'
            items = ['System Instructions', 'Chat History', 'User Prompt', 'Retrieved Context']
            cues = list(range(min(len(items), max(1, len(parts)))))
        elif re.search(r'\b(what should be removed|what should be summarized|manage context carefully)\b', text, re.I):
            kind = 'components'
            items = ['Retain Core Prompt', 'Trim Old History', 'Summarize Chat', 'Retrieve On-Demand']
            cues = list(range(min(len(items), max(1, len(parts)))))
        elif re.search(r'\b(your prompt is context|conversation history is context|tool result can also become)\b', text, re.I):
            kind = 'components'
            items = ['System Persona', 'User Prompt', 'Conversation History', 'Tool Outputs']
            cues = list(range(min(len(items), max(1, len(parts)))))
        elif re.search(r'\b(code can also be split|symbols, punctuation, operators|ai is useful)\b', text, re.I):
            kind = 'example'
            items = []
            cues = []

        elif re.search(r'\b(word count and token count|one token does not always equal|simple word like.*hello.*multiple tokens)\b', text, re.I):
            kind = 'comparison'
            items = ['Word Count (Natural Language)', 'Token Count (Model Subunits)']
            cues = [0, min(1, len(parts)-1)]
        elif re.search(r'\b(different models can use different tokenizers|different models.*split differently|model-specific|one model may split.*another model)\b', text, re.I):
            kind = 'comparison'
            items = ['Model A Tokenizer (Split)', 'Model B Tokenizer (Single)']
            cues = [0, min(1, len(parts)-1)]
        elif re.search(r'\b(input tokens plus output tokens|shared between input and output|input is very small.*room for|input already consumes|room to generate its response)\b', text, re.I):
            kind = 'comparison'
            items = ['Input Tokens (Prompt + History)', 'Output Tokens (Available Response)']
            cues = [0, min(1, len(parts)-1)]
        elif re.search(r'\b(training creates.*context gives|context is not the same as the knowledge learned|parameters.*context window|model learns patterns.*parameters)\b', text, re.I):
            kind = 'comparison'
            items = ['Model Parameters (Permanent Weights)', 'Context Window (Temporary Scratchpad)']
            cues = [0, min(1, len(parts)-1)]
        elif re.search(r'\b(more context is not always better|relevant context|too much irrelevant)\b', text, re.I):
            kind = 'comparison'
            items = ['Targeted Relevant Context', 'Excess Irrelevant Context']
            cues = [0, min(1, len(parts)-1)]
        elif re.search(r'\b(ai models work with numbers|do not directly understand raw text)\b', text, re.I):
            kind = 'comparison'
            items = ['Human Language (Text)', 'Model Computation (Numbers)']
            cues = [0, min(1, len(parts)-1)]
        elif re.search(r'\b(two important ideas that affect|tokens and context windows)\b', text, re.I):
            kind = 'relationship'
            items = ['Token Units (Vocabulary)', 'Context Window (Capacity)']
            cues = [0, min(1, len(parts)-1)]

        elif re.search(r'\b(embeddings?|vectors?|vector space|high-dimensional|mathematically|meaning using numbers|tokens are still just ids)\b', text, re.I):
            kind = 'neural_net'
            items = ['Token IDs', 'Embedding Layer', 'Attention Head', 'Semantic Vector']
            cues = list(range(min(len(items), max(1, len(parts)))))
        elif re.search(r'\b(transformers?|attention|large language models process language)\b', text, re.I):
            kind = 'neural_net'
            items = ['Input Tokens', 'Attention Mechanism', 'Feedforward Layer', 'Next Token Prediction']
            cues = list(range(min(len(items), max(1, len(parts)))))

        elif re.search(r'\b(think of it as|temporary working space|imagine.*container|company with thousands of internal documents)\b', text, re.I):
            kind = 'analogy'
            items = []
            cues = []
        elif re.search(r'\b(one important thing to remember|this is important|leads to another important idea|so what exactly is)\b', text, re.I):
            kind = 'quote'
            items = []
            cues = []

    if items and kind in {'neural_net','components','process','comparison','cycle','timeline'}:
        normalize=lambda s:' '.join(re.findall(r'\w+',s.casefold()))
        if any(normalize(label) not in normalize(scene.narration) for label in items):
            # Preserve literal sentence-based diagrams, replacing keyword template inventions.
            if not all(any(part.startswith(label.rstrip('...')) for part in parts) for label in items):
                kind,items,cues='explanation',[],[]
    icon = choose_icon(text, recent_icons)
    if items and len(cues) != len(items):
        cues = [min(idx, len(parts)-1) for idx in range(len(items))]
    res = {'kind': kind, 'items': items, 'cues': cues, 'icon': icon, 'directed': True}
    if 'values' in locals():
        res['values'] = values
    return res


def direct_scene(scene, index, total, recent_icons=None):
    visual = _extract_scene(scene, index, total, recent_icons)
    parts = sentences(scene.narration)
    text = scene.narration
    stages = [(r'evapor|water vapou?r|water rises', 'Evaporation'),
              (r'condens|clouds? form|forms? clouds?', 'Condensation'),
              (r'precipitation|rain falls|falls as rain', 'Precipitation'),
              (r'collect|flows? back|returns? to', 'Collection')]
    matches = [next((i for i,p in enumerate(parts) if re.search(pattern,p,re.I)),None) for pattern,_ in stages]
    if all(i is not None for i in matches) and matches == sorted(matches):
        visual.update(kind='water_cycle',items=[label for _,label in stages],cues=matches)
    elif re.search(r'\b(cycle|repeats|repeat|back to|again)\b',text,re.I) and len(parts)>=3 and re.search(r'\b(first|next|then|finally|stage)\b',text,re.I):
        indices=list(range(min(4,len(parts))))
        visual.update(kind='cycle',items=[short(parts[i]) for i in indices],cues=indices)
    else:
        percentages=[(i,p,re.search(r'\b(\d+(?:\.\d+)?)\s*(?:percent\b|%)',p,re.I)) for i,p in enumerate(parts)]
        percentages=[(i,p,float(m[1])) for i,p,m in percentages if m]
        dated=[(i,p) for i,p in enumerate(parts) if re.search(r'\b(?:1[0-9]{3}|20[0-9]{2})\b',p)]
        years=[int(re.search(r'\b(?:1[0-9]{3}|20[0-9]{2})\b',p)[0]) for _,p in dated]
        if 2<=len(percentages)<=4 and all(0<=value<=100 for _,_,value in percentages):
            visual.update(kind='chart',items=[short(p) for _,p,_ in percentages],cues=[i for i,_,_ in percentages],values=[value for _,_,value in percentages])
        elif 2<=len(dated)<=4 and years==sorted(years) and len(set(years))==len(years):
            visual.update(kind='timeline',items=[short(p) for _,p in dated],cues=[i for i,_ in dated])
        elif (match:=re.search(r'\b(?:consists of|is made up of|has three parts:|contains the following:)\s+([^.!?]+)',text,re.I)):
            labels=[p.strip(' ,') for p in re.split(r',\s*(?:and\s+)?|\s+and\s+',match[1]) if p.strip(' ,')]
            if 2<=len(labels)<=4 and all(len(p)<=50 for p in labels):
                cue=next(i for i,p in enumerate(parts) if match[0] in p)
                visual.update(kind='components',items=labels,cues=[cue]*len(labels))
    from backend.services.topic_visuals import topic_visual
    topic_plan = topic_visual(scene)
    if topic_plan and visual['kind'] not in {'chart','water_cycle','timeline'}:
        visual = topic_plan
    visual['variant'] = index % 2
    visual['icons'] = [choose_icon(item, recent_icons) for item in visual['items']]
    visual['transition'] = 'slide' if visual['kind']=='process' and index%3==1 else 'fade'
    visual['motion'] = {'process':'assemble','components':'assemble','relationship':'focus',
                        'comparison':'focus','timeline':'reveal','neural_net':'flow',
                        'code':'reveal','stat_card':'reveal','cycle':'flow','quote':'focus','analogy':'focus'}.get(visual['kind'],'flow')
    return visual


def build_direction(video):
    from backend.services.lesson_quality import improve_visual
    scenes = []
    recent_icons = []
    for i, s in enumerate(video.scenes):
        d = direct_scene(s, i, len(video.scenes), recent_icons)
        d = improve_visual(s, d, scenes)
        recent_icons.append(d.get('icon', 'idea'))
        scenes.append({'id': s.id, **d})
    for previous, current in zip(scenes, scenes[1:]):
        if previous['kind']==current['kind']: current['variant']=1-previous['variant']
    return {'scenes': scenes,
            'notice': 'Evidence-based diagrams with narration cues. Unsupported concepts use simpler compositions; review facts before publishing.'}


def timed_visual(visual, narration, beats):
    result = dict(visual)
    if not visual.get('directed'):
        return result
    if len(beats) != len(sentences(narration)):
        raise ValueError('Speech timing does not match the current narration')
    cues = visual.get('cues', [])
    if len(cues) != len(visual['items']) or any(i >= len(beats) for i in cues):
        # A manual layout edit has no authored alignment; distribute items over
        # measured sentence boundaries, never fabricate sub-sentence precision.
        cues = [min(i, len(beats)-1) for i in range(len(visual['items']))]
    from backend.utils.word_timing import cue_time, phrase_time
    # An item quoted from its sentence appears as it is spoken; summaries keep the sentence start.
    reveals = []
    for item, cue in zip(visual['items'], cues):
        at = cue_time(beats[cue], phrase_time(beats[cue], item) if isinstance(item, str) else None)
        reveals.append(max(at, reveals[-1]) if reveals else at)
    result['revealAt'] = reveals
    result.setdefault('transition', 'fade')
    return result
