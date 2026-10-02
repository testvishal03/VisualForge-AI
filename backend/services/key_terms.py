"""Concepts a scene can draw, taken from its own headline and caption and grounded in its narration.

The headline and caption are the script's summary of the scene, so the phrases they share
with a spoken sentence are the concepts worth showing. Labels are returned exactly as spoken,
so every object stays a verbatim quote of the sentence that introduces it.
"""
import re

# Function words, generic nouns, and common explanatory verbs never make useful objects.
STOP = set('''a an the and or but if so as of to in on at by for from with without into onto over under about
than then that this these those there here it its it's they them their we our you your he she his her i me my
is are was were be been being am do does did done has have had can could will would should may might must shall
not no yes very more most less least many much some any each every all both few other another such same own
just only also even still too again already often usually always never sometimes before after during while when
where why how what which who whom whose because although though until unless whether
thing things way ways example examples idea ideas part parts step steps kind kinds type types lot lots something
anything everything nothing someone everyone people person first second third next last new old simple important
become becomes became convert converts converted determine determines determined assemble assembles assembled
help helps helped use uses used using make makes made take takes took give gives gave show shows shown showed mean
means meant need needs needed work works worked receive receives received produce produces produced create creates
created turn turns turned change changes changed move moves moved include includes included contain contains
contained learn learns learned predict predicts predicted generate generates generated represent represents
represented process processes processed store stores stored find finds found look looks looked matter matters
depend depends depended explain explains explained describe describes described let lets allow allows allowed
keep keeps kept get gets got see sees saw know knows knew think thinks thought call calls called start starts
begin begins happen happens happened go goes went come comes came put puts set sets run runs ran say says said
select selects selected follow follows followed affect affects affected handle handles handled compare compares
compared lose loses lost check checks checked invent invents invented return returns returned read reads write
writes ask asks asked add adds added remove removes removed reduce reduces increase increases improve improves
choose chooses chosen try tries tried seem seems seemed provide provides provided require requires required
time times together close earlier later well really actually simply clearly directly one let's now
us imagine imagines bring brings brought measure measures measured forever active
instead point points related closer relative whereas rather despite yet minus plus capture captures captured
various certain amount dimensional two-dimensional three-dimensional
cannot can't send sends sent like likes given tend tends exist exists inside fit fits
suppose consider notice remember note recall picture'''.split())
# Describing words that are poor labels alone but fine inside a phrase ("relevant information").
SOLO_STOP = set('''different similar relevant individual common longer shorter higher lower bigger larger smaller
faster slower better worse closest nearest farthest best largest smallest highest lowest'''.split())
# After a noun, an -s word followed by one of these is the sentence's verb ("the model analyzes the text").
OBJECT_START = {'the', 'a', 'an', 'that', 'this', 'these', 'those', 'its', 'their', 'our', 'your', 'them', 'it', 'to',
                'how', 'for', 'whether', 'which', 'what', 'if', 'through', 'with'}
# Labels must end in a noun: words with these endings are verbs, adjectives or adverbs here.
NOT_NOUN = ('ed', 'ing', 'ly', 'ize', 'ise', 'ive', 'ous', 'ful', 'able', 'ible')


def noun_like(phrase):
    return not phrase.split()[-1].lower().endswith(NOT_NOUN)
# A lone word right after these is being used as a verb ("may select", "to follow", "we split").
VERB_CONTEXT = {'to', 'can', 'could', 'may', 'might', 'will', 'would', 'should', 'must', 'not', 'also',
                'we', 'you', 'they', 'i', 'he', 'she', 'it'}
MAX_LABEL = 36


def _words(text):
    return re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text.replace('’', "'"))


def split_verb(run):
    """Split "tokenizer splits input text" into subject and object around its -s verb."""
    if len(run) >= 3:
        for k in range(1, len(run) - 1):
            word, prior = run[k].lower(), run[k-1].lower()
            if word.endswith('s') and not word.endswith('ss') and not prior.endswith('s'):
                return [run[:k], run[k+1:]]
    return [run]


# Nouns that name nothing a learner could picture ("a smarter trick", "a tiny bit"); grammar alone
# cannot tell these apart from real concepts.
VAGUE_NOUNS = {'trick', 'tricks', 'bit', 'bits', 'one', 'ones', 'deal', 'stuff', 'side', 'sides', 'area', 'areas', 'option', 'options'}
_PARSER = []


def parser():
    """spaCy's small English pipeline (MIT, about 12 MB), loaded once per process; None if not installed."""
    if not _PARSER:
        try:
            import spacy
            nlp = spacy.load('en_core_web_sm', disable=['ner', 'lemmatizer'])
            # The tokenizer reads "id" as the contraction "I'd"; in lessons it is an identifier.
            for form in ('id', 'Id'):
                nlp.tokenizer.add_special_case(form, [{'ORTH': form}])
            _PARSER.append(nlp)
        except Exception:  # OSError for a missing model, ImportError for a missing package
            _PARSER.append(None)
    return _PARSER[0]


# Words ending in -ing that are things in these lessons; the small parser often tags them as verbs
# ("every single stored embedding"), so a phrase ending on one is rebuilt from its modifiers.
DOMAIN_NOUNS = {'embedding', 'embeddings', 'training', 'encoding', 'encodings', 'ranking', 'rankings', 'meaning', 'meanings',
                'learning', 'reasoning', 'filtering', 'indexing', 'chunking', 'setting', 'settings', 'mapping', 'mappings',
                'pooling', 'clustering', 'prompting', 'fine-tuning'}
MODIFIER = {'NOUN', 'PROPN', 'ADJ'}


def _words_of(tokens):
    """Group tokens into written words: "next-word" is one word although it is three tokens."""
    words = []
    for t in tokens:
        if words and not words[-1][-1].whitespace_ and (t.text == '-' or words[-1][-1].text == '-'):
            words[-1].append(t)
        else:
            words.append([t])
    return words


def _phrase(doc, tokens):
    """Up to three written words ending on the head; four only for a name ("Approximate Nearest
    Neighbor search") that still fits a label, never for a run the parser merged with a verb."""
    words = _words_of(tokens)
    for size in (4, 3, 2, 1):
        kept = words[-size:]
        text = doc.text[kept[0][0].idx:kept[-1][-1].idx + len(kept[-1][-1].text)]
        name = sum(w[0].pos_ == 'PROPN' for w in kept) >= 2
        if size <= 3 or len(text) <= MAX_LABEL and name:
            return text


def grammar_candidates(text):
    """Noun phrases found by a real part-of-speech parse, ending on their head noun, in reading order.

    Unlike word-shape rules, the parser knows "built" in "what a vector database is built for" is a
    verb and "lines" in "the meaning lines up" is too. Phrases are cut from the original text, so
    hyphens and apostrophes survive and every label stays a verbatim quote. None without spaCy.
    """
    nlp = parser()
    if nlp is None:
        return None
    doc, found = nlp(text.replace('’', "'")), []   # found: (token indices, phrase)

    def opening(word, head):
        """A whole written word that may open a chunk but never a label ("the", "every", "your")."""
        token = word[0]
        # Numbers stay ("ten million documents"); "one" is a pronoun-like opener ("one popular index").
        return len(word) == 1 and token.i != head.i and (token.pos_ in ('DET', 'PRON', 'PART', 'CCONJ', 'ADP', 'PUNCT', 'AUX', 'VERB')
                                                         or token.lower_ in STOP)
    for chunk in doc.noun_chunks:
        root = chunk.root
        if root.pos_ not in ('NOUN', 'PROPN') or root.lower_ in STOP or root.lower_ in VAGUE_NOUNS:
            continue
        chunk_tokens = [t for t in chunk if t.i <= root.i]
        # "Vector databases store embeddings": the parser may call "databases" the verb and "store"
        # a noun. An -s word right after the head, followed by a common verb, belongs to the phrase.
        if chunk.end == root.i + 1 and root.i + 2 < len(doc):
            after, verb = doc[root.i + 1], doc[root.i + 2]
            if after.pos_ == 'VERB' and after.lower_.endswith('s') and not after.lower_.endswith('ss') and \
                    verb.lower_ in STOP and verb.pos_ in ('NOUN', 'VERB'):
                chunk_tokens.append(after)
                root = after
        # "make similarity search lightning fast": a noun right before a clause-ending adjective or
        # adverb is an intensifier, so the phrase ends on the word before it.
        if len(chunk_tokens) > 1 and root.i + 1 < len(doc) and doc[root.i + 1].pos_ in ('ADV', 'ADJ') and \
                (root.i + 2 >= len(doc) or doc[root.i + 2].is_punct):
            chunk_tokens.pop()
            root = chunk_tokens[-1]
        words = _words_of(chunk_tokens)
        while words and opening(words[0], root):
            words.pop(0)
        # The parser can merge a verb into a run of nouns ("vector database stores embeddings"); the
        # word-shape rule that finds the -s verb between them splits it back into two concepts.
        pieces = split_verb([''.join(t.text for t in w) for w in words])
        groups = [words[:len(pieces[0])], words[len(pieces[0]) + 1:]] if len(pieces) == 2 else [words]
        for group in groups:
            tokens = [t for w in group for t in w]
            if not tokens or len(tokens) == 1 and tokens[0].lower_ in SOLO_STOP:
                continue
            found.append(({t.i for t in tokens}, _phrase(doc, tokens)))
    covered = set().union(*(ids for ids, _ in found)) if found else set()
    for token in doc:
        if token.lower_ in DOMAIN_NOUNS and token.i not in covered:
            tokens = [token]
            while tokens[0].i > 0 and len(tokens) < 3:
                before = doc[tokens[0].i - 1]
                if before.lower_ in STOP or before.lower_ in SOLO_STOP or not (before.pos_ in MODIFIER or before.tag_ == 'VBN'):
                    break
                tokens.insert(0, before)
            ids = {t.i for t in tokens}
            # "the query" + "embedding" is one concept, "query embedding": the longer phrase replaces the shorter.
            found = [(other, phrase) for other, phrase in found if not other <= ids]
            covered |= ids
            found.append((ids, _phrase(doc, tokens)))
    return [phrase for _, phrase in sorted(found, key=lambda row: min(row[0]))]


def candidates(text, alternatives=False):
    """Noun phrases in reading order: from the grammar parser when installed, otherwise from runs of
    one to three content words, skipping lone words used as verbs.

    With `alternatives`, a run split around a possible verb also offers its unsplit opening
    ("Similar meanings" as well as "Similar"), since a plural noun can look like a verb.
    """
    parsed = grammar_candidates(text)
    if parsed is not None:
        return parsed
    found, run, before = [], [], None
    for word in [*_words(text), '.']:
        if word.lower() in STOP or word == '.':
            if len(run) >= 2 and word.lower() in OBJECT_START and run[-1].lower().endswith('s') and not run[-1].lower().endswith('ss'):
                run = run[:-1]
            pieces = split_verb(run)
            if alternatives and len(pieces) == 2:
                pieces = [*pieces, run[:len(pieces[0]) + 1]]
            for piece in pieces:
                lone_verb = len(piece) == 1 and ((before in VERB_CONTEXT and piece is run) or piece[0].lower() in SOLO_STOP)
                phrase = ' '.join(piece[-3:])
                if piece and not lone_verb and noun_like(phrase):
                    found.append(phrase)
            run, before = [], word.lower()
        else:
            run.append(word)
    return found


def spoken(sentence, phrase):
    """The phrase exactly as spoken in the sentence (a plural ending allowed), or None."""
    # Either apostrophe style matches, but the label is returned verbatim from the sentence.
    words = [re.escape(w.replace('’', "'")).replace("'", "['’]") for w in phrase.split()]
    pattern = r'\b' + r'\s+'.join(words[:-1] + [words[-1] + "(?:s|es|['’]s)?"]) + r'\b'
    match = re.search(pattern, sentence, re.I)
    return match[0] if match else None


def key_terms(headline, body, parts, limit=6, per_sentence=2):
    """[{'label', 'sentence'}] for summary phrases spoken in the narration, at their first sentence.

    Summary phrases come first; sentences still without a concept may add one of their own,
    so the diagram grows as the explanation proceeds instead of appearing all at once.
    """
    terms = []

    def add(option, only=None):
        rows = [(i, part) for i, part in enumerate(parts) if only is None or i == only]
        hit = next(((i, label) for i, part in rows if (label := spoken(part, option))), None)
        if not hit:
            return False
        index, label = hit
        known = [t['label'].casefold() for t in terms]
        # A phrase already drawn, or a sentence already at its limit, is settled without a new object.
        if any(label.casefold() in k or k in label.casefold() for k in known):
            return 'known'
        if sum(t['sentence'] == index for t in terms) >= per_sentence:
            return 'full'
        terms.append({'label': label, 'sentence': index})
        return 'added'

    for phrase in candidates(f'{headline}. {body}'):
        head = phrase.split()[-1]
        options = [phrase] + ([head] if ' ' in phrase and len(head) >= 5 else [])
        for option in options:
            if 4 <= len(option) <= MAX_LABEL and add(option):
                break
    for index, part in enumerate(parts):
        if len(terms) >= limit or any(t['sentence'] == index for t in terms):
            continue
        # A sentence's own phrases are less reliable than the summary's, so keep them short.
        own = [c for c in candidates(part) if 5 <= len(c) <= MAX_LABEL and len(c.split()) <= 2 and (' ' in c or len(c) >= 6)]
        for option in sorted(own, key=lambda c: -len(c.split())):
            # A concept already drawn ("Regular databases" after "regular database") lets the
            # sentence offer its next phrase ("exact matches") instead of adding nothing.
            if add(option, index) in ('added', 'full'):
                break
    return sorted(terms, key=lambda t: t['sentence'])[:limit]


def overlap(label, sentence):
    """Shared word stems between a label and a sentence, to pick what a sentence is still about."""
    stems = lambda text: {w.lower()[:5] for w in _words(text) if w.lower() not in STOP and len(w) > 3}
    return len(stems(label) & stems(sentence))
