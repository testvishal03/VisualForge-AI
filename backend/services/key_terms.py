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
cannot can't send sends sent like likes given tend tends exist exists inside fit fits'''.split())
# Describing words that are poor labels alone but fine inside a phrase ("relevant information").
SOLO_STOP = set('''different similar relevant individual common longer shorter higher lower bigger larger smaller
faster slower better worse'''.split())
# After a noun, an -s word followed by one of these is the sentence's verb ("the model analyzes the text").
OBJECT_START = {'the', 'a', 'an', 'that', 'this', 'these', 'those', 'its', 'their', 'our', 'your', 'them', 'it', 'to',
                'how', 'for', 'whether', 'which', 'what', 'if', 'through', 'with'}
# Labels must end in a noun: words with these endings are verbs, adjectives or adverbs here.
NOT_NOUN = ('ed', 'ing', 'ly', 'ize', 'ise', 'ive', 'ous', 'ful', 'able', 'ible')


def noun_like(phrase):
    return not phrase.split()[-1].lower().endswith(NOT_NOUN)
# A lone word right after these is being used as a verb ("may select", "to follow").
VERB_CONTEXT = {'to', 'can', 'could', 'may', 'might', 'will', 'would', 'should', 'must', 'not', 'also'}
MAX_LABEL = 36


def _words(text):
    return re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text.replace('’', "'"))


def candidates(text):
    """Runs of one to three content words, in reading order; lone words used as verbs are skipped."""
    found, run, before = [], [], None
    for word in [*_words(text), '.']:
        if word.lower() in STOP or word == '.':
            if len(run) >= 2 and word.lower() in OBJECT_START and run[-1].lower().endswith('s') and not run[-1].lower().endswith('ss'):
                run = run[:-1]
            lone_verb = len(run) == 1 and (before in VERB_CONTEXT or run[0].lower() in SOLO_STOP)
            phrase = ' '.join(run[-3:])
            if run and not lone_verb and noun_like(phrase):
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
        if not any(label.casefold() in k or k in label.casefold() for k in known) and \
                sum(t['sentence'] == index for t in terms) < per_sentence:
            terms.append({'label': label, 'sentence': index})
        return True

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
            if add(option, index):
                break
    return sorted(terms, key=lambda t: t['sentence'])[:limit]


def overlap(label, sentence):
    """Shared word stems between a label and a sentence, to pick what a sentence is still about."""
    stems = lambda text: {w.lower()[:5] for w in _words(text) if w.lower() not in STOP and len(w) > 3}
    return len(stems(label) & stems(sentence))
