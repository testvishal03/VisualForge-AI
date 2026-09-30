"""Bounded composition choices and review checks; never invent diagram data."""
import re

LAYOUTS = {'auto', 'pipeline', 'branching', 'layers', 'contrast', 'timeline', 'detail'}
COMPATIBLE = {'pipeline': {'process'}, 'branching': {'relationship'},
              'layers': {'components'}, 'contrast': {'comparison'},
              'timeline': {'timeline'}, 'detail': {'process','relationship','components','comparison','timeline'}}

def composition(visual):
    return (visual.get('layout') if visual.get('layout')!='auto' else None) or {'process':'pipeline','relationship':'branching',
        'components':'layers','comparison':'contrast','timeline':'timeline'}.get(visual['kind'],'auto')

def visual_issues(document):
    from backend.services.lesson_quality import label_problem
    from backend.services.director import sentences
    issues=[]; previous=[]
    for i, scene in enumerate(document['scenes'],1):
        from backend.services.choreography import compile_scene
        demonstration=compile_scene(scene)
        visual=scene['visual']; form=((demonstration or {}).get('layout') or composition(visual),visual.get('motion','flow'))
        def add(code,message):issues.append({'scene':i,'code':code,'severity':'warning','message':message})
        for label in visual['items']:
            if label_problem(label):
                issues.append({'scene':i,'code':'incomplete_label','severity':'error','message':f'Complete the cut-off visual label: {label}'})
        if visual.get('planned') and visual.get('cues') and visual['kind'] != 'water_cycle':
            parts = sentences(scene['narration'])
            normalize = lambda text: ' '.join(re.findall(r'\w+', text.lower()))
            for label, cue in zip(visual['items'], visual['cues']):
                if cue < len(parts) and f' {normalize(label)} ' not in f' {normalize(parts[cue])} ':
                    add('visual_narration_mismatch', 'A diagram label is not present in its assigned narration sentence. Review its meaning and timing.')
        if visual['kind'] in {'stat_card','chart'}:
            numbers={float(n) for n in re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?(?!\w|\.\d)',scene['narration'].replace(',',''))}
            if any(v not in numbers for v in visual.get('values',visual.get('statValues',[]))):
                issues.append({'scene':i,'code':'unsupported_statistic','severity':'error','message':'These statistics do not appear in the narration. Replan this visual or supply supported source values.'})
        from backend.services.code_examples import select_spec
        if visual['kind']=='code' and not visual.get('codeLines') and not select_spec({**scene,'topic':document.get('topic','')}):
            issues.append({'scene':i,'code':'missing_code','severity':'error','message':'No code was supplied for this scene. Replan its visual or supply a code example.'})
        if len(previous)>=2 and previous[-2:]==[form,form]:
            add('repeated_layout','Three consecutive scenes use the same composition and motion. Consider a different visual approach.')
        if len(re.findall(r'\w+',scene['body']+' '+' '.join(visual['items'])))>45:
            add('visual_text_density','On-screen text is dense. Shorten the explanation or diagram labels.')
        seconds=len(scene['narration'].split())/2.5
        if seconds>15 and len(visual['items'])<2 and not demonstration:
            add('static_explanation','This scene may spend over 15 seconds on one visual. Add a demonstration or split the teaching point.')
        previous.append(form)
    return issues

def preview_scenes(scenes, durations=None):
    """Whole-sentence previews; narrated bookends use an explicitly excerpted review reel."""
    durations=durations or {s['id']:len(s['narration'].split())/2.2+1 for s in scenes}
    def choreography(row):
        return row.get('choreography') or row.get('visualPlan',{}).get('choreography') or row.get('visual',{}).get('choreography') or {}
    if len(scenes)>2 and choreography(scenes[0]).get('layout')=='intro' and choreography(scenes[-1]).get('layout')=='outro':
        selected=[scenes[0],scenes[-1]]
        for row in sorted(scenes[1:-1],key=lambda s:(bool(s.get('visual',{}).get('worked')),choreography(s).get('layout')=='budget'),reverse=True):
            if len(selected)>=4:break
            if sum(durations[s['id']] for s in selected)+durations[row['id']]<=120:selected.append(row)
        if sum(durations[s['id']] for s in selected)<=120:
            ids={s['id'] for s in selected}
            return [s for s in scenes if s['id'] in ids]
    candidates=[]
    for start in range(len(scenes)):
        rows=[]; seconds=0
        for row in scenes[start:]:
            duration=durations[row['id']]
            if seconds+duration>60:break
            rows.append(row); seconds+=duration
            if seconds>=40:break
        if rows:
            variety=len({r.get('visualPlan',{}).get('kind') or composition(r.get('visual',{'kind':'explanation'})) for r in rows})
            candidates.append(((seconds>=30,variety,min(seconds,40),-start),rows))
    if not candidates:raise ValueError('A scene exceeds the 60-second preview limit. Split its narration first.')
    return max(candidates,key=lambda pair:pair[0])[1]
