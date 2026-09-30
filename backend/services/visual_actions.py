"""Source-grounded diagram actions for the illustrated video stage."""
import re

from backend.services.choreography import compile_scene, timed as timed_choreography
from backend.services.director import sentences
from backend.utils.word_timing import cue_time, pattern_time

FORMS={'flow','split','mapping','compare','window','network'}
VERBS={'reveal','split','transform','evict','fill','compare','flow'}


def form_for(scene, choreography):
    text=scene['narration'].lower()
    visual=scene.get('visual',{})
    if choreography['layout']=='comparison' and re.search(r'model weights|persistent memory',text):return 'compare'
    if re.search(r'context window|output budget|conversation history',text):return 'window'
    if re.search(r'\b(token ids?|identifiers?|embeddings?|numerical representations?)\b',text):return 'mapping'
    if re.search(r'\b(different|versus|compare|comparison|unlike|whereas)\b',text) or visual.get('kind')=='comparison':return 'compare'
    if re.search(r'\b(whole words|word pieces|split\w*|boundaries)\b',text):return 'split'
    if re.search(r'not (?:always|the same)',text):return 'compare'
    return {'workspace':'window','comparison':'compare','connections':'network'}.get(choreography['layout'],'flow')


VERB_PATTERNS={
    'evict':r'\b(remove\w*|drop\w*|outside|omit\w*|exclud\w*)\b',
    'split':r'\b(split\w*|pieces|segments?|boundaries)\b',
    'transform':r'\b(map\w*|convert\w*|become\w*|transform\w*|representations?)\b',
    'fill':r'\b(grow\w*|accumulat\w*|fill\w*|occupy|add\w*)\b',
    'compare':r'\b(different|compar\w*|whereas|unlike|rather than)\b|not the same',
    'flow':r'\b(pass\w*|flow\w*|lead\w*|connect\w*|produce\w*|enter\w*)\b',
}


def verb_for(text):
    return next((verb for verb,pattern in VERB_PATTERNS.items() if re.search(pattern,text,re.I)),'reveal')


def plan(scene):
    choreography=compile_scene(scene)
    if not choreography or choreography['layout'] in {'intro','outro','budget'}:return None
    form=form_for(scene,choreography)
    rows=[];objects=choreography['objects']
    for index,text in enumerate(sentences(scene['narration'])):
        steps=[step for step in choreography['steps'] if step['sentence']==index]
        targets=list(dict.fromkeys(target for step in steps for target in step['targets']))
        if not targets:
            prior=[i for i,obj in enumerate(objects) if obj['sentence']<=index]
            targets=prior[-1:]
        verb=verb_for(text)
        if verb=='evict' and not any(step['action']=='remove' for step in steps):verb='reveal'
        rows.append({'sentence':index,'text':text,'verb':verb,'targets':targets})
    return {'form':form,'beats':rows}


def timed(scene,beats):
    result=plan(scene)
    if not result:return None
    if len(result['beats'])!=len(beats):raise ValueError('Visual actions require every measured narration sentence')
    objects=timed_choreography(compile_scene(scene),beats)['objects']
    rows=[]
    for i,row in enumerate(result['beats']):
        beat=beats[i]
        # The action plays on its spoken verb, once every object it uses has appeared.
        spoken=pattern_time(beat,VERB_PATTERNS[row['verb']]) if row['verb'] in VERB_PATTERNS else None
        ready=[objects[t]['at'] for t in row['targets'] if objects[t]['sentence']==i]
        rows.append({**row,'start':beat['start'],'end':beat['end'],'at':max([cue_time(beat,spoken),*ready])})
    return {**result,'beats':rows}
