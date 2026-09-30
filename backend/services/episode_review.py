"""Read-only, whole-episode review data and revision-safe visual candidates."""
import copy
import json
import re
import math
from types import SimpleNamespace
from backend.services.run_state import fingerprint, file_hash
from backend.services.script_generator import write_json_atomic
from backend.services.editor_store import EditorStore, validate_document


def locate(jobs,project,uid):
    if not isinstance(uid,str) or not re.fullmatch('[a-f0-9]{12}',uid):raise ValueError('Select a valid scene')
    if 'long_video' not in project:
        scene=next((s for s in (project.get('document') or {}).get('scenes',[]) if s['uid']==uid),None)
        if not scene:raise ValueError('Unknown scene')
        return jobs,project,scene
    from backend.services.long_video import nested_jobs
    nested=nested_jobs(jobs,project)
    for chapter in project['long_video']['chapters']:
        child=nested.store.load(chapter['id'])
        for scene in (child.get('document') or {}).get('scenes',[]):
            if scene['uid']==uid:return nested,child,scene
    raise ValueError('Unknown scene')


def review(result):
    chapters=result.get('chapter_details') or [result]
    rows=[];offset=0;previous=None;run=0
    for chapter in chapters:
        doc=chapter.get('document') or {};plans=(chapter.get('visual_plan') or {}).get('scenes',[])
        style=chapter.get('review_style',{});first=(plans[0].get('choreography') or {}).get('layout') if plans else None
        last=(plans[-1].get('choreography') or {}).get('layout') if plans else None
        if style.get('showIntro') and first!='intro':offset+=3
        for i,s in enumerate(doc.get('scenes',[])):
            plan=plans[i] if i<len(plans) else {};choreo=plan.get('choreography');audio=chapter.get('audio',{}).get(s['uid'])
            duration=audio['duration'] if audio else len(s['narration'].split())/135*60
            frames=math.ceil((duration+.5)*30)
            from backend.services.visual_actions import plan as planned_actions
            actions=planned_actions(s)
            form=(actions or {}).get('form') or (choreo or {}).get('layout') or plan.get('kind') or s['visual']['kind']
            run=run+1 if form==previous else 1;previous=form
            warnings=[q['message'] for q in chapter.get('quality',{}).get('issues',[]) if q.get('scene')==i+1]
            if run>=3:warnings.append('This composition repeats across at least three scenes. Review pacing and focus.')
            if len(s['body'].split())+sum(len(o['label'].split()) for o in (choreo or {}).get('objects',[]))>32:warnings.append('Dense labels: check readability at normal playback size.')
            if duration>15 and not choreo and form in {'fallback','explanation','title','takeaway'}:warnings.append('Long static passage: consider a worked example or a shorter explanation.')
            if choreo and not any(step['action'] in {'connect','remove'} for step in choreo['steps']) and duration>22:warnings.append('Only introductions and highlights occur here. Review whether an operation would explain more.')
            if actions and len(actions['beats'])>1 and len({b['verb'] for b in actions['beats']})==1 and duration>20:warnings.append('One visual action repeats through this scene. Check the continuous preview for a static passage.')
            if actions and sum(len(o['label']) for o in (choreo or {}).get('objects',[]))>110:warnings.append('Diagram labels may be crowded at normal playback size.')
            from backend.services.shot_direction import plan as planned_shots
            shots=[{**shot,'override':s['visual'].get('shotOverrides',{}).get(str(shot['sentence']),'auto')} for shot in planned_shots(s)]
            rows.append({'uid':s['uid'],'title':s['headline'],'narration':s['narration'],'form':form,'start':round(offset,3),'seconds':frames/30,'measured':bool(audio),'thumbnail':chapter.get('preview_urls',{}).get(s['uid']),'clip':chapter.get('motion_urls',{}).get(s['uid']),'warnings':list(dict.fromkeys(warnings)),'carry':plan.get('carry'),'shots':shots,'actions':(actions or {}).get('beats',[])})
            offset+=frames/30
        if style.get('showOutro') and last!='outro':offset+=5
    # Seeking is exposed only when every start can be derived from measured audio.
    return {'scenes':rows,'measured':bool(rows) and all(s['measured'] for s in rows),'warnings':sum(len(s['warnings']) for s in rows),'notice':'Editorial checks are review aids, not factual or aesthetic guarantees.'}


def propose(jobs,project,uid,instructions):
    nested,child,scene=locate(jobs,project,uid)
    from backend.services.editor_jobs import EditorJobs
    source=copy.deepcopy(child['document']);base=fingerprint(source)
    store=EditorStore(jobs.store.folder(project['id'])/'visual-candidates')
    candidate=store.create(child['topic'],source,source={'mode':'script'})
    worker=EditorJobs(jobs.root,store);worker.cancel=jobs.cancel;worker.state=jobs.state
    style=nested.workspaces.style(child['id'])
    worker.workspaces=SimpleNamespace(style=lambda _:style,for_project=lambda _:project.get('workspace'))
    folder=store.folder(candidate['id'])
    worker._perform(candidate,'replan',uid,instructions,folder)
    candidate=store.load(candidate['id'])
    worker._perform(candidate,'motion',uid,'',folder)
    candidate=store.load(candidate['id']);record=candidate['motion_previews'][uid]
    visual=next(s['visual'] for s in candidate['document']['scenes'] if s['uid']==uid)
    pending={'uid':uid,'base':base,'revision':project['revision'],'visual':visual,'file':f"visual-candidates/{candidate['id']}/{record['file']}",'sha256':record['sha256']}
    write_json_atomic(jobs.store.folder(project['id'])/'visual-candidate.json',pending)
    jobs.state['message']='Replacement preview ready. Accept it or keep the current visual; narration is unchanged.'


def _candidate(jobs,project):
    file=jobs.store.folder(project['id'])/'visual-candidate.json'
    if not file.is_file():return None
    p=json.loads(file.read_text(encoding='utf-8'))
    try:_,child,_=locate(jobs,project,p['uid'])
    except ValueError:return None
    if p['revision']!=project['revision'] or p['base']!=fingerprint(child['document']):return None
    root=jobs.store.folder(project['id']).resolve();target=(root/p['file']).resolve()
    if not target.is_relative_to(root) or not target.is_file() or file_hash(target)!=p['sha256']:return None
    return p


def candidate(jobs,project):
    try:return _candidate(jobs,project)
    except (OSError,ValueError,KeyError,TypeError):return None


def decide(jobs,project,accept):
    p=candidate(jobs,project)
    if not p:raise ValueError('This visual candidate is stale or unavailable. Prepare another preview.')
    if accept:
        nested,child,scene=locate(jobs,project,p['uid']);document=copy.deepcopy(child['document'])
        next(s for s in document['scenes'] if s['uid']==p['uid'])['visual']=p['visual']
        validate_document(document)
        approved=child.get('storyboard_approved')==fingerprint(child['document'])
        saved=nested.store.save(child['id'],child['revision'],document)
        if approved:nested.store.approve_storyboard(saved['id'],saved['revision'])
        if 'long_video' in project:
            project['revision']+=1;project.pop('accepted_export',None)
            write_json_atomic(jobs.store.folder(project['id'])/'project.json',project)
    # Candidate records are reversible review metadata; media stays cached.
    (jobs.store.folder(project['id'])/'visual-candidate.json').unlink()
    return jobs.store.load(project['id'])
