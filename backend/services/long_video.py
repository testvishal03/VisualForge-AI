"""Reviewed chapter plans with isolated, resumable chapter projects."""
import copy
import json
from backend.services.script_generator import write_json_atomic
from backend.services.run_state import fingerprint
from backend.services.editor_store import EditorStore, document_from_video
from backend.services.director import script_to_video, build_direction


def initialize(store, topic, minutes):
    if type(minutes) is not int or not 7 <= minutes <= 30:
        raise ValueError('Long videos require a target of 7–30 whole minutes.')
    project = store.create(topic, source={'mode': 'long', 'minutes': minutes})
    project['long_video'] = {'chapters': [], 'outline_approved': None, 'script_approved': None}
    write_json_atomic(store.folder(project['id']) / 'project.json', project)
    return project


def chapters_store(store, project):
    return EditorStore(store.folder(project['id']) / 'chapters')


def plan_key(project):
    return fingerprint(project['long_video']['chapters'])


def script_key(store, project):
    children = chapters_store(store, project)
    return fingerprint([project['long_video']['chapters'],
                        [children.load(c['id'])['document'] for c in project['long_video']['chapters']]])


def save(store, project, body):
    candidate = copy.deepcopy(project)
    data = candidate['long_video']
    children = chapters_store(store, project)
    updates = []
    if 'documents' in body:
        from backend.services.editor_store import validate_document
        from backend.services.director import direct_scene
        if not isinstance(body['documents'],dict) or 'chapters' in body or 'scripts' in body:
            raise ValueError('Save storyboard documents separately.')
        for cid, document in body['documents'].items():
            if cid not in {c['id'] for c in data['chapters']}:
                raise ValueError('Unknown chapter')
            child=children.load(cid); document=copy.deepcopy(document)
            video=validate_document(document)
            if video.topic != child['topic']:
                raise ValueError('Keep the chapter topic unchanged.')
            old={s['uid']:s for s in (child['document'] or {}).get('scenes',[])}
            for i,s in enumerate(document['scenes']):
                if s['uid'] in old and s['narration'] != old[s['uid']]['narration']:
                    demo=s['visual'].get('demo')
                    worked=s['visual'].get('worked')
                    s['visual']=direct_scene(video.scenes[i],i,len(video.scenes))
                    if demo:s['visual']['demo']=demo
                    if worked:s['visual']['worked']=worked
            if document != child['document']:
                child.update(document=document,revision=child['revision']+1); updates.append(child)
    if 'chapters' in body:
        rows = body['chapters']
        if not isinstance(rows, list) or len(rows) != len(data['chapters']) or not rows or any(not isinstance(c, dict) for c in rows):
            raise ValueError('Keep every chapter in the plan.')
        old = {c['id']: c for c in data['chapters']}
        if {c.get('id') for c in rows} != set(old) or len({c.get('id') for c in rows}) != len(rows):
            raise ValueError('Chapter IDs must match the saved plan.')
        for row in rows:
            if set(row) != {'id', 'title', 'focus', 'seconds', 'visual_goal'}:
                raise ValueError('Unexpected chapter fields.')
            for field, limit in [('title', 100), ('focus', 300), ('visual_goal', 160)]:
                if not isinstance(row[field], str) or not row[field].strip() or len(row[field]) > limit or any(ord(c) < 32 for c in row[field]):
                    raise ValueError(f'Invalid chapter {field}.')
            if type(row['seconds']) is not int or not 30 <= row['seconds'] <= 180:
                raise ValueError('Chapter targets must be 30–180 seconds.')
            if row != old[row['id']]:
                child = children.load(row['id'])
                child.update(document=None, revision=child['revision'] + 1)
                child['source']['minutes'] = row['seconds'] / 60
                updates.append(child)
        if sum(c['seconds'] for c in rows) != project['source']['minutes'] * 60:
            raise ValueError('Chapter times must add up to the full target duration.')
        data['chapters'] = copy.deepcopy(rows)
    if 'scripts' in body:
        if not isinstance(body['scripts'], dict):
            raise ValueError('Scripts must be keyed by chapter ID.')
        if 'chapters' in body:
            raise ValueError('Save the outline and scripts separately.')
        for cid, text in body['scripts'].items():
            row = next((c for c in data['chapters'] if c['id'] == cid), None)
            if row is None:
                raise ValueError('Unknown chapter.')
            child = children.load(cid)
            previous = '\n\n'.join(s['narration'] for s in (child['document'] or {}).get('scenes', []))
            if text != previous:
                video = script_to_video(row['title'], text)
                video = video.model_copy(update={'topic': child['topic']})
                child.update(document=document_from_video(video, build_direction(video)), revision=child['revision'] + 1)
                updates.append(child)
    # Validate approvals against prospective edits before publishing any files.
    prospective = {child['id']: child for child in updates}
    if body.get('approve_outline') and not data['chapters']:
        raise ValueError('Generate an outline first.')
    if body.get('approve_script') and (not data['chapters'] or any(not (prospective.get(c['id']) or children.load(c['id']))['document'] for c in data['chapters'])):
        raise ValueError('Every chapter needs a script before approval.')
    for child in updates:
        write_json_atomic(children.folder(child['id']) / 'project.json', child)
    if updates or data['chapters'] != project['long_video']['chapters']:
        data['script_approved'] = None
    if data['chapters'] != project['long_video']['chapters']:
        data['outline_approved'] = None
    if body.get('approve_outline'):
        if not data['chapters']:
            raise ValueError('Generate an outline first.')
        data['outline_approved'] = plan_key(candidate)
    if body.get('approve_script'):
        if not data['chapters'] or any(not children.load(c['id'])['document'] for c in data['chapters']):
            raise ValueError('Every chapter needs a script before approval.')
        data['script_approved'] = script_key(store, candidate)
    candidate['revision'] += 1
    write_json_atomic(store.folder(project['id']) / 'project.json', candidate)
    return candidate


def publish_chapters(jobs, project, nested, data, folder, profile):
    """Thumbnail and description for the joined chapter video, using each chapter's exact render props."""
    from backend.services.publishing import publish_safely, scene_seconds
    name = 'draft-props.json' if profile == 'draft' else 'render-props.json'
    scenes, parts = [], []
    for chapter in data['chapters']:
        props = nested.store.folder(chapter['id'])/name
        if not props.is_file():
            return None
        rows = json.loads(props.read_text(encoding='utf-8'))['videoData']['scenes']
        scenes += rows
        parts.append((chapter['title'], sum(scene_seconds(s) for s in rows)))
    style = {**jobs.workspaces.style(project['id']), 'agenda': [c['title'] for c in data['chapters']][:100]}
    video = {'title': project.get('topic') or data['chapters'][0]['title'], 'style': style, 'scenes': scenes}
    jobs.state.update(phase='thumbnail')
    return publish_safely(jobs, project, folder, video, lambda command, name: jobs.remotion(folder, command, name), profile, parts)


def nested_jobs(jobs, project):
    from backend.services.editor_jobs import EditorJobs
    nested = EditorJobs(jobs.root, chapters_store(jobs.store, project))
    nested.cancel = jobs.cancel
    nested.state = jobs.state
    nested.publishing = False
    # Chapter style and lifecycle belong to the parent workspace.
    nested.workspaces = copy.copy(jobs.workspaces)
    def chapter_style(child_id):
        style=jobs.workspaces.style(project['id'])
        ids=[c['id'] for c in project['long_video']['chapters']]
        # Bookends describe the whole lesson, so they list chapters rather than one chapter's scenes.
        titles=[c['title'] for c in project['long_video']['chapters'] if isinstance(c.get('title'),str) and c['title'].strip()][:100]
        return {**style,'showIntro':bool(ids and child_id==ids[0] and style.get('showIntro')),
                'showOutro':bool(ids and child_id==ids[-1] and style.get('showOutro')),
                **({'agenda':[t.strip()[:160] for t in titles]} if len(titles)>1 else {})}
    nested.workspaces.style = chapter_style
    nested.workspaces.for_project = lambda _: jobs.workspaces.for_project(project['id'])
    return nested


def present(jobs, project, result):
    nested = nested_jobs(jobs, project)
    rows = []
    for chapter in project['long_video']['chapters']:
        child = nested.store.load(chapter['id'])
        info = nested.present(child)
        row = {**chapter, 'script': '\n\n'.join(s['narration'] for s in (child['document'] or {}).get('scenes', [])),
               'duration': info.get('duration'), 'quality': info.get('quality'), 'layouts': [s['visual']['kind'] for s in (child['document'] or {}).get('scenes', [])]}
        row['preview_url'] = f"/media/{project['id']}/chapter/{chapter['id']}/draft" if info.get('draft_url') else None
        row['style_url']=f"/media/{project['id']}/chapter/{chapter['id']}/style" if info.get('style_url') else None
        row['document'] = child['document']
        row['visual_plan'] = info.get('visual_plan')
        row['audio']=info.get('audio',{})
        row['quality']=info.get('quality',{})
        row['review_style']=info.get('review_style',{})
        row['preview_urls']={uid:f"/media/{project['id']}/chapter/{chapter['id']}/preview/{uid}?v={child['previews'][uid]['key']}" for uid in info.get('preview_urls',{})}
        row['worked_examples']=info.get('worked_examples',{})
        row['motion_urls'] = {uid:f"/media/{project['id']}/chapter/{chapter['id']}/motion/{uid}?v={child['motion_previews'][uid]['key']}" for uid in info.get('motion_urls',{})}
        rows.append(row)
    result['chapter_details'] = rows
    result['visual_plan'] = {'scenes':[scene for row in rows for scene in (row.get('visual_plan') or {}).get('scenes',[])],
        'warnings':[{'scene':row['title']+' / '+str(warning['scene']),'message':warning['message']} for row in rows for warning in (row.get('visual_plan') or {}).get('warnings',[])]}
    result['outline_approved'] = project['long_video']['outline_approved'] == plan_key(project)
    result['script_approved'] = bool(rows) and project['long_video']['script_approved'] == script_key(jobs.store, project)
    measured = [r.get('duration', {}).get('measured_seconds') if r.get('duration') else None for r in rows]
    result['long_duration'] = {'target_seconds': project['source']['minutes'] * 60,
                             'measured_seconds': round(sum(measured), 2) if measured and all(v is not None for v in measured) else None}
    for kind, urlkey, route in [('draft_render', 'draft_url', 'draft'), ('render', 'video_url', 'video')]:
        record = project.get(kind)
        result[urlkey] = f"/media/{project['id']}/{route}" if jobs.artifact_ready(project, record) else None
    return result


def output_key(jobs, project, profile):
    from backend.services.worked_examples import model_dependency
    children=chapters_store(jobs.store,project)
    dependencies=[model_dependency(children.load(c['id'])['document']) for c in project['long_video']['chapters']]
    return fingerprint([dependencies,script_key(jobs.store, project), jobs.workspaces.style(project['id']), jobs.version, profile, 'chapters-v1'])


def perform(jobs, project, action, uid, instructions='Make this explanation concrete and concise.'):
    from backend.services.process_runner import python_stage
    from backend.schemas.video_schema import VideoScript
    folder = jobs.store.folder(project['id'])
    def py(name, args, script='long_video_worker.py'):
        if jobs.cancel.is_set():
            raise InterruptedError('Cancelled; completed chapters are saved.')
        log = folder / 'logs' / f'{name}.log'
        jobs.state.update(phase=name, log=str(log), log_offset=log.stat().st_size if log.exists() else 0)
        return python_stage(jobs.root / 'backend/scripts' / script, args, root=jobs.root,
                            folder=folder, name=name, timeout=3600, cancel_event=jobs.cancel)
    nested = nested_jobs(jobs, project)
    data = project['long_video']
    if action.startswith('long_scene_'):
        target=action.removeprefix('long_scene_')
        if target not in {'motion','replan','regenerate','audio','style_preview','prepare_example'}:
            raise ValueError('Unknown storyboard task')
        child=next((nested.store.load(c['id']) for c in data['chapters'] if any(s['uid']==uid for s in (nested.store.load(c['id'])['document'] or {}).get('scenes',[]))),None)
        if child is None:
            raise ValueError('Select a valid storyboard scene')
        nested._perform(child,target,uid,instructions,nested.store.folder(child['id']))
        if target in {'replan','regenerate'}:
            data['script_approved']=None
    elif action == 'long_outline':
        if data['chapters']:
            raise ValueError('An outline already exists. Edit it before approving.')
        output = folder / 'outline.json'
        py('chapter-outline', ['outline', project['topic'], str(project['source']['minutes']), output])
        plan = __import__('json').loads(output.read_text(encoding='utf-8'))
        for row in plan['chapters']:
            child = nested.store.create(row['title'], source={'mode': 'prompt', 'minutes': row['seconds'] / 60})
            data['chapters'].append({'id': child['id'], **row})
    elif action in {'long_scripts', 'long_adjust'}:
        if data['outline_approved'] != plan_key(project):
            raise ValueError('Review and approve the chapter outline first.')
        for index, row in enumerate(data['chapters']):
            if action == 'long_adjust' and row['id'] != uid:
                continue
            child = nested.store.load(row['id'])
            if action == 'long_scripts' and child['document']:
                continue
            source = nested.store.folder(row['id']) / 'chapter.json'
            context = folder / 'chapter-request.json'
            request = {'topic': project['topic'], 'chapter': row, 'index': index,
                       'titles': [c['title'] for c in data['chapters']], 'audience': jobs.workspaces.for_project(project['id'])['audience']}
            request['reference_script'] = project.get('source', {}).get('reference_script', '')[:10000]
            workspace = jobs.workspaces.for_project(project['id']) or {}
            request['playlist_context'] = workspace.get('current_topic', '')
            episode_ids = workspace.get('episodes', [])
            if project['id'] in episode_ids and episode_ids.index(project['id']) > 0:
                request['playlist_context'] = jobs.store.load(episode_ids[episode_ids.index(project['id']) - 1])['topic']
            if action == 'long_adjust':
                info = nested.present(child)
                measured = info['duration']['measured_seconds']
                if not measured:
                    raise ValueError('Measure narration before adjusting its duration.')
                request.update(previous=child['document'], measured_seconds=measured)
            write_json_atomic(context, request)
            py(f'chapter-{index + 1}-script', ['adjust' if action == 'long_adjust' else 'script', context, source])
            video = VideoScript.model_validate_json(source.read_text(encoding='utf-8')).model_copy(update={'topic': child['topic']})
            import json
            plan_file = source.with_suffix('.visuals.json')
            direction = json.loads(plan_file.read_text(encoding='utf-8')) if plan_file.is_file() else build_direction(video)
            for s in direction['scenes']:
                s['variant'] = (s['id'] + index) % 2
                s['transition'] = 'slide' if (s['id'] + index) % 3 == 0 else 'fade'
            nested.store.save(child['id'], child['revision'], document_from_video(video, direction))
            data['script_approved'] = None
            project['revision'] += 1
            write_json_atomic(folder / 'project.json', project)
    elif action == 'long_visuals':
        import json
        if not data['chapters'] or any(not nested.store.load(c['id'])['document'] for c in data['chapters']):
            raise ValueError('Generate chapter scripts before planning visuals.')
        for index, row in enumerate(data['chapters']):
            if jobs.cancel.is_set():
                raise InterruptedError('Cancelled; completed visual plans are saved.')
            child = nested.store.load(row['id'])
            child_folder = nested.store.folder(row['id'])
            from backend.services.editor_store import validate_document
            source, output = child_folder/'visual-source.json', child_folder/'visual-plan.json'
            write_json_atomic(source, validate_document(child['document']).model_dump())
            py(f'chapter-{index+1}-visuals', [source, output], script='plan_visuals.py')
            plan = json.loads(output.read_text(encoding='utf-8'))
            revised = copy.deepcopy(child['document'])
            for scene, visual in zip(revised['scenes'], plan['scenes']):
                scene['visual'] = {k:v for k,v in visual.items() if k != 'id'}
            nested.store.save(child['id'], child['revision'], revised)
            data['script_approved'] = None
            project['revision'] += 1
            write_json_atomic(folder/'project.json', project)
    elif action in {'long_audio', 'long_render_draft', 'long_render'}:
        if not data['chapters'] or any(not nested.store.load(c['id'])['document'] for c in data['chapters']):
            raise ValueError('Generate all chapter scripts first.')
        if action != 'long_audio' and data['script_approved'] != script_key(jobs.store, project):
            raise ValueError('Review and approve the scripts before rendering.')
        if action != 'long_audio' and jobs.artifact_ready(project, project.get('draft_render' if action == 'long_render_draft' else 'render')):
            jobs.state['message'] = 'Reused the complete verified chapter video.'
            return
        for index, row in enumerate(data['chapters']):
            child = nested.store.load(row['id'])
            jobs.state.update(chapter_index=index,chapter_total=len(data['chapters']))
            jobs.state['message'] = f"Chapter {index + 1}/{len(data['chapters'])}: {row['title']}"
            nested._perform(child, {'long_audio': 'audio', 'long_render_draft': 'render_draft', 'long_render': 'render'}[action], None, '', nested.store.folder(child['id']))
        if action != 'long_audio':
            profile = 'draft' if action == 'long_render_draft' else 'final'
            name = 'draft' if profile == 'draft' else 'video'
            request = {'profile': profile, 'chapters': [str(nested.store.folder(c['id'])) for c in data['chapters']], 'output': str(folder / f'{name}.pending.mp4')}
            manifest = folder / 'join-request.json'
            write_json_atomic(manifest, request)
            py('assemble-and-validate', ['join', manifest])
            pending = folder / f'{name}.pending.mp4'
            final = folder / f'{name}.mp4'
            pending.replace(final)
            from backend.services.run_state import file_hash
            project.pop('accepted_export',None)
            project.pop('publish',None)
            project['draft_render' if profile == 'draft' else 'render'] = {'key': output_key(jobs, project, profile), 'profile': profile, 'file': final.name, 'sha256': file_hash(final), 'styled': True}
            project['revision'] += 1
            write_json_atomic(folder / 'project.json', project)
            publish_chapters(jobs, project, nested, data, folder, profile)
            project = jobs.store.load(project['id'])
            return
    else:
        raise ValueError('Unknown long-video task.')
    project['revision'] += 1
    write_json_atomic(folder / 'project.json', project)
