"""Source-grounded diagram actions for the illustrated video stage."""
import re

from backend.services.choreography import compile_scene, timed as timed_choreography
from backend.services.director import sentences
from backend.utils.word_timing import cue_time, pattern_time

FORMS={'flow','split','mapping','compare','window','network','grid','stack','focus'}
VERBS={'reveal','split','transform','evict','fill','compare','flow'}
# Layouts that claim nothing about the meaning, used when the narration names no structure.
NEUTRAL=['focus','grid','network','stack','flow']


def form_candidates(scene, choreography):
    """Layouts that fit what the narration says, best first. A specific meaning (a comparison, ordered
    steps, parts of a whole) comes before the neutral layouts, which only add variety."""
    text=scene['narration'].lower()
    visual=scene.get('visual',{})
    n=len(choreography['objects'])
    fits=lambda form:{'grid':n>=3,'network':n>=3,'stack':2<=n<=3,'focus':n>=2,'split':n>=3}.get(form,True)
    found=[]
    if choreography['layout']=='comparison' and re.search(r'model weights|persistent memory',text):found.append('compare')
    if re.search(r'context window|output budget|conversation history',text):found.append('window')
    if re.search(r'\b(token ids?|identifiers?|embeddings?|numerical representations?)\b',text):found.append('mapping')
    if re.search(r'\b(different|versus|compare|comparison|unlike|whereas|in contrast)\b',text) or visual.get('kind')=='comparison':found.append('compare')
    if re.search(r'\b(whole words|word pieces|split\w*|boundaries)\b',text):found.append('split')
    if re.search(r'not (?:always|the same)',text):found.append('compare')
    if visual.get('kind')=='process' or re.search(r'\bfirst\b.*\b(?:next|then)\b|\bstep by step\b|\bstages?\b|\bin order\b|\bstart with\b|\bresulting\b',text):found.append('flow')
    if re.search(r'\b(?:two|three|four|several) (?:parts|pieces|components|layers|kinds|types)\b|\bconsists? of\b|\bmade (?:up )?of\b',text):found+=['split','stack']
    # A real list: "such as a calculator, a search engine, and a calendar".
    if re.search(r'\b(?:such as|including|like)\b[^.]*,[^.]*\b(?:and|or)\b',text):found+=['grid','network']
    if re.search(r'\b(?:depends? on|leads? to|turns? \w+ into|becomes?|converts?|transforms?)\b',text):found.append('mapping')
    layout={'workspace':'window','comparison':'compare','connections':'network'}.get(choreography['layout'])
    if layout:found.append(layout)
    specific=[f for f in dict.fromkeys(found) if fits(f)]
    return specific, [f for f in NEUTRAL if fits(f) and f not in specific]


def form_for(scene, choreography, recent=()):
    """The best-fitting layout that the previous scenes did not just use, so a video does not show
    the same diagram scene after scene. A required meaning (a real comparison) may still repeat."""
    specific, neutral = form_candidates(scene, choreography)
    # A side-by-side comparison or the context-window frame is the meaning itself, so it stays.
    if specific and specific[0] in ('compare', 'window'):
        return specific[0]
    for form in specific:
        if not recent or form != recent[-1]:
            return form
    # Among neutral layouts, the one this video has used least so far (ties keep NEUTRAL order).
    for form in sorted(neutral, key=lambda f: list(recent).count(f)):
        if form not in recent[-2:]:
            return form
    return (specific or neutral or ['flow'])[0]


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


def plan(scene, recent=()):
    choreography=compile_scene(scene)
    if not choreography or choreography['layout'] in {'intro','outro','budget'}:return None
    form=form_for(scene,choreography,recent)
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


def timed(scene,beats,recent=()):
    result=plan(scene,recent)
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
