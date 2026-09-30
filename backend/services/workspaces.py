"""Atomic workspace catalog. Trash hides references; project files remain intact."""
import copy
import json
import re
import uuid
from backend.services.script_generator import write_json_atomic
from backend.tts.kokoro_tts import DEFAULT_VOICE, RECOMMENDED_VOICE, VOICES

THEMES = {'ocean', 'forest', 'sunset'}
GENERATIVE_AI_TOPICS = ['What is Generative AI?', 'How Large Language Models Work',
    'Tokens and Context Windows', 'Embeddings', 'Vector Databases', 'RAG',
    'Prompt Engineering', 'Fine-Tuning', 'Tool Calling', 'AI Agents', 'MCP',
    'Multimodal AI', 'Guardrails and AI Safety', 'Build a RAG Application', 'Build an AI Agent']


def next_topic(workspace, project_topics=()):
    topics = workspace.get('topics', [])
    known = [t.casefold().strip() for t in topics]
    current = workspace.get('current_topic', '').casefold().strip()
    index = known.index(current) if current in known else -1
    for topic in project_topics:
        if topic.casefold().strip() in known:
            index = max(index, known.index(topic.casefold().strip()))
    return topics[index + 1] if index + 1 < len(topics) else None


class Workspaces:
    def __init__(self, store):
        self.store = store
        self.path = store.directory / 'workspaces.json'

    def read(self):
        catalog = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else []
        assigned = {p for w in catalog for p in w['episodes']}
        # Adopt old projects without touching their documents, revisions or outputs.
        # They keep the original voice so their recorded narration stays valid.
        for p in self.store.list():
            if p['id'] not in assigned:
                catalog.append(self.new(p['title'], 'single', [p['id']]) | {'voice': DEFAULT_VOICE})
        return catalog

    @staticmethod
    def new(name, kind, episodes=None):
        return dict(id=uuid.uuid4().hex[:12], name=name, kind=kind, episodes=episodes or [],
                    theme='ocean', audience='beginners', brand='VISUALFORGE / LEARN', voice=RECOMMENDED_VOICE, deleted=False,
                    show_intro=True, show_outro=True,
                    topics=list(GENERATIVE_AI_TOPICS) if name.casefold().strip() == 'generative ai visualized' and kind == 'series' else [], current_topic='')

    def list(self):
        with self.store.lock:
            catalog = self.read()
            write_json_atomic(self.path, catalog)
            result = copy.deepcopy(catalog)
            for w in result:
                from backend.services.creator_workflow import accepted
                projects = [self.store.load(pid) for pid in w['episodes']]
                pending = [p for p in projects if not accepted(self.store, p)]
                w['active_project'] = pending[-1]['id'] if pending else None
                w['next_topic'] = next_topic(w, [p['topic'] for p in projects if accepted(self.store,p)]) if w['kind'] == 'series' and not pending else None
            return result

    def get(self, workspace_id, active=True):
        if not isinstance(workspace_id, str) or not re.fullmatch('[a-f0-9]{12}', workspace_id):
            raise ValueError('Invalid workspace ID')
        workspace = next((w for w in self.list() if w['id'] == workspace_id), None)
        if workspace is None or active and workspace['deleted']:
            raise ValueError('Workspace is unavailable')
        return workspace

    def for_project(self, project_id):
        return next((w for w in self.list() if project_id in w['episodes']), None)

    def require_active(self, project_id):
        w = self.for_project(project_id)
        if w and w['deleted']:
            raise ValueError('Restore this workspace from Trash first')
        return w

    @staticmethod
    def validate(w):
        topics = w.get('topics', [])
        if not isinstance(topics, list) or len(topics) > 100 or any(not isinstance(t, str) or not t.strip() or len(t) > 160 or any(ord(c) < 32 for c in t) for t in topics):
            raise ValueError('Use up to 100 topic titles, each on one line (160 characters maximum).')
        w['topics'] = [t.strip() for t in topics]
        if len(set(t.casefold() for t in w['topics'])) != len(topics):
            raise ValueError('Playlist topics must be unique.')
        if w.get('current_topic', '') and w['current_topic'] not in w['topics']:
            raise ValueError('Choose a current topic from the playlist sequence.')
        for key, limit in [('name',120), ('audience',160), ('brand',48)]:
            value = w.get(key)
            if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 for c in value):
                raise ValueError(f'{key} must be a single line of 1–{limit} characters')
            w[key] = value.strip()
        if w['kind'] not in {'single','series'} or w['theme'] not in THEMES or w.get('voice', DEFAULT_VOICE) not in VOICES:
            raise ValueError('Unsupported workspace settings')
        if w['kind']=='single' and len(w['episodes'])>1:
            raise ValueError('A single-video workspace can contain only one video')
        for key in ('show_intro', 'show_outro'):
            if key in w and not isinstance(w[key], bool):
                raise ValueError(f'{key} must be true or false')

    def create(self, body):
        with self.store.lock:
            catalog=self.read()
            w=self.new(body.get('name',''), body.get('kind','single'))
            for key in ('theme','audience','brand','voice','show_intro','show_outro','topics','current_topic'):
                if key in body: w[key]=body[key]
            self.validate(w)
            catalog.append(w)
            write_json_atomic(self.path,catalog)
            return w

    def home(self, workspace_id, project_id, name):
        """Put a new project in its workspace; without one, give it a fresh single-video workspace
        so it gets current defaults (natural voice, intro and outro) rather than legacy adoption."""
        if not workspace_id:
            workspace_id = self.create({'name': (name or 'New video').strip()[:120] or 'New video', 'kind': 'single'})['id']
        self.attach(workspace_id, project_id)

    def attach(self, workspace_id, project_id):
        with self.store.lock:
            catalog=self.read()
            w=next(x for x in catalog if x['id']==workspace_id)
            if w['deleted'] or w['kind']=='single' and w['episodes']:
                raise ValueError('Choose an empty single-video workspace or a series')
            # read() may have adopted the freshly created project into a single.
            catalog=[x for x in catalog if x['id']==workspace_id or x['episodes']!=[project_id]]
            w['episodes'].append(project_id)
            write_json_atomic(self.path,catalog)

    def change(self, workspace_id, action, body):
        with self.store.lock:
            catalog=self.read()
            w=next((x for x in catalog if x['id']==workspace_id),None)
            if w is None: raise ValueError('Workspace not found')
            if action=='restore': w['deleted']=False
            elif action=='trash': w['deleted']=True
            elif w['deleted']: raise ValueError('Restore this workspace first')
            elif action=='save':
                old_style = {key:w.get(key) for key in ('theme','brand','voice','show_intro','show_outro')}
                for key in ('name','kind','theme','audience','brand','voice','show_intro','show_outro','topics','current_topic'):
                    if key in body: w[key]=body[key]
                self.validate(w)
                if old_style != {key:w.get(key) for key in old_style}:
                    for pid in w['episodes']:
                        project=self.store.load(pid)
                        if project.pop('accepted_export',None):
                            project['revision']+=1
                            write_json_atomic(self.store.folder(pid)/'project.json',project)
            elif action=='reorder':
                order=body.get('episodes')
                if not isinstance(order,list) or len(order)!=len(w['episodes']) or sorted(order)!=sorted(w['episodes']):
                    raise ValueError('Episode order must contain every existing episode exactly once')
                w['episodes']=order
            elif action=='duplicate':
                duplicate=self.new(w['name'][:110]+' (copy)',w['kind'])
                for key in ('theme','audience','brand','show_intro','show_outro'): duplicate[key]=w.get(key,False)
                duplicate['voice']=w.get('voice',DEFAULT_VOICE)
                for project_id in w['episodes']:
                    p=self.store.load(project_id)
                    copied=self.store.create(p['topic'],copy.deepcopy(p['document']),source=copy.deepcopy(p.get('source')))
                    if 'long_video' in p:
                        from backend.services.long_video import chapters_store
                        original_children = chapters_store(self.store, p)
                        copied_children = chapters_store(self.store, copied)
                        copied['long_video'] = {'chapters': [], 'outline_approved': None, 'script_approved': None}
                        for chapter in p['long_video']['chapters']:
                            child = original_children.load(chapter['id'])
                            new_child = copied_children.create(child['topic'], copy.deepcopy(child['document']), source=copy.deepcopy(child.get('source')))
                            copied['long_video']['chapters'].append({**chapter, 'id': new_child['id']})
                        write_json_atomic(self.store.folder(copied['id']) / 'project.json', copied)
                    duplicate['episodes'].append(copied['id'])
                catalog.append(duplicate)
                w=duplicate
            else: raise ValueError('Unknown workspace action')
            write_json_atomic(self.path,catalog)
            return w

    def style(self, project_id):
        """Render style. The voice is included so a voice change invalidates every export key."""
        w = self.for_project(project_id)
        if w:
            style = {key: w[key] for key in ('theme', 'brand') if key in w} | \
                    {'showIntro':w.get('show_intro',False),'showOutro':w.get('show_outro',False),'voice':w.get('voice',DEFAULT_VOICE)}
            # A series outro can point viewers to the next lesson in the playlist sequence.
            if w['kind'] == 'series' and project_id in w['episodes']:
                through = w['episodes'][:w['episodes'].index(project_id)+1]
                upcoming = next_topic(w, [self.store.load(pid)['topic'] for pid in through])
                if upcoming:
                    style['nextTopic'] = upcoming
            return style
        return {'theme': 'ocean', 'brand': 'VISUALFORGE / LEARN', 'showIntro': False, 'showOutro': False, 'voice': DEFAULT_VOICE}

    def voice(self, project_id):
        return self.style(project_id).get('voice', DEFAULT_VOICE)
