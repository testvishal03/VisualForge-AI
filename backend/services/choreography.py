"""Compile bounded, source-grounded visual actions; never execute generated code."""
import re
from backend.services.director import sentences

LAYOUTS = {'sequence', 'workspace', 'comparison', 'connections', 'intro', 'outro', 'budget'}
TREATMENTS = {'build', 'focus', 'compare'}


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
        if step['action'] == 'remove' and not re.search(r'\b(remove\w*|drop\w*|outside|omit\w*|exclud\w*)\b',parts[step['sentence']],re.I):
            raise ValueError('Removal requires explicit narration support')
        if step['action'] == 'connect' and (len(step['targets']) != 2 or not re.search(r'\b(convert\w*|become\w*|map\w*|connect\w*|pass\w*|flow\w*|lead\w*|produce\w*|turn\w*|link\w*)\b',parts[step['sentence']],re.I)):
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
    if len(objects) < 2:
        objects = [{'label':label,'sentence':cue} for label,cue in zip(visual.get('items',[]),visual.get('cues',[])) if isinstance(label,str) and type(cue) is int and len(label)<=36 and 0<=cue<len(parts) and label.casefold() in parts[cue].casefold()][:6]
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
        if new:steps.append({'sentence':cue,'action':'reveal','targets':new})
        if present:steps.append({'sentence':cue,'action':'focus','targets':present})
        if len(present)>=2 and re.search(r'\b(convert\w*|become\w*|map\w*|connect\w*|pass\w*|flow\w*|lead\w*|produce\w*|turn\w*|link\w*)\b',part,re.I):
            steps.append({'sentence':cue,'action':'connect','targets':present[:2]})
        if re.search(r'\b(remove\w*|drop\w*|outside|omit\w*|exclud\w*)\b',part,re.I):
            targets=[i for i in present if objects[i]['label'].casefold()=='older messages']
            if targets:steps.append({'sentence':cue,'action':'remove','targets':targets})
    if len(steps)>20:return None
    return validate({'layout':layout,'objects':objects,'steps':steps,'note':'Illustrative diagram; not measured model output'},text)


def timed(spec, beats):
    return {**spec, 'steps':[{**s,'start':beats[s['sentence']]['start'],'end':beats[s['sentence']]['end']} for s in spec['steps']]}
