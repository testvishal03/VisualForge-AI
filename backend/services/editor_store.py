"""Local JSON projects, stable scene identity, optimistic revisions, validated layouts."""
import copy
import json
from pathlib import Path
import re
import threading
import uuid
import math

from backend.schemas.video_schema import VideoScript, Scene
from backend.services.quality import review_video
from backend.services.run_state import fingerprint, file_hash
from backend.services.script_generator import write_json_atomic
from backend.services.director import ICONS, sentences, direct_scene

KINDS = {'title', 'explanation', 'process', 'comparison', 'example', 'takeaway', 'relationship', 'cycle', 'timeline', 'components', 'water_cycle', 'chart', 'neural_net', 'code', 'stat_card', 'quote', 'analogy'}


def validate_document(document):
    if not isinstance(document, dict) or set(document) != {'title', 'topic', 'scenes'}:
        raise ValueError('A project requires title, topic and scenes')
    scenes, seen = [], set()
    for index, scene in enumerate(document['scenes'], 1):
        uid = scene.get('uid', '')
        if not re.fullmatch(r'[a-f0-9]{12}', uid) or uid in seen:
            raise ValueError('Every scene requires a unique stable identity')
        seen.add(uid)
        if set(scene) != {'uid', 'headline', 'body', 'narration', 'visual'}:
            raise ValueError('Unexpected or missing scene fields')
        visual = scene['visual']
        if not isinstance(visual, dict) or not {'kind', 'items'} <= set(visual) or set(visual)-{'kind','items','directed','planned','motion','layout','icon','cues','icons','variant','transition','values','statValues','codeLines','worked','demo','treatment','choreography','shotOverrides','concepts'} or visual['kind'] not in KINDS:
            raise ValueError('Unknown visual layout')
        if not isinstance(visual['items'],list): raise ValueError('Visual items must be a list')
        count = 3 if visual['kind'] == 'process' else 2 if visual['kind'] == 'comparison' else 4 if visual['kind']=='water_cycle' else len(visual['items']) if visual['kind'] in {'relationship','cycle','timeline','components','chart','neural_net','stat_card'} else 0
        if visual['kind'] in {'cycle','timeline','components','chart','neural_net','stat_card'} and not 2<=count<=4:
            raise ValueError('Diagrams require two to four labels')
        if visual['kind']=='chart':
            values=visual.get('values')
            if not isinstance(values,list) or len(values)!=count or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=100 for v in values):
                raise ValueError('Charts require one percentage from 0 to 100 per label')
        elif 'values' in visual and visual['kind'] != 'stat_card': raise ValueError('Only charts accept numeric values')
        if visual['kind']=='stat_card':
            values=visual.get('values',visual.get('statValues'))
            if 'values' in visual and 'statValues' in visual or not isinstance(values,list) or len(values)!=count or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
                raise ValueError('Statistic cards require one finite source value per label')
        elif 'statValues' in visual:
            raise ValueError('Only statistic cards accept statValues')
        if visual['kind']=='code':
            lines=visual.get('codeLines')
            if lines is not None and (not isinstance(lines,list) or not 1<=len(lines)<=30 or any(not isinstance(line,str) or len(line)>100 or any(ord(c)<32 and c!='\t' for c in line) for line in lines) or not any(line.strip() for line in lines)):
                raise ValueError('Code scenes require 1-30 authored code lines, at most 100 characters each')
        elif 'codeLines' in visual:
            raise ValueError('Only code scenes accept codeLines')
        if visual['kind']=='relationship' and count not in (2,3):
            raise ValueError('Relationships require two or three labels')
        limit = 180 if visual['kind']=='comparison' else 70
        if not isinstance(visual['items'], list) or len(visual['items']) != count:
            raise ValueError(f"{visual['kind']} requires {count} labels")
        for item in visual['items']:
            if not isinstance(item, str) or not item.strip() or len(item) > limit:
                raise ValueError(f'Visual labels must be nonempty and at most {limit} characters')
            Scene.plain_text(item)
        if 'directed' in visual and visual['directed'] is not True:
            raise ValueError('Invalid automatic direction flag')
        if 'planned' in visual and visual['planned'] is not True:
            raise ValueError('Invalid semantic planning flag')
        from backend.services.scene_direction import LAYOUTS, COMPATIBLE
        layout=visual.get('layout','auto')
        if not isinstance(layout,str) or layout not in LAYOUTS or layout!='auto' and visual['kind'] not in COMPATIBLE[layout]:
            raise ValueError('Composition does not support this visual kind')
        if visual.get('motion', 'flow') not in {'flow','assemble','focus','reveal'}:
            raise ValueError('Unknown animation treatment')
        if 'icon' in visual and visual['icon'] not in ICONS:
            raise ValueError('Unknown icon')
        if 'icons' in visual and (not isinstance(visual['icons'],list) or len(visual['icons'])!=count or any(i not in ICONS for i in visual['icons'])):
            raise ValueError('Every visual item requires a known icon')
        if 'variant' in visual and (type(visual['variant']) is not int or visual['variant'] not in (0,1)):
            raise ValueError('Unknown composition')
        if 'transition' in visual and visual['transition'] not in {'fade','slide','wipe','zoom'}:
            raise ValueError('Unknown transition')
        if visual.get('treatment','build') not in {'build','focus','compare'}:
            raise ValueError('Unknown visual treatment')
        if 'concepts' in visual:
            # Planner-chosen concepts for explanation and example scenes; stale ones are ignored when drawing.
            concepts=visual['concepts']
            if visual['kind'] not in {'explanation','example'} or not isinstance(concepts,list) or len(concepts)>6 or any(
                    not isinstance(c,dict) or set(c)!={'label','sentence'} or not isinstance(c['label'],str) or not 1<=len(c['label'])<=60
                    or type(c['sentence']) is not int or not 0<=c['sentence']<=20 for c in concepts):
                raise ValueError('Invalid scene concepts')
            for c in concepts:
                Scene.plain_text(c['label'])
        if 'choreography' in visual:
            from backend.services.choreography import validate
            validate(visual['choreography'], scene['narration'])
        if 'shotOverrides' in visual:
            from backend.services.shot_direction import MODES,plan
            overrides=visual['shotOverrides']
            if not isinstance(overrides,dict) or len(overrides)>20 or any(not isinstance(key,str) or not key.isdecimal() or str(int(key))!=key or int(key)>=len(sentences(scene['narration'])) or not isinstance(mode,str) or mode not in MODES for key,mode in overrides.items()) or not plan(scene):
                raise ValueError('Shot choices must reference illustrated narration sentences')
        if 'demo' in visual:
            from backend.services.code_examples import validate_spec
            validate_spec(visual['demo'],scene['narration'])
        if 'worked' in visual:
            from backend.services.worked_examples import validate_spec
            validate_spec(visual['worked'],scene['narration'])
        cues = visual.get('cues', [])
        if not isinstance(cues, list) or len(cues) not in (0,count) or any(type(c) is not int or not 0 <= c < len(sentences(scene['narration'])) for c in cues) or cues != sorted(cues):
            raise ValueError('Visual cues must reference ordered narration sentences')
        scenes.append({'id': index, **{k: scene[k] for k in ['headline', 'body', 'narration']}})
    return VideoScript.model_validate({'title': document['title'], 'topic': document['topic'], 'scenes': scenes})


def document_from_video(video, visuals=None):
    by_id = {s['id']: {k:v for k,v in s.items() if k != 'id'} for s in (visuals or {}).get('scenes', [])}
    result = {'title': video.title, 'topic': video.topic, 'scenes': []}
    for index, scene in enumerate(video.scenes):
        default = 'title' if index == 0 else 'takeaway' if index == len(video.scenes)-1 else 'explanation'
        result['scenes'].append({'uid': uuid.uuid4().hex[:12], **scene.model_dump(exclude={'id'}),
                                 'visual': by_id.get(scene.id, {'kind': default, 'items': []})})
    validate_document(result)
    return result


class EditorStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self.lock = threading.RLock()

    def folder(self, project_id):
        if not isinstance(project_id, str) or not re.fullmatch('[a-f0-9]{12}', project_id):
            raise ValueError('Invalid project ID')
        return self.directory/project_id

    def load(self, project_id):
        return json.loads((self.folder(project_id)/'project.json').read_text(encoding='utf-8'))

    def create(self, topic, document=None, source=None):
        if document:
            validate_document(document)
        project_id = uuid.uuid4().hex[:12]
        project = {'id': project_id, 'topic': topic, 'revision': 1, 'document': document, 'previews': {}, 'render': None}
        if source:
            project.update(source=source, directed=True)
        write_json_atomic(self.folder(project_id)/'project.json', project)
        return project

    def save(self, project_id, revision, document):
        with self.lock:
            current = self.load(project_id)
            if type(revision) is not int or revision != current['revision']:
                raise ValueError('This project changed in another window. Reload before saving.')
            document = copy.deepcopy(document)
            old = {s['uid']: s for s in (current['document'] or {}).get('scenes', [])}
            for i, row in enumerate(document.get('scenes', [])):
                if row.get('visual', {}).get('directed') and row.get('uid') in old and row['narration'] != old[row['uid']]['narration']:
                    scene = Scene.model_validate({'id':i+1, **{k:row[k] for k in ('headline','body','narration')}})
                    demo=row['visual'].get('demo')
                    worked=row['visual'].get('worked')
                    row['visual'] = direct_scene(scene, i, len(document['scenes']))
                    if demo:row['visual']['demo']=demo
                    if worked:row['visual']['worked']=worked
            video = validate_document(document)
            if video.topic != current['topic']:
                raise ValueError('The topic cannot change inside an existing project')
            document = copy.deepcopy(document)
            document['title'] = video.title
            for row, scene in zip(document['scenes'], video.scenes):
                row.update(scene.model_dump(exclude={'id'}))
            current.update(document=document, revision=revision+1)
            write_json_atomic(self.folder(project_id)/'project.json', current)
            return current

    def update_artifact(self, project_id, kind, record, uid=None):
        with self.lock:
            current = self.load(project_id)
            if kind in {'render','draft_render'}:
                current.pop('accepted_export',None)
                # A new export needs its own thumbnail and description.
                current.pop('publish',None)
            if kind == 'motion':
                current.setdefault('motion_previews', {})[uid] = record
            elif kind == 'preview':
                current['previews'][uid] = record
            else:
                current[kind] = record
            write_json_atomic(self.folder(project_id)/'project.json', current)

    def approve_storyboard(self, project_id, revision):
        with self.lock:
            current = self.load(project_id)
            if type(revision) is not int or revision != current['revision']:
                raise ValueError('Project changed. Reload before approving.')
            current.update(storyboard_approved=fingerprint(current['document']), revision=revision+1)
            write_json_atomic(self.folder(project_id)/'project.json', current)
            return current

    def list(self):
        result = []
        for file in self.directory.glob('*/project.json'):
            try:
                data = self.load(file.parent.name)
                result.append({'id': data['id'], 'title': (data['document'] or {}).get('title', data['topic']), 'revision': data['revision']})
            except (ValueError, OSError, KeyError):
                continue
        return result


def renderer_version(root):
    files = [*sorted((root/'renderer/src').rglob('*.ts')), *sorted((root/'renderer/src').rglob('*.tsx')), root/'renderer/remotion.config.ts']
    if (root/'renderer/package-lock.json').is_file():files.append(root/'renderer/package-lock.json')
    files += [p for p in [root/'backend/services/teaching_plan.py',root/'backend/services/code_examples.py',root/'backend/services/visual_storytelling.py',root/'backend/services/scene_direction.py',root/'backend/services/choreography.py',root/'backend/services/shot_direction.py',root/'backend/services/visual_actions.py',root/'backend/services/scene_cache.py'] if p.is_file()]
    return fingerprint([file_hash(p) for p in files])


def artifact_key(document, version, uid=None):
    if uid is None:
        return fingerprint([document, version])
    index, scene = next((i,s) for i,s in enumerate(document['scenes']) if s['uid']==uid)
    return fingerprint([document['title'], len(document['scenes']), index, scene, version])


def quality(document):
    from backend.services.scene_direction import visual_issues
    result=review_video(validate_document(document))
    # Drafting rejects weak/repeated AI prose so it can try again. Export must
    # preserve authored scripts, where repetition may be an intentional recap.
    for issue in result['issues']:
        if issue['code'] in {'repeated_explanation', 'weak_example'}:
            issue['severity'] = 'warning'
    result['issues'].extend(visual_issues(document))
    from backend.services.worked_examples import narration_issues,model_dependency,read_result,ROOT
    model=model_dependency(document)
    from backend.services.code_examples import narration_issues as demonstration_issues
    for i,scene in enumerate(document['scenes'],1):
        result['issues'].extend({**issue,'scene':i} for issue in demonstration_issues({**scene,'topic':document['topic']}))
        spec=scene['visual'].get('worked')
        measured=read_result(spec['input'],model,ROOT/'data/worked-example-cache') if spec and model and not model.get('unavailable') else None
        result['issues'].extend({**issue,'scene':i} for issue in narration_issues(scene,measured))
    result['status']='needs_review' if result['issues'] else 'checks_passed'
    return result


def require_export_quality(document):
    errors = [issue for issue in quality(document)['issues'] if issue['severity'] == 'error']
    if errors:
        details = ' '.join(f"Scene {issue['scene']}: {issue['message']}" for issue in errors[:5])
        if len(errors) > 5:
            details += f' Plus {len(errors)-5} more issues; open the editor quality review.'
        raise ValueError('Video quality check: ' + details)
