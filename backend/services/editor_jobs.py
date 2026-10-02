"""One local task at a time, with subprocess isolation and explicit cancellation."""
import copy
import json
import shutil
from backend.services.render_assets import RENDER_CONCURRENCY
import math
from pathlib import Path
import threading
import time
import uuid

from backend.schemas.video_schema import VideoScript, Scene
from backend.services.editor_store import validate_document, document_from_video, artifact_key, renderer_version, quality, require_export_quality
from backend.services.incremental_audio import cached_speech
from backend.services.process_runner import python_stage, execute, node_executable
from backend.services.run_state import file_hash
from backend.services.script_generator import write_json_atomic
from backend.services.director import build_direction, timed_visual, direct_scene
from backend.services.workspaces import Workspaces
from backend.services.duration import duration_report
from backend.services.worked_examples import model_dependency, summaries, validate_result, narration_issues


class EditorJobs:
    def __init__(self, root, store):
        self.root, self.store = root, store
        self.thread = None
        self.cancel = threading.Event()
        self.state = {'status': 'idle'}
        self.version = renderer_version(root)
        # Whole videos get a thumbnail and description; chapter renders inside a long video do not.
        self.publishing = True
        self.workspaces = Workspaces(store)

    def output_key(self, project, uid=None, profile='final'):
        from backend.services.run_state import fingerprint
        if 'long_video' in project:
            from backend.services.long_video import output_key
            return output_key(self, project, profile)
        # Legacy artifacts remain inspectable; new artifacts include style and quality.
        return fingerprint([artifact_key(project['document'], self.version, uid), self.workspaces.style(project['id']), profile, model_dependency(project['document'],uid)])

    def story_key(self,project,start_uid):
        from backend.services.run_state import fingerprint
        return fingerprint([self.output_key(project,None,'draft'),'story-preview-v1',start_uid])

    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    def status(self):
        result = copy.deepcopy(self.state)
        if result.get('status') == 'running':
            result['elapsed_seconds'] = round(time.time()-result['started'])
        log = result.pop('log', None)
        offset = result.pop('log_offset', 0)
        if log and Path(log).is_file():
            with Path(log).open('rb') as stream:
                stream.seek(max(offset, Path(log).stat().st_size-4000))
                result['progress'] = stream.read().decode('utf-8', errors='replace').splitlines()[-8:]
        return result

    def start(self, project_id, action, uid=None, instructions=''):
        with self.store.lock:
            if self.busy():
                raise ValueError('Another task is running. Wait or cancel it first.')
            project = self.store.load(project_id)
            self.workspaces.require_active(project_id)
            if 'long_video' in project:
                if action not in {'long_outline', 'long_scripts', 'long_visuals', 'long_audio', 'long_adjust', 'long_render_draft', 'long_render', 'long_scene_motion', 'long_scene_replan', 'long_scene_regenerate', 'long_scene_audio', 'long_scene_style_preview', 'long_scene_prepare_example', 'auto_generate', 'expand_script', 'visual_preview', 'propose_visual'}:
                    raise ValueError('Choose a chapter workflow action.')
                if action == 'long_adjust' and uid not in {c['id'] for c in project['long_video']['chapters']}:
                    raise ValueError('Select a valid chapter.')
            else:
                if action not in {'draft', 'generate', 'audio', 'preview', 'motion', 'regenerate', 'render', 'render_draft', 'replan', 'style_preview', 'story_preview', 'prepare_example', 'auto_generate', 'expand_script', 'visual_preview', 'propose_visual'}:
                    raise ValueError('Unknown task')
                if action == 'draft' and project['document'] is not None:
                    raise ValueError('Create a new project to generate a new full draft')
                if action not in {'draft','generate','auto_generate'} and project['document'] is None:
                    raise ValueError('Generate a draft first')
                if action == 'generate' and not project.get('directed'):
                    raise ValueError('Automatic generation requires a prompt or script project')
                if action in {'preview', 'motion', 'regenerate', 'replan', 'prepare_example','story_preview'} and not any(s['uid']==uid for s in project['document']['scenes']):
                    raise ValueError('Select a valid scene')
                if action == 'audio' and uid and not any(s['uid']==uid for s in project['document']['scenes']):
                    raise ValueError('Select a valid scene')
                if action in {'render','render_draft'}:
                    require_export_quality(project['document'])
                if action in {'render','render_draft'} and project.get('source',{}).get('review_first'):
                    from backend.services.run_state import fingerprint
                    if project.get('storyboard_approved') != fingerprint(project['document']):
                        raise ValueError('Review and approve the current storyboard before rendering.')
            self.cancel.clear()
            self.state = {'id': uuid.uuid4().hex[:12], 'project': project_id, 'action': action, 'status': 'running', 'phase': 'Starting', 'started': time.time()}
            self.thread = threading.Thread(target=self._work, args=(project, action, uid, instructions), daemon=False)
            self.thread.start()
            return self.status()

    def _work(self, project, action, uid, instructions):
        folder = self.store.folder(project['id'])
        try:
            self._perform(project, action, uid, instructions, folder)
            self.state.update(status='complete', phase='Complete')
        except InterruptedError as exc:
            self.state.update(status='cancelled', error=str(exc), phase='Cancelled')
        except Exception as exc:
            self.state.update(status='failed', error=str(exc), phase='Failed')
        finally:
            self.state['seconds'] = round(time.time()-self.state['started'], 3)
            write_json_atomic(folder/'last-job.json', self.state)

    def _perform(self, project, action, uid, instructions, folder):
        if action=='propose_visual':
            from backend.services.episode_review import propose
            return propose(self,project,uid,instructions)
        if action == 'visual_preview':
            from backend.services.visual_storytelling import preview
            return preview(self, project, folder)
        if action == 'expand_script':
            from backend.services.script_review import expand
            return expand(self, project, folder)
        if action=='auto_generate':
            from backend.services.automatic_video import perform
            return perform(self,project,folder)
        if 'long_video' in project:
            from backend.services.long_video import perform
            return perform(self, project, action, uid, instructions)
        def phase(name):
            log = folder/'logs'/f'{name}.log'
            self.state.update(phase=name, log=str(log), log_offset=log.stat().st_size if log.exists() else 0)

        def py(name, script, args):
            if self.cancel.is_set():
                raise InterruptedError('Cancelled')
            phase(name)
            return python_stage(self.root/'backend/scripts'/script, args, root=self.root, folder=folder, name=name, timeout=3600, cancel_event=self.cancel)
        def render(command, name):
            phase(name)
            return self.remotion(folder, command, name)
        if action == 'draft' or action == 'generate' and project['document'] is None:
            source = folder/'draft.json'
            workspace = self.workspaces.for_project(project['id'])
            py('draft', 'generate_script.py', [project['topic'], '--output', source, '--checkpoint-dir', folder/'drafts', '--minutes', str(project.get('source', {}).get('minutes', 2)), '--audience', workspace['audience'] if workspace else 'beginners'])
            video = VideoScript.model_validate_json(source.read_text(encoding='utf-8'))
            plan = build_direction(video) if project.get('directed') else None
            project = self.store.save(project['id'], project['revision'], document_from_video(video, plan))
            if action == 'draft':
                return
        if action == 'generate':
            # Both prompt-generated and pasted scripts pass through the semantic visual planner. Long
            # scripts would need ~40 s per scene, so only their weakest rule-directed scenes are
            # planned, within a fixed time budget; the rest keep their narration-based visuals.
            from backend.services.script_check import LONG_VIDEO_PLANNING_SECONDS, MODEL_PLANNING_LIMIT, SECONDS_PER_PLANNED_SCENE
            scenes = project['document']['scenes']
            if not all(s['visual'].get('planned') for s in scenes):
                long = len(scenes) > MODEL_PLANNING_LIMIT
                only = None
                if long:
                    from backend.services.visual_quality import weak_scenes
                    only = weak_scenes(project['document'], LONG_VIDEO_PLANNING_SECONDS // SECONDS_PER_PLANNED_SCENE)
                plan = None
                if not long or only:
                    video = validate_document(project['document'])
                    source = folder/'visual-source.json'
                    output = folder/'visual-plan.json'
                    write_json_atomic(source, video.model_dump())
                    args = [source, output, *(['--only', ','.join(map(str, only)), '--budget', str(LONG_VIDEO_PLANNING_SECONDS)] if long else [])]
                    if long:
                        self.state['message'] = f'AI planning the {len(only)} weakest of {len(scenes)} scenes (about {LONG_VIDEO_PLANNING_SECONDS // 60} minutes)'
                    try:
                        py('visual-direction', 'plan_visuals.py', args)
                        plan = json.loads(output.read_text(encoding='utf-8'))
                    except (RuntimeError, OSError, ValueError) as exc:
                        if not long:
                            raise
                        # A long video never depended on the model; it keeps its rule-based visuals.
                        self.state['message'] = f'AI planning was skipped ({str(exc)[:160]}); narration-based visuals are used.'
                revised = copy.deepcopy(project['document'])
                for number, row in enumerate(revised['scenes'], 1):
                    # Long videos take only the scenes the model actually planned; a scene it failed on keeps its visual.
                    visual = plan['scenes'][number-1] if plan and (only is None or number in plan.get('model_planned', [])) else None
                    if visual is None:
                        row['visual']['planned'] = True
                        continue
                    authored={key:row['visual'][key] for key in ('demo','worked') if key in row['visual']}
                    row['visual'] = {k:v for k,v in visual.items() if k != 'id'}
                    row['visual'].update(authored)
                if revised != project['document']:
                    project = self.store.save(project['id'], project['revision'], revised)
            if project.get('source',{}).get('review_first'):
                self.state['result_kind'] = 'storyboard'
                self.state['message'] = 'Storyboard ready for review. Inspect scenes and animations, then approve before exporting.'
                return
            if not project.get('storyboard_approved'):
                self.store.approve_storyboard(project['id'], project['revision'])
                project = self.store.load(project['id'])
            action = 'render_draft' if project.get('source',{}).get('profile')=='draft' else 'render'
        profile = 'draft' if action in {'render_draft','motion','style_preview','story_preview'} else 'final'
        if action=='render_draft': action='render'
        document = project['document']
        if action == 'render':
            from backend.services.script_review import require_approval
            require_approval(project)
            require_export_quality(document)
        video = validate_document(document)
        from backend.services.teaching_plan import plan_document, timed_plan
        from backend.services.run_state import fingerprint
        write_json_atomic(folder/'teaching-plan.json', {'document_key':fingerprint(document), 'scenes':plan_document(document)})
        def prepare_worked(rows):
            inputs=list(dict.fromkeys(s['visual']['worked']['input'] for s in rows if s['visual'].get('worked')))
            if not inputs:return {}
            src,out=folder/'worked-inputs.json',folder/'worked-results.json'
            write_json_atomic(src,inputs)
            py('worked-examples','prepare_examples.py',[src,out])
            results=json.loads(out.read_text(encoding='utf-8'))
            for row in rows:
                spec=row['visual'].get('worked')
                if not spec:continue
                measured=results[spec['input']]
                validate_result(measured)
                if measured['input']!=spec['input'] or measured['model']!=model_dependency(document):raise ValueError('Example model or input changed; prepare again')
                errors=[i['message'] for i in narration_issues(row,measured) if i['severity']=='error']
                if errors:raise ValueError(' '.join(errors))
            return results
        if action=='prepare_example':
            rows=[s for s in document['scenes'] if s['uid']==uid]
            if not rows or not rows[0]['visual'].get('worked'):raise ValueError('Enable a worked example first')
            prepare_worked(rows)
            self.state['message']='Measured example ready. Review the continuation and play the scene.'
            return
        if action=='replan':
            revised=copy.deepcopy(document)
            index=next(i for i,s in enumerate(revised['scenes']) if s['uid']==uid)
            source, output = folder/'visual-source.json', folder/'visual-plan-scene.json'
            write_json_atomic(source, video.model_dump())
            py('visual-direction', 'plan_visuals.py', [source, output, '--scene-id', str(index+1), '--instructions', instructions])
            visual = json.loads(output.read_text(encoding='utf-8'))['scenes'][0]
            demo=revised['scenes'][index]['visual'].get('demo')
            worked=revised['scenes'][index]['visual'].get('worked')
            revised['scenes'][index]['visual']={k:v for k,v in visual.items() if k != 'id'}
            if demo:revised['scenes'][index]['visual']['demo']=demo
            if worked:revised['scenes'][index]['visual']['worked']=worked
            if not project.get('directed'):
                revised['scenes'][index]['visual'].pop('directed',None)
            self.store.save(project['id'],project['revision'],revised)
            self.state['message']='Replanned only this scene. Its narration is unchanged.'
            return
        source = folder/'source.json'
        write_json_atomic(source, video.model_dump())
        if action == 'regenerate':
            index = next(i for i,s in enumerate(document['scenes']) if s['uid']==uid)
            output = folder/'regenerated.json'
            py('regenerate', 'regenerate_scene.py', [source, output, '--scene-id', str(index+1), '--instructions', instructions])
            scene = Scene.model_validate_json(output.read_text(encoding='utf-8'))
            revised = copy.deepcopy(document)
            revised['scenes'][index].update(scene.model_dump(exclude={'id'}))
            # Generated text may no longer support old diagram labels.
            revised['scenes'][index]['visual'] = direct_scene(scene, index, len(video.scenes)) if project.get('directed') else {'kind': 'explanation', 'items': []}
            self.store.save(project['id'], project['revision'], revised)
            self.state['message'] = 'Only the selected scene changed. Review its updated text and layout before rendering.'
            return
        key = self.story_key(project,uid) if action=='story_preview' else self.output_key(project, uid if action in {'preview','motion'} else None, profile)
        record = project.get('story_render') if action=='story_preview' else project.get('style_render') if action=='style_preview' else project.get('motion_previews',{}).get(uid) if action=='motion' else project['previews'].get(uid) if action == 'preview' else project.get('draft_render' if profile=='draft' else 'render') if action == 'render' else None
        if record and record['key']==key:
            target = folder/record['file']
            if target.is_file() and file_hash(target)==record['sha256']:
                self.state['message'] = 'Reused the current verified output.'
                return
        selected = [s for s in video.scenes if document['scenes'][s.id-1]['uid']==uid] if uid and action in {'preview','motion','audio'} else video.scenes
        if action=='story_preview':
            from backend.services.shot_direction import select_contiguous
            directed=bool(project.get('directed') or any(s['visual'].get('worked') for s in document['scenes']))
            durations={}
            for row in document['scenes']:
                speech=cached_speech(self.root/'renderer/public',row['narration'],self.voice(project['id']),directed=directed)
                durations[row['uid']]=speech[1] if speech else len(row['narration'].split())/135*60
            selected_uids={s['uid'] for s in select_contiguous(document['scenes'],uid,durations)}
            selected=[s for s in video.scenes if document['scenes'][s.id-1]['uid'] in selected_uids]
        if action=='style_preview':
            from backend.services.scene_direction import preview_scenes
            from backend.services.visual_storytelling import plan_document as preview_plan
            planned = preview_plan(document)['scenes']
            candidates=[{**s.model_dump(),'visual':document['scenes'][s.id-1]['visual'],'visualPlan':planned[s.id-1]} for s in video.scenes]
            ids={s['id'] for s in preview_scenes(candidates)}
            selected=[s for s in video.scenes if s.id in ids]
        worked_results=prepare_worked([document['scenes'][s.id-1] for s in selected]) if action!='audio' else {}
        measured=self.measure_explainers([document['scenes'][s.id-1] for s in selected],folder,py) if action!='audio' else {'next':{},'tokens':{},'maps':{}}
        next_tokens,tokenized,maps=measured['next'],measured['tokens'],measured.get('maps',{})
        selected_source = folder/'speech-source.json'
        write_json_atomic(selected_source, {'title': video.title, 'topic': video.topic, 'scenes': [s.model_dump() for s in selected]})
        metadata = folder/'speech.generated.json'
        py('audio', 'generate_audio.py', ['--input', selected_source, '--output', metadata, '--incremental', *(['--directed'] if project.get('directed') or any(s['visual'].get('worked') for s in document['scenes']) else []), '--voice', self.voice(project['id'])])
        data = json.loads(metadata.read_text(encoding='utf-8'))
        self.state['audio_cache'] = data['cache']
        if action=='story_preview':
            from backend.services.shot_direction import select_contiguous
            durations={document['scenes'][s['id']-1]['uid']:s['duration'] for s in data['scenes']}
            exact=select_contiguous([document['scenes'][s['id']-1] for s in data['scenes']],uid,durations)
            chosen={s['uid'] for s in exact}
            data['scenes']=[s for s in data['scenes'] if document['scenes'][s['id']-1]['uid'] in chosen]
            self.state['sample_scene_ids']=[s['id'] for s in data['scenes']]
        if action == 'audio':
            return
        from backend.services.visual_storytelling import plan_document as visual_plan, timed_plan as timed_visual_plan
        directions = visual_plan(document)['scenes']
        recent_forms = []  # diagram layouts already used, so neighbouring scenes look different
        for scene in data['scenes']:
            if scene.get('beats'):
                scene['visualPlan'] = timed_visual_plan(directions[scene['id']-1], scene['beats'])
                authored = document['scenes'][scene['id']-1]
                from backend.services.choreography import compile_scene, timed
                choreography = compile_scene(authored)
                if choreography:scene['choreography']=timed(choreography,scene['beats'])
                if choreography:
                    from backend.services.shot_direction import timed as timed_shots
                    shots=timed_shots(authored,scene['beats'])
                    if shots:scene['shots']=shots
                    from backend.services.visual_actions import timed as timed_actions
                    actions=timed_actions(authored,scene['beats'],recent_forms)
                    if actions:
                        scene['actions']=actions
                        recent_forms.append(actions['form'])
                scene['teaching'] = timed_plan({**scene,'visual':authored['visual'],'topic':document['topic']}, scene['beats'])
                from backend.services.code_examples import timed_example
                demonstration = timed_example({**authored,'topic':document['topic']},scene['beats'])
                if demonstration:scene['demonstration']=demonstration
                # Narration that explains next-token prediction, noise-to-image, judge-vs-create
                # or limitations gets its dedicated explainer animation.
                from backend.services.explainers import plan as plan_explainer, timed as timed_explainer
                explainer = None if demonstration or authored['visual'].get('worked') else plan_explainer(authored)
                if explainer and explainer['kind']=='next_token' and explainer['prompt'] in next_tokens:
                    # Measured odds from the installed model replace the illustrative example.
                    from backend.services.next_token import shown
                    tokens,probs=shown(next_tokens[explainer['prompt']])
                    if tokens:explainer.update(candidates=tokens,probs=probs,measured=True,model=self.model_name())
                if explainer and explainer['kind']=='tokens':
                    # Only the model's own tokenization is drawn; without it the scene keeps its normal visual.
                    found=tokenized.get(explainer['text'])
                    explainer=dict(explainer,pieces=found['pieces'],ids=found['ids'],model=self.model_name()) if found else None
                if explainer and explainer['kind']=='embedding_map':
                    # Measured positions and nearest-neighbour similarities replace the illustrative layout.
                    found=maps.get(tuple(p['label'] for p in explainer['points']))
                    if found:
                        from backend.services.embeddings import MODEL_NAME, nearest_links
                        explainer=dict(explainer,points=[dict(p,xy=xy) for p,xy in zip(explainer['points'],found['xy'])],
                                       links=nearest_links(found['similarity']),measured=True,model=MODEL_NAME)
                if explainer:scene['explainer']=timed_explainer(explainer,scene['beats'])
            scene['visual'] = timed_visual(document['scenes'][scene['id']-1]['visual'], scene['narration'], scene.get('beats', []))
            if scene.get('demonstration'):
                scene['visual'] = {'kind':'example','items':[],'directed':True,'revealAt':[],'transition':'fade'}
            if scene['visual'].get('worked'):
                scene['visual']['workedData']=worked_results[scene['visual']['worked']['input']]
        if action=='style_preview':
            from backend.services.scene_direction import preview_scenes
            data['scenes']=preview_scenes(data['scenes'],{s['id']:math.ceil((s['duration']+.5)*30)/30 for s in data['scenes']})
            self.state['sample_scene_ids']=[s['id'] for s in data['scenes']]
            self.state['message']='Visual preview uses complete scenes. Narrated intros and outros are included with selected excerpts when available.'
        data['style']=self.workspaces.style(project['id'])
        # Narrated bookends already include their own measured audio and title treatment.
        if data['scenes'][0].get('choreography',{}).get('layout')=='intro':data['style']['showIntro']=False
        if data['scenes'][-1].get('choreography',{}).get('layout')=='outro':data['style']['showOutro']=False
        if action in {'preview','motion','style_preview','story_preview'}:
            data['style']={**data['style'],'showIntro':False,'showOutro':False}
        props = folder/'story-props.json' if action=='story_preview' else folder/'style-props.json' if action=='style_preview' else folder/f'motion-{uid}-props.json' if action=='motion' else folder/'preview-props.json' if action == 'preview' else folder/('draft-props.json' if profile=='draft' else 'render-props.json')
        if action == 'preview':
            data['previewTotal'] = len(document['scenes'])
        write_json_atomic(props, {'videoData': data})
        if action == 'preview':
            pending, final = folder/'preview.pending.png', folder/f'preview-{uid}.png'
            at = min(data['scenes'][0]['duration']+.2,max(data['scenes'][0]['visual'].get('revealAt', [0]) or [0])+0.6)
            render(['still', 'VisualForgeVideo', pending, f'--props={props}', f'--frame={int(at*30)}'], 'preview')
        else:
            name='story' if action=='story_preview' else 'style' if action=='style_preview' else f'motion-{uid}' if action=='motion' else 'draft' if profile=='draft' else 'video'
            pending, final = folder/f'{name}.pending.mp4', folder/f'{name}.mp4'
            if action in {'render','story_preview'}:
                from backend.services.scene_cache import render_cached
                render_cached(self,project,data,props,pending,profile,render)
            else:
                render(['render', 'VisualForgeVideo', pending, f'--props={props}', f'--concurrency={RENDER_CONCURRENCY}', *(['--scale=0.6666666666666666'] if profile=='draft' else [])], 'render')
            py('validate', 'validate_render.py', [pending, '--metadata', props, '--report', folder/f'{name}-validation.json', '--profile', profile])
        if action in {'render','motion'}:
            from backend.services.scene_cache import thumbnails
            thumbnails(self,project,data,pending,profile)
        pending.replace(final)
        artifact={'key': key, 'file': final.name, 'sha256': file_hash(final), 'profile':profile, 'styled':True}
        if action=='story_preview':artifact.update(start_uid=uid,scene_uids=[document['scenes'][s['id']-1]['uid'] for s in data['scenes']],seconds=sum(math.ceil((s['duration']+.5)*30)/30 for s in data['scenes']))
        kind='story_render' if action=='story_preview' else 'style_render' if action=='style_preview' else 'motion' if action=='motion' else 'preview' if action == 'preview' else 'draft_render' if profile=='draft' else 'render'
        self.store.update_artifact(project['id'], kind, artifact, uid)
        if kind in {'render','draft_render'} and self.publishing:
            from backend.services.publishing import publish_safely
            phase('thumbnail')
            publish_safely(self, project, folder, data, render, profile)

    def model_name(self):
        from backend.llm.gguf_llm import model_status
        return str(model_status().get('model', 'local model')).split('/')[-1][:60]

    def measure_explainers(self, rows, folder, py):
        """Measured data for explainers: next-token odds, tokenizations and embedding maps; cached, never fatal.

        Cached results are read without loading a model. A missing model or a failed run leaves
        next-token scenes and maps illustrative (labelled) and tokenization scenes on their normal visual.
        """
        from backend.services.explainers import plan as plan_explainer
        from backend.services import embeddings, next_token
        plans=[e for row in rows if not row['visual'].get('worked') and (e:=plan_explainer(row))]
        prompts=list(dict.fromkeys(e['prompt'] for e in plans if e['kind']=='next_token'))
        texts=list(dict.fromkeys(e['text'] for e in plans if e['kind']=='tokens'))
        maps=list(dict.fromkeys(tuple(p['label'] for p in e['points']) for e in plans if e['kind']=='embedding_map'))
        results={'next':{},'tokens':{},'maps':{}}
        model=None
        if prompts or texts:
            try:
                from backend.services.worked_examples import identity
                model=identity()
            except (OSError, ValueError, KeyError):
                prompts,texts=[],[]
        results['next']={p:r for p in prompts if (r:=next_token.read(p,model))}
        results['tokens']={t:r for t in texts if (r:=next_token.read_tokens(t,model))}
        results['maps']={m:r for m in maps if (r:=embeddings.read(m))}
        missing={'next':[p for p in prompts if p not in results['next']],'tokens':[t for t in texts if t not in results['tokens']],
                 'maps':[list(m) for m in maps if m not in results['maps'] and embeddings.installed()]}
        if any(missing.values()):
            src,out=folder/'explainer-measure-request.json',folder/'explainer-measure-results.json'
            write_json_atomic(src,missing)
            try:
                py('next-token','measure_next_token.py',[src,out])
                measured=json.loads(out.read_text(encoding='utf-8'))
                results['next'].update({p:next_token.validate(measured['next'][p],p,model) for p in missing['next'] if p in measured['next']})
                results['tokens'].update({t:next_token.validate_tokens(measured['tokens'][t],t,model) for t in missing['tokens'] if t in measured['tokens']})
                results['maps'].update({tuple(m):embeddings.validate(found,m) for m in missing['maps'] if (found:=measured.get('maps',{}).get('\n'.join(m)))})
            except (RuntimeError, OSError, ValueError, KeyError) as exc:
                self.state['message']=f'Model measurements were not made ({str(exc)[:160]}); those explainers stay illustrative or use the normal visual.'
        return results

    def voice(self, project_id):
        """Narration voice from the render style, so stand-in catalogues that only provide style() work."""
        from backend.tts.kokoro_tts import DEFAULT_VOICE
        return self.workspaces.style(project_id).get('voice', DEFAULT_VOICE)

    def remotion(self, folder, command, name):
        """Run one Remotion CLI command for a project, retrying once after a transient browser failure."""
        from backend.services.render_assets import with_public_dir
        command = with_public_dir(self.root, folder, command)
        bundle = self.bundle(folder, command)
        if bundle:
            # Rendering from a prepared bundle skips webpack and the public-dir copy on every call.
            command = [command[0], str(bundle), *[a for a in command[1:] if not str(a).startswith('--public-dir=')]]
        for attempt in range(2):
            try:
                return execute([node_executable(), self.root/'renderer/node_modules/@remotion/cli/remotion-cli.js', *command],
                               cwd=self.root/'renderer', log=folder/'logs'/f'{name}.log', cancel_event=self.cancel)
            except RuntimeError:
                if attempt:
                    raise

    def bundle(self, folder, command):
        """A renderer bundle for this job's narration, built once and reused by every segment and still.

        Keyed by renderer code and the exact public files, so a code or narration change rebuilds it.
        Any failure falls back to the normal per-command bundling rather than failing the render.
        """
        public = next((str(a).split('=', 1)[1] for a in command if str(a).startswith('--public-dir=')), None)
        if not command or command[0] not in {'render', 'still'} or not public:
            return None
        from backend.services.run_state import fingerprint
        files = sorted((p.relative_to(public).as_posix(), p.stat().st_size) for p in Path(public).rglob('*') if p.is_file())
        key = fingerprint(['render-bundle-v1', self.version, files])
        target = folder/'render-bundle'
        marker = target/'bundle-key.txt'
        try:
            if marker.is_file() and marker.read_text(encoding='utf-8') == key and (target/'index.html').is_file():
                return target
            pending = folder/'render-bundle.pending'
            shutil.rmtree(pending, ignore_errors=True)
            execute([node_executable(), self.root/'renderer/node_modules/@remotion/cli/remotion-cli.js', 'bundle', 'src/index.ts',
                     f'--public-dir={public}', f'--out-dir={pending}', '--log=error'],
                    cwd=self.root/'renderer', log=folder/'logs'/'bundle.log', cancel_event=self.cancel)
            if not (pending/'index.html').is_file():
                return None
            (pending/'bundle-key.txt').write_text(key, encoding='utf-8')
            shutil.rmtree(target, ignore_errors=True)
            pending.replace(target)
            return target
        except InterruptedError:
            raise
        except Exception:  # noqa: BLE001 - bundling is an optimisation; per-command bundling still works
            return None

    def close(self):
        self.cancel.set()
        if self.thread:
            self.thread.join(timeout=30)

    def artifact_ready(self, project, record, uid=None):
        if not record or record['key'] != (self.output_key(project, uid, record.get('profile','final')) if record.get('styled') else artifact_key(project['document'], self.version, uid)):
            return False
        return self.artifact_intact(project, record)

    def artifact_intact(self, project, record):
        if not record:
            return False
        folder = self.store.folder(project['id']).resolve()
        target = (folder / record['file']).resolve()
        return target.is_relative_to(folder) and target.is_file() and file_hash(target) == record['sha256']

    def present(self, project):
        result = copy.deepcopy(project)
        from backend.services.creator_workflow import accepted
        result['accepted'] = accepted(self.store, project)
        result['workspace']=self.workspaces.for_project(project['id'])
        result['review_style']=self.workspaces.style(project['id'])
        last=self.store.folder(project['id'])/'last-job.json'
        result['last_job']=json.loads(last.read_text(encoding='utf-8')) if last.exists() else {'status':'idle'}
        if self.busy() and self.state.get('project')==project['id']:
            result['last_job']={'status':'running'}
        if 'long_video' in project:
            from backend.services.long_video import present
            result=present(self, project, result)
            from backend.services.publishing import present as publish_present
            result=publish_present(self, project, result)
            from backend.services.episode_review import review, candidate
            result['episode_review']=review(result)
            pending=candidate(self,project)
            result['visual_candidate']={'uid':pending['uid'],'url':f"/media/{project['id']}/candidate?v={pending['sha256']}"} if pending else None
            return result
        if not project['document']:
            return result
        from backend.services.visual_storytelling import plan_document as visual_plan
        result['visual_plan'] = visual_plan(project['document'])
        result['quality'] = quality(project['document'])
        from backend.services.teaching_plan import plan_document
        result['teaching_plan'] = plan_document(project['document'])
        from backend.services.code_examples import select_spec
        result['demonstration_specs'] = {s['uid']:select_spec({**s,'topic':project['document']['topic']}) for s in project['document']['scenes']}
        result['worked_examples'] = summaries(project['document'])
        from backend.services.run_state import fingerprint
        result['review_required'] = bool(project.get('source',{}).get('review_first'))
        result['storyboard_approved'] = project.get('storyboard_approved') == fingerprint(project['document'])
        result['motion_urls'] = {}
        result['audio'] = {}
        result['preview_urls'] = {}
        voice = self.voice(project['id'])
        for scene in project['document']['scenes']:
            uid = scene['uid']
            cached = cached_speech(self.root/'renderer/public', scene['narration'], voice, directed=bool(project.get('directed') or any(s['visual'].get('worked') for s in project['document']['scenes'])))
            if cached:
                result['audio'][uid] = {'url': f"/media/{project['id']}/audio/{uid}?v={file_hash(cached[0])[:12]}", 'duration': cached[1]}
            record = project['previews'].get(uid)
            if self.artifact_ready(project, record, uid):
                result['preview_urls'][uid] = f"/media/{project['id']}/preview/{uid}?v={record['key']}"
            clip = project.get('motion_previews',{}).get(uid)
            if self.artifact_ready(project,clip,uid):
                result['motion_urls'][uid] = f"/media/{project['id']}/motion/{uid}?v={clip['key']}"
        sample=project.get('style_render')
        result['style_url']=f"/media/{project['id']}/style?v={sample['key']}" if self.artifact_ready(project,sample) else None
        story=project.get('story_render')
        result['story_preview']={'url':f"/media/{project['id']}/story?v={story['key']}",'start_uid':story['start_uid'],'scene_uids':story['scene_uids'],'seconds':story['seconds']} if story and story['key']==self.story_key(project,story['start_uid']) and self.artifact_intact(project,story) else None
        record = project.get('render')
        result['video_url'] = None
        if self.artifact_ready(project, record):
            result['video_url'] = f"/media/{project['id']}/video?v={record['key']}"
        record=project.get('draft_render')
        result['draft_url']=f"/media/{project['id']}/draft?v={record['key']}" if self.artifact_ready(project,record) else None
        result['previous_export_url'] = None
        if not result['video_url'] and not result['draft_url']:
            for kind, old in [('video',project.get('render')), ('draft',project.get('draft_render'))]:
                if self.artifact_intact(project,old):
                    result['previous_export_url'] = f"/media/{project['id']}/{kind}?previous=1&v={old['key']}"
                    break
        from backend.services.publishing import present as publish_present
        result=publish_present(self, project, result)
        target=project.get('source',{}).get('minutes',0)*60 if project.get('source',{}).get('mode')=='prompt' else None
        result['duration']=duration_report(project['document'],result['audio'],target)
        style=self.workspaces.style(project['id'])
        plans=result['visual_plan']['scenes']
        intro=(plans[0].get('choreography') or {}).get('layout')=='intro'
        outro=(plans[-1].get('choreography') or {}).get('layout')=='outro'
        bookends=(3 if style.get('showIntro') and not intro else 0)+(5 if style.get('showOutro') and not outro else 0)
        result['duration']['bookend_seconds']=bookends
        for field in ('estimated_seconds','measured_seconds'):
            if result['duration'][field] is not None:result['duration'][field]+=bookends
        actual=result['duration']['measured_seconds'] or result['duration']['estimated_seconds']
        result['duration']['outside_target']=bool(target and abs(actual-target)>max(5,target*.15))
        if result['duration']['outside_target']:
            d=result['duration'];actual=d['measured_seconds'] if d['measured_seconds'] is not None else d['estimated_seconds']
            result['quality']['issues'].append({'scene':0,'code':'duration_target','severity':'warning','message':f'Runtime is approximately {actual:.0f}s for a {target:.0f}s target. Review narration length before final export.'})
            result['quality']['status']='needs_review'
        from backend.services.episode_review import review, candidate
        result['episode_review']=review(result)
        pending=candidate(self,project)
        result['visual_candidate']={'uid':pending['uid'],'url':f"/media/{project['id']}/candidate?v={pending['sha256']}"} if pending else None
        return result
