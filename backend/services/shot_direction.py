"""Bounded camera shots tied to measured narration sentences."""
import copy

from backend.services.director import sentences
from backend.services.run_state import fingerprint
from backend.services.script_generator import write_json_atomic

MODES={'wide','follow','detail'}


def plan(scene):
    visual=scene.get('visual',{})
    from backend.services.choreography import compile_scene
    choreography=compile_scene(scene)
    if not choreography or choreography['layout'] in {'intro','outro','budget'}:
        return []
    overrides=visual.get('shotOverrides',{})
    objects=choreography['objects']
    rows=[]
    for index,text in enumerate(sentences(scene['narration'])):
        actions=[step for step in choreography['steps'] if step['sentence']==index]
        chosen=next((step for step in reversed(actions) if step['action'] in {'connect','remove','focus','reveal'}),None)
        focus=chosen['targets'][-1] if chosen else next((i for i in range(len(objects)-1,-1,-1) if objects[i]['sentence']<=index),None)
        if index==0:mode='wide'
        elif any(step['action'] in {'connect','remove'} for step in actions):mode='follow'
        elif focus is not None:mode='detail' if index%3==2 else 'follow'
        else:mode='wide'
        mode=overrides.get(str(index),mode)
        rows.append({'sentence':index,'text':text,'mode':mode,'focus':focus,
                     'label':objects[focus]['label'] if focus is not None else None})
    return rows


def timed(scene,beats):
    if len(beats)!=len(sentences(scene['narration'])):
        raise ValueError('Shot timing requires every measured narration sentence')
    return [{**row,'start':beats[row['sentence']]['start'],'end':beats[row['sentence']]['end']} for row in plan(scene)]


def select_contiguous(scenes,start_uid,durations,limit=120):
    start=next((i for i,s in enumerate(scenes) if s['uid']==start_uid),None)
    if start is None:raise ValueError('Select a starting scene in this episode')
    selected=[];seconds=0.0
    for scene in scenes[start:]:
        duration=float(durations[scene['uid']])+.5
        if duration>limit and not selected:raise ValueError('This scene exceeds two minutes. Split its narration first.')
        if selected and seconds+duration>limit:break
        selected.append(scene);seconds+=duration
    return selected


def set_override(jobs,project,uid,sentence,mode):
    from backend.services.episode_review import locate
    from backend.services.editor_store import validate_document
    nested,child,scene=locate(jobs,project,uid)
    if type(sentence) is not int or sentence<0 or sentence>=len(sentences(scene['narration'])):
        raise ValueError('Select a valid narration sentence')
    if mode not in MODES and mode!='auto':raise ValueError('Choose a supported shot view')
    if not plan(scene):raise ValueError('This scene does not use illustrated shots')
    document=copy.deepcopy(child['document'])
    target=next(s for s in document['scenes'] if s['uid']==uid)
    overrides=target['visual'].setdefault('shotOverrides',{})
    if mode=='auto':overrides.pop(str(sentence),None)
    else:overrides[str(sentence)]=mode
    if not overrides:target['visual'].pop('shotOverrides',None)
    validate_document(document)
    approved=child.get('storyboard_approved')==fingerprint(child['document'])
    saved=nested.store.save(child['id'],child['revision'],document)
    if approved:nested.store.approve_storyboard(saved['id'],saved['revision'])
    if 'long_video' in project:
        project=copy.deepcopy(project);project['revision']+=1;project.pop('accepted_export',None)
        write_json_atomic(jobs.store.folder(project['id'])/'project.json',project)
    return jobs.store.load(project['id'])
