"""Local-only review editor. No accounts, database, hosted services or web framework."""
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import secrets
import socket
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.llm.prompts import normalize_topic
from backend.schemas.video_schema import VideoScript, words
from backend.services.editor_store import EditorStore, document_from_video, quality
from backend.services.editor_jobs import EditorJobs
from backend.services.incremental_audio import cached_speech
from backend.services.director import script_to_video, build_direction


class LocalHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR permits two listeners to share a port unexpectedly.
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(port=8765, root=ROOT, directory=None):
    store = EditorStore(directory or root/'data/editor')
    jobs = EditorJobs(root, store)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def allowed(self):
            hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            origin = self.headers.get('Origin')
            return self.headers.get('Host') in hosts and (not origin or origin in {'http://'+h for h in hosts})

        def common_headers(self, code, mime, size):
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(size))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")

        def json_response(self, data, code=200):
            raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.common_headers(code, 'application/json; charset=utf-8', len(raw))
            self.end_headers()
            self.wfile.write(raw)

        def file_response(self, path):
            size = path.stat().st_size
            start, end, code = 0, size-1, 200
            byte_range = self.headers.get('Range')
            if byte_range:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', byte_range)
                if not match or not any(match.groups()):
                    return self.json_response({'error': 'Invalid byte range'}, 416)
                if match[1]:
                    start = int(match[1])
                    end = min(int(match[2]), end) if match[2] else end
                else:
                    start = max(0, size-int(match[2]))
                if start > end or start >= size:
                    return self.json_response({'error': 'Range outside file'}, 416)
                code = 206
            self.common_headers(code, mimetypes.guess_type(path.name)[0] or 'application/octet-stream', end-start+1)
            self.send_header('Accept-Ranges', 'bytes')
            if code == 206:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            with path.open('rb') as stream:
                stream.seek(start)
                remaining = end-start+1
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def do_GET(self):
            if not self.allowed():
                return self.json_response({'error': 'Local origin required'}, 403)
            path = urlsplit(self.path).path
            try:
                if path in {'/', '/app.js', '/storyboard.js', '/style.css', '/creator.js', '/creator.css', '/progress.js', '/episode-review.js'}:
                    return self.file_response(root/'review' / ('index.html' if path=='/' else path[1:]))
                if path == '/api/config':
                    from backend.llm.gguf_llm import model_status
                    return self.json_response({'token': token, 'model': model_status()})
                chapter_media = re.fullmatch(r'/media/([a-f0-9]{12})/chapter/([a-f0-9]{12})/(draft|style)', path)
                if chapter_media:
                    from backend.services.long_video import nested_jobs
                    parent = store.load(chapter_media[1])
                    jobs.workspaces.require_active(parent['id'])
                    if chapter_media[2] not in {c['id'] for c in parent.get('long_video', {}).get('chapters', [])}:
                        raise FileNotFoundError('Chapter not found')
                    nested = nested_jobs(jobs, parent)
                    child = nested.store.load(chapter_media[2])
                    kind='style_render' if chapter_media[3]=='style' else 'draft_render'
                    if not nested.artifact_ready(child, child.get(kind)):
                        raise FileNotFoundError('Chapter preview is not current')
                    return self.file_response(nested.store.folder(child['id']) / child[kind]['file'])
                if path == '/api/projects':
                    return self.json_response(store.list())
                if path == '/api/workspaces':
                    catalog=jobs.workspaces.list()
                    projects={p['id']:p for p in store.list()}
                    for w in catalog:
                        w['videos']=[]
                        for pid in w['episodes']:
                            if pid not in projects: continue
                            p=store.load(pid)
                            status='Draft'
                            if jobs.busy() and jobs.state.get('project')==pid: status='Generating'
                            elif 'long_video' in p:
                                if jobs.artifact_ready(p, p.get('render')): status='Ready'
                                elif jobs.artifact_ready(p, p.get('draft_render')): status='Draft ready'
                                else: status='Chapter review'
                            elif not p['document'] and jobs.present(p)['last_job'].get('status')=='failed': status='Generation failed'
                            elif p['document']:
                                if any(i for i in quality(p['document'])['issues']): status='Needs review'
                                elif jobs.artifact_ready(p,p.get('render')): status='Ready'
                                elif jobs.artifact_ready(p,p.get('draft_render')): status='Draft ready'
                            w['videos'].append({**projects[pid],'status':status})
                    return self.json_response(catalog)
                if path == '/api/job':
                    return self.json_response(jobs.status())
                if path == '/api/runs':
                    runs = [{'id': 'demo', 'title': 'Current validated script'}] if (root/'data/video.json').is_file() else []
                    for source in (root/'data/runs').glob('*/video.json'):
                        try:
                            video = VideoScript.model_validate_json(source.read_text(encoding='utf-8'))
                            runs.append({'id': source.parent.name, 'title': video.title+' - '+source.parent.name[-10:]})
                        except (ValueError, OSError):
                            continue
                    return self.json_response(runs)
                match = re.fullmatch(r'/api/projects/([a-f0-9]{12})', path)
                if match:
                    return self.json_response(jobs.present(store.load(match[1])))
                chapter_motion = re.fullmatch(r'/media/([a-f0-9]{12})/chapter/([a-f0-9]{12})/(motion|preview)/([a-f0-9]{12})', path)
                if chapter_motion:
                    from backend.services.long_video import nested_jobs
                    parent=store.load(chapter_motion[1]); jobs.workspaces.require_active(parent['id'])
                    if chapter_motion[2] not in {c['id'] for c in parent.get('long_video',{}).get('chapters',[])}:
                        raise FileNotFoundError('Unknown chapter')
                    nested=nested_jobs(jobs,parent); child=nested.store.load(chapter_motion[2])
                    record=child.get('motion_previews' if chapter_motion[3]=='motion' else 'previews',{}).get(chapter_motion[4])
                    if not nested.artifact_ready(child,record,chapter_motion[4]):
                        raise FileNotFoundError('Scene preview is not current')
                    return self.file_response(nested.store.folder(child['id'])/record['file'])
                proposal=re.fullmatch(r'/media/([a-f0-9]{12})/candidate',path)
                if proposal:
                    from backend.services.episode_review import candidate
                    project=store.load(proposal[1]);jobs.workspaces.require_active(project['id'])
                    pending=candidate(jobs,project)
                    if not pending:raise FileNotFoundError('Candidate is stale or missing')
                    return self.file_response(store.folder(project['id'])/pending['file'])
                story_media=re.fullmatch(r'/media/([a-f0-9]{12})/story',path)
                if story_media:
                    project=store.load(story_media[1]);jobs.workspaces.require_active(project['id'])
                    record=project.get('story_render')
                    if not record or record['key']!=jobs.story_key(project,record['start_uid']) or not jobs.artifact_intact(project,record):
                        raise FileNotFoundError('Story preview is stale or missing')
                    return self.file_response(store.folder(project['id'])/record['file'])
                match = re.fullmatch(r'/media/([a-f0-9]{12})/(audio|preview|motion|video|draft|style)(?:/([a-f0-9]{12}))?', path)
                if match:
                    project = store.load(match[1])
                    jobs.workspaces.require_active(project['id'])
                    ready = jobs.present(project)
                    if match[2] == 'audio':
                        scene = next(s for s in project['document']['scenes'] if s['uid']==match[3])
                        cached = cached_speech(root/'renderer/public', scene['narration'], directed=project.get('directed', False))
                        if not cached:
                            raise FileNotFoundError('Audio needs regeneration')
                        return self.file_response(cached[0])
                    if match[2] == 'motion':
                        if match[3] not in ready['motion_urls']:
                            raise FileNotFoundError('Scene animation needs regeneration')
                        record = project['motion_previews'][match[3]]
                    elif match[2] == 'preview':
                        if match[3] not in ready['preview_urls']:
                            raise FileNotFoundError('Preview needs regeneration')
                        record = project['previews'][match[3]]
                    else:
                        record = project['style_render' if match[2]=='style' else 'draft_render' if match[2]=='draft' else 'render']
                        previous = match[2] in {'video','draft'} and 'previous=1' in urlsplit(self.path).query.split('&')
                        if previous:
                            if not jobs.artifact_intact(project,record):
                                raise FileNotFoundError('Previous export is unavailable')
                        elif not ready['style_url' if match[2]=='style' else 'draft_url' if match[2]=='draft' else 'video_url']:
                            raise FileNotFoundError('Video needs rendering')
                    folder = store.folder(project['id']).resolve()
                    file = (folder/record['file']).resolve()
                    if not file.is_relative_to(folder):
                        raise ValueError('Invalid media path')
                    return self.file_response(file)
                return self.json_response({'error': 'Not found'}, 404)
            except (FileNotFoundError, StopIteration):
                self.json_response({'error': 'Not found or not generated yet'}, 404)
            except (ValueError, KeyError, TypeError) as exc:
                self.json_response({'error': str(exc)}, 400)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            supplied = self.headers.get('X-Editor-Token', '')
            # An open same-origin browser tab can retain unsaved edits across a
            # server restart. Fetch Metadata + the exact Origin allow token rollover;
            # cross-origin callers and non-browser clients still require the token.
            same_origin_tab = bool(supplied) and self.headers.get('Sec-Fetch-Site') == 'same-origin' and self.headers.get('Origin') == 'http://'+self.headers.get('Host', '')
            if not self.allowed() or not (secrets.compare_digest(supplied, token) or same_origin_tab):
                return self.json_response({'error': 'Local editor token required'}, 403)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2000000 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('Send a JSON object under 2 MB')
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError('Expected a JSON object')
                path = urlsplit(self.path).path
                if path == '/api/cancel':
                    jobs.cancel.set()
                    return self.json_response({'status': 'cancelling'})
                with store.lock:
                    if jobs.busy():
                        return self.json_response({'error': 'A task is running. Wait or cancel before changing a project.'}, 409)
                    if path=='/api/workspaces':
                        return self.json_response(jobs.workspaces.create(body),201)
                    workspace_match=re.fullmatch(r'/api/workspaces/([a-f0-9]{12})/(save|trash|restore|duplicate|reorder|delete)',path)
                    if workspace_match and workspace_match[2] == 'delete':
                        if body.get('confirmation') != 'DELETE': raise ValueError('Type DELETE to permanently remove this workspace and all its videos.')
                        workspace = jobs.workspaces.get(workspace_match[1], active=False)
                        from backend.services.creator_workflow import delete_projects
                        delete_projects(store, jobs.workspaces, workspace['episodes'])
                        from backend.services.script_generator import write_json_atomic
                        write_json_atomic(jobs.workspaces.path, [w for w in jobs.workspaces.read() if w['id'] != workspace['id']])
                        return self.json_response({'deleted':workspace['id']})
                    if workspace_match:
                        return self.json_response(jobs.workspaces.change(workspace_match[1],workspace_match[2],body))
                    if path == '/api/projects':
                        workspace_id=body.get('workspace_id')
                        if workspace_id:
                            workspace=jobs.workspaces.get(workspace_id)
                            if workspace['kind']=='single' and workspace['episodes']:
                                raise ValueError('This workspace already has a video. Create another workspace or use a series.')
                        if 'mode' in body:
                            mode = body['mode']
                            text = body.get('text') or ''
                            # If text is a file path (quoted or plain), load its content automatically
                            cleaned_path = text.strip(' "\'\t\r\n')
                            if '\n' not in cleaned_path and len(cleaned_path) < 500:
                                try:
                                    path_obj = Path(cleaned_path)
                                    if path_obj.is_file():
                                        text = path_obj.read_text(encoding='utf-8', errors='replace')
                                except Exception:
                                    pass
                            if mode == 'long':
                                from backend.services.long_video import initialize
                                project = initialize(store, normalize_topic(text), body.get('minutes'))
                                if workspace_id:
                                    jobs.workspaces.attach(workspace_id, project['id'])
                                jobs.start(project['id'], 'long_outline')
                                return self.json_response(jobs.present(project), 201)
                            if mode not in {'prompt', 'script'}:
                                raise ValueError('Choose prompt or script input')
                            profile=body.get('profile','final')
                            if profile not in {'draft','final'}: raise ValueError('Unknown render profile')
                            automatic=body.get('automatic',False)
                            if type(automatic) is not bool:raise ValueError('Invalid automatic generation setting')
                            reviewed = body.get('approval_required', False)
                            if type(reviewed) is not bool: raise ValueError('Invalid review setting')
                            minutes = 2 if automatic else body.get('minutes', 1)
                            if mode == 'script':
                                title = normalize_topic(body['title']) if body.get('title') else None
                                from backend.services.script_projects import create as create_script
                                project = create_script(store, title, text, {'mode':mode,'text':text,'profile':profile,
                                    'review_first':reviewed or not bool(body.get('render_now') or automatic),
                                    'automatic':automatic,'approval_required':reviewed})
                                if 'long_video' in project and not automatic:
                                    project['source']['automatic']=True
                                    from backend.services.script_generator import write_json_atomic
                                    write_json_atomic(store.folder(project['id'])/'project.json',project)
                                if workspace_id: jobs.workspaces.attach(workspace_id,project['id'])
                                jobs.start(project['id'], 'auto_generate' if automatic or 'long_video' in project else 'generate')
                                return self.json_response(jobs.present(project),201)
                            else:
                                if type(minutes) not in (int, float) or not 0.5 <= minutes <= 30:
                                    raise ValueError('Choose a supported prompt draft target between 0.5 and 30 minutes')
                                topic = normalize_topic(text)
                                document = None
                            render_now = (automatic or bool(body.get('render_now'))) and not reviewed
                            project = store.create(topic, document, source={'mode':mode, 'text':text, 'minutes':minutes,'profile':profile,'review_first': not render_now,'automatic':automatic,'approval_required':reviewed,'minimum_seconds':0})
                            if render_now and document:
                                store.approve_storyboard(project['id'], project['revision'])
                                project = store.load(project['id'])
                            if workspace_id: jobs.workspaces.attach(workspace_id,project['id'])
                            jobs.start(project['id'], 'auto_generate' if automatic else 'generate')
                            return self.json_response(jobs.present(project), 201)
                        topic = normalize_topic(body.get('topic'))
                        project = store.create(topic)
                        jobs.start(project['id'], 'draft')
                        return self.json_response(project, 201)
                    if path == '/api/import':
                        run_id = body.get('run')
                        if not isinstance(run_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', run_id):
                            raise ValueError('Invalid run ID')
                        folder = root/'data' if run_id == 'demo' else root/'data/runs'/run_id
                        video = VideoScript.model_validate_json((folder/'video.json').read_text(encoding='utf-8'))
                        plan = json.loads((folder/'visuals.json').read_text(encoding='utf-8')) if (folder/'visuals.json').is_file() else None
                        project = store.create(video.topic, document_from_video(video, plan))
                        return self.json_response(jobs.present(project), 201)
                    match = re.fullmatch(r'/api/projects/([a-f0-9]{12})/(save|task|long-save|approve|accept|delete|reopen|accept-visual|discard-visual|shot)', path)
                    if match:
                        current = store.load(match[1])
                        jobs.workspaces.require_active(match[1])
                        if body.get('revision') != current['revision']:
                            return self.json_response({'error': 'Project changed. Reload before continuing.'}, 409)
                        if match[2] in {'accept-visual','discard-visual'}:
                            from backend.services.episode_review import decide
                            return self.json_response(jobs.present(decide(jobs,current,match[2]=='accept-visual')))
                        if match[2]=='shot':
                            from backend.services.shot_direction import set_override
                            return self.json_response(jobs.present(set_override(jobs,current,body.get('uid'),body.get('sentence'),body.get('mode'))))
                        if match[2] == 'delete':
                            if body.get('confirmation') != 'DELETE': raise ValueError('Type DELETE to permanently remove this video and its project data.')
                            from backend.services.creator_workflow import delete_projects
                            delete_projects(store, jobs.workspaces, [current['id']])
                            return self.json_response({'deleted':current['id']})
                        if match[2] == 'reopen':
                            current.pop('accepted_export',None)
                            current['revision']+=1
                            from backend.services.script_generator import write_json_atomic
                            write_json_atomic(store.folder(current['id'])/'project.json',current)
                            return self.json_response(jobs.present(current))
                        if match[2] == 'accept':
                            from backend.services.creator_workflow import accept
                            return self.json_response(jobs.present(accept(jobs, current)))
                        if match[2] == 'approve':
                            if 'long_video' in current:
                                raise ValueError('Approve the chapter storyboard through chapter review.')
                            return self.json_response(jobs.present(store.approve_storyboard(match[1],body['revision'])))
                        if match[2] == 'long-save':
                            from backend.services.long_video import save
                            if 'long_video' not in current:
                                raise ValueError('This is not a chapter project.')
                            return self.json_response(jobs.present(save(store, current, body)))
                        if match[2] == 'save':
                            return self.json_response(jobs.present(store.save(match[1], body['revision'], body['document'])))
                        instructions = body.get('instructions', 'Make the explanation concrete and concise. Avoid hype.')
                        if not isinstance(instructions, str) or len(instructions)>1000:
                            raise ValueError('Instructions must be at most 1000 characters')
                        return self.json_response(jobs.start(match[1], body.get('action'), body.get('uid'), instructions), 202)
                    return self.json_response({'error': 'Not found'}, 404)
            except FileNotFoundError:
                self.json_response({'error': 'Project or run not found'}, 404)
            except (ValueError, KeyError, TypeError) as exc:
                self.json_response({'error': str(exc)}, 400)

    server = LocalHTTPServer(('127.0.0.1', port), Handler)
    server.editor_jobs = jobs
    server.editor_store = store
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f'VisualForge review editor: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.editor_jobs.close()
        server.server_close()
