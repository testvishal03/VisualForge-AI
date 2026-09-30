"""Compile bounded, source-grounded visual actions; never execute generated code."""
import re
from backend.services.director import sentences
from backend.utils.word_timing import cue_time, pattern_time, phrase_time
from backend.services.key_terms import key_terms, overlap

LAYOUTS = {'sequence', 'workspace', 'comparison', 'connections', 'intro', 'outro', 'budget'}
TREATMENTS = {'build', 'focus', 'compare'}
CONNECT = r'\b(convert\w*|become\w*|map\w*|connect\w*|pass\w*|flow\w*|lead\w*|produce\w*|turn\w*|link\w*|receiv\w*|send\w*|feed\w*|generat\w*|creat\w*|split\w*|transform\w*)\b'
NEGATION = r"\b(cannot|can't|can’t|not|never|no|don't|don’t|doesn't|doesn’t|won't|won’t|without)\b"
REMOVE = r'\b(remove\w*|drop\w*|outside|omit\w*|exclud\w*)\b'


def validate(spec, narration):
    if not isinstance(spec, dict) or set(spec) != {'layout','objects','steps','note'}:
        raise ValueError('Invalid demonstration fields')
    if not isinstance(spec['layout'],str) or spec['layout'] not in LAYOUTS or spec['note'] != 'Illustrative diagram; not measured model output':
        raise ValueError('Invalid demonstration layout or disclosure')
    parts = sentences(narration)
    objects = spec['objects']
    if not isinstance(objects, list) or not 1 <= len(objects) <= 6:
        raise ValueError('Demonstrations require one to six objects')
    for obj in objects:
        if not isinstance(obj,dict) or set(obj) != {'label','sentence'} or type(obj['sentence']) is not int or not 0 <= obj['sentence'] < len(parts):
            raise ValueError('Invalid object cue')
        if not isinstance(obj['label'], str) or not 1 <= len(obj['label']) <= 36 or obj['label'].casefold() not in parts[obj['sentence']].casefold():
            raise ValueError('Demonstration labels must occur in the cited narration sentence')
    if spec['layout']=='budget':
        values=[int(o['label'].split()[0].replace(',','')) for o in objects if re.fullmatch(r'[0-9,]+ tokens',o['label'])]
        if len(values)!=3 or min(values)<=0 or values[1]+values[2]!=values[0]:raise ValueError('Budget must show a source-grounded total and two parts')
    steps = spec['steps']
    if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
        raise ValueError('Invalid demonstration actions')
    for step in steps:
        if not isinstance(step,dict) or set(step) != {'sentence','action','targets'} or type(step['sentence']) is not int or not 0 <= step['sentence'] < len(parts):
            raise ValueError('Invalid action cue')
        if not isinstance(step['action'],str) or step['action'] not in {'reveal','focus','connect','remove'} or not isinstance(step['targets'],list) or not step['targets'] or any(type(i) is not int or not 0 <= i < len(objects) for i in step['targets']):
            raise ValueError('Invalid action targets')
        if any(objects[i]['sentence'] > step['sentence'] for i in step['targets']):
            raise ValueError('An action cannot precede its spoken object')
        if step['action'] == 'remove' and not re.search(REMOVE,parts[step['sentence']],re.I):
            raise ValueError('Removal requires explicit narration support')
        if step['action'] == 'connect' and (len(step['targets']) != 2 or not re.search(CONNECT,parts[step['sentence']],re.I)):
            raise ValueError('Connections require a narrated relationship')
    if [s['sentence'] for s in steps] != sorted(s['sentence'] for s in steps):
        raise ValueError('Actions must follow narration order')
    if any(not any(s['action']=='reveal' and i in s['targets'] and s['sentence']==o['sentence'] for s in steps) for i,o in enumerate(objects)):
        raise ValueError('Every object must appear at its narration cue')
    return spec


def compile_scene(scene, visual=None):
    visual = visual or scene.get('visual', {})
    if visual.get('choreography'):
        return validate(visual['choreography'], scene['narration'])
    if visual.get('worked') or visual.get('demo') or visual.get('kind') in {'code','chart','stat_card','water_cycle','neural_net'}:
        return None
    # Exact, sentence-cited visual labels can use this bounded grammar across
    # topics. Charts, code, and authored examples retain dedicated renderers.
    text = scene['narration']; parts = sentences(text)
    topic = bool(re.search(r'\b(tokens?|tokenizer|context window)\b',text,re.I))
    objects = []
    if topic:
        phrases = r'context window|tokenizer|token IDs|tokens|word pieces|whole words|punctuation|instructions|conversation history|retrieved documents|current question|generated answer|output budget|older messages|relevant evidence|model weights|persistent memory|input text|text pieces|training|inference|summary|retrieval'
        for cue, part in enumerate(parts):
            for match in re.finditer(r'\b(?:'+phrases+r')\b',part,re.I):
                if match[0].casefold() not in [o['label'].casefold() for o in objects]:
                    objects.append({'label':match[0], 'sentence':cue})
        objects = objects[:6]
    budget=[]
    if 'toy model' in text.lower():
        for cue,part in enumerate(parts):
            budget.extend({'label':m[0],'sentence':cue} for m in re.finditer(r'\b[0-9,]+ tokens\b',part))
    if len(budget)==3:objects=budget
    grown = topic
    if len(objects) < 2:
        objects = [{'label':label,'sentence':cue} for label,cue in zip(visual.get('items',[]),visual.get('cues',[])) if isinstance(label,str) and type(cue) is int and len(label)<=36 and 0<=cue<len(parts) and label.casefold() in parts[cue].casefold()][:6]
        grown = False
    # Generic explanation and example scenes draw the concepts their own summary and narration name.
    if len(objects) < 2 and visual.get('kind') in {'explanation', 'example'}:
        objects, grown = key_terms(scene.get('headline', ''), scene.get('body', ''), parts), True
    if grown and len(budget) != 3:
        objects = grow(objects, key_terms(scene.get('headline', ''), scene.get('body', ''), parts), parts)
    if len(objects) < 2:return None
    if visual.get('treatment')=='focus':objects=objects[:4]
    layout = 'workspace' if re.search(r'context window|output budget',text,re.I) else 'sequence'
    if visual.get('kind') == 'comparison' or visual.get('treatment') == 'compare':layout='comparison'
    if visual.get('kind') == 'relationship':layout='connections'
    if visual.get('kind') == 'components':layout='workspace'
    if re.search(r'model weights|persistent memory',text,re.I) and 'context window' in text.lower():layout='comparison'
    if len(budget)==3:layout='budget'
    if re.search(r'\b(welcome|in this video|we will explore)\b',text,re.I):layout='intro'
    if re.search(r'\b(thanks for watching|subscribe|to recap|let.s recap)\b',text,re.I):layout='outro'
    steps=[]
    for cue, part in enumerate(parts):
        new=[i for i,o in enumerate(objects) if o['sentence']==cue]
        present=[i for i,o in enumerate(objects) if o['sentence']<=cue and o['label'].casefold() in part.casefold()]
        # Reading order decides direction: "converts X into Y" draws X -> Y.
        present.sort(key=lambda i: part.casefold().find(objects[i]['label'].casefold()))
        if new:steps.append({'sentence':cue,'action':'reveal','targets':new})
        if present:steps.append({'sentence':cue,'action':'focus','targets':present})
        elif not new:
            # Every sentence gets a cue: keep attention on what the sentence is still about.
            known=[i for i,o in enumerate(objects) if o['sentence']<cue]
            if known:
                steps.append({'sentence':cue,'action':'focus','targets':[max(known,key=lambda i:(overlap(objects[i]['label'],part),objects[i]['sentence'],i))]})
        verb=re.search(CONNECT,part,re.I)
        # "We cannot send X to Y" must not draw X -> Y: a negated relationship gets no arrow.
        if verb and re.search(NEGATION,part[:verb.start()],re.I):verb=None
        if len(present)>=2 and verb:
            steps.append({'sentence':cue,'action':'connect','targets':flow_pair(present,objects,part,verb.start())})
        if re.search(REMOVE,part,re.I):
            targets=[i for i in present if objects[i]['label'].casefold()=='older messages']
            if targets:steps.append({'sentence':cue,'action':'remove','targets':targets})
    if len(steps)>20:return None
    try:
        return validate({'layout':layout,'objects':objects,'steps':steps,'note':'Illustrative diagram; not measured model output'},text)
    except ValueError:
        # An automatic plan that cannot be fully grounded keeps the scene's existing card or diagram.
        return None


def grow(objects, terms, parts, limit=6):
    """Add grounded terms to sentences that introduce nothing yet, keeping narrative order."""
    result=list(objects)
    for term in terms:
        if len(result)>=limit:
            break
        known=[o['label'].casefold() for o in result]
        if any(o['sentence']==term['sentence'] for o in result) or any(term['label'].casefold() in k or k in term['label'].casefold() for k in known):
            continue
        result.append(term)
    return sorted(result,key=lambda o:(o['sentence'],parts[o['sentence']].casefold().find(o['label'].casefold())))


def flow_pair(present, objects, part, verb_at):
    """Source and target of a narrated relationship, in reading order around its verb."""
    at=lambda i: part.casefold().find(objects[i]['label'].casefold())
    after=[i for i in present if at(i)>verb_at]
    before=[i for i in present if at(i)<verb_at]
    if len(after)>=2:return [after[0],after[-1]]
    if before and after:return [before[-1],after[-1]]
    return present[:2]


def timed(spec, beats):
    """Attach measured times: objects appear on their spoken label, actions on their spoken cue.

    Without word timing every cue falls back to its sentence start, as before.
    """
    objects = [{**o, 'at': cue_time(beats[o['sentence']], phrase_time(beats[o['sentence']], o['label']))} for o in spec['objects']]
    steps = []
    for s in spec['steps']:
        beat = beats[s['sentence']]
        # Objects introduced in this sentence must be on screen before an action uses them.
        introduced = [objects[i]['at'] for i in s['targets'] if objects[i]['sentence'] == s['sentence']]
        if s['action'] == 'reveal':
            start = min(introduced)
        elif s['action'] == 'focus':
            mentions = [phrase_time(beat, objects[i]['label']) for i in s['targets']]
            start = cue_time(beat, min((m for m in mentions if m is not None), default=None))
        else:
            start = cue_time(beat, pattern_time(beat, CONNECT if s['action'] == 'connect' else REMOVE))
            start = max([start, *introduced])
        steps.append({**s, 'start': start, 'end': beat['end']})
    return {**spec, 'objects': objects, 'steps': steps}
