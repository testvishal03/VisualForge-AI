import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from backend.tests.test_pipeline import fake_speech
from backend.tests.test_script_generation import valid_script, FakeLLM
from backend.schemas.video_schema import VideoScript
from backend.services.incremental_audio import generate_incremental, cached_speech
from backend.services.editor_store import EditorStore, document_from_video, validate_document, artifact_key
from backend.scripts.regenerate_scene import regenerate
from backend.scripts.review_app import make_server
from backend.services.run_state import file_hash


class IncrementalAudioTests(unittest.TestCase):
    def test_edit_one_narration_regenerates_only_one_and_reorder_reuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source.json'; output=root/'generated.json'
            data=valid_script(); source.write_text(json.dumps(data))
            calls=[]
            def synth(text,path,voice):
                calls.append(text); fake_speech(text,path,voice)
            first=generate_incremental(source,output,root/'public',synthesizer=synth)
            paths={s['narration']:s['audio'] for s in first['scenes']}
            self.assertEqual(len(calls),3)
            data['scenes'].reverse()
            for i,s in enumerate(data['scenes'],1): s['id']=i
            data['scenes'][0]['headline']='Revised visual title'
            source.write_text(json.dumps(data))
            second=generate_incremental(source,output,root/'public',synthesizer=synth)
            self.assertEqual(len(calls),3)
            self.assertEqual(second['cache']['generated_scene_ids'],[])
            for s in second['scenes']: self.assertEqual(s['audio'],paths[s['narration']])
            data['scenes'][1]['narration']+=' Readers can ask staff for help.'
            source.write_text(json.dumps(data))
            third=generate_incremental(source,output,root/'public',synthesizer=synth)
            self.assertEqual(len(calls),4)
            self.assertEqual(third['cache']['generated_scene_ids'],[2])
            self.assertEqual(third['cache']['reused_scene_ids'],[1,3])

    def test_corrupt_audio_regenerated_and_failed_batch_keeps_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source.json'; output=root/'generated.json'
            data=valid_script(); source.write_text(json.dumps(data))
            first=generate_incremental(source,output,root/'public',synthesizer=fake_speech)
            wav=root/'public'/first['scenes'][1]['audio']; wav.write_bytes(b'corrupt')
            before=output.read_bytes()
            with self.assertRaises(RuntimeError):
                generate_incremental(source,output,root/'public',synthesizer=lambda *args: (_ for _ in ()).throw(RuntimeError('TTS failed')))
            self.assertEqual(output.read_bytes(),before)
            repaired=generate_incremental(source,output,root/'public',synthesizer=fake_speech)
            self.assertEqual(repaired['cache']['generated_scene_ids'],[2])


class EditorStoreTests(unittest.TestCase):
    def test_optimistic_save_and_stable_scene_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            store=EditorStore(Path(directory)); video=VideoScript.model_validate(valid_script())
            doc=document_from_video(video); project=store.create(video.topic,doc)
            before_uids=[s['uid'] for s in doc['scenes']]
            doc['scenes'].reverse()
            saved=store.save(project['id'],1,doc)
            self.assertEqual(saved['revision'],2)
            self.assertEqual([s['uid'] for s in saved['document']['scenes']],before_uids[::-1])
            self.assertEqual([s.id for s in validate_document(saved['document']).scenes],[1,2,3])
            with self.assertRaisesRegex(ValueError,'another window'): store.save(project['id'],1,doc)

    def test_layout_validation_and_traversal(self):
        doc=document_from_video(VideoScript.model_validate(valid_script()))
        doc['scenes'][0]['visual']={'kind':'process','items':['One','Two','']}
        with self.assertRaises(ValueError): validate_document(doc)
        with self.assertRaises(ValueError): EditorStore(Path('.')).folder('../secret')
        doc['scenes'][0]['visual']={'kind':'takeaway','items':[]}
        doc['scenes'][1]['uid']=doc['scenes'][0]['uid']
        with self.assertRaises(ValueError): validate_document(doc)

    def test_preview_invalidation_is_scene_specific(self):
        doc=document_from_video(VideoScript.model_validate(valid_script()))
        one,two=[s['uid'] for s in doc['scenes'][:2]]
        key1,key2=artifact_key(doc,'renderer',one),artifact_key(doc,'renderer',two)
        doc['scenes'][0]['visual']['kind']='example'
        self.assertNotEqual(artifact_key(doc,'renderer',one),key1)
        self.assertEqual(artifact_key(doc,'renderer',two),key2)
        self.assertNotEqual(artifact_key(doc,'new-renderer',two),key2)
        doc['scenes'].reverse()
        self.assertNotEqual(artifact_key(doc,'renderer',one),key1)

    def test_single_scene_regeneration_preserves_siblings_and_failure_preserves_original(self):
        video=VideoScript.model_validate(valid_script()); before=video.model_dump()
        draft={'body':'A catalog helps visitors locate books by subject.',
               'narration':'A visitor can search the catalog for a book about gardening. The catalog shows its shelf location, helping the visitor find the right section.'}
        result=regenerate(video,1,'Use a gardening example',FakeLLM([{'body':draft['body']},{'narration':draft['narration']}]))
        self.assertEqual(result.id,1)
        self.assertEqual(result.headline,video.scenes[0].headline)
        self.assertEqual(video.model_dump(),before)
        with self.assertRaises(ValueError): regenerate(video,1,'Improve',FakeLLM(['bad']*3))
        self.assertEqual(video.model_dump(),before)


class EditorHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        (self.root/'renderer/src').mkdir(parents=True)
        (self.root/'renderer/remotion.config.ts').write_text('// fixture')
        (self.root/'data').mkdir()
        (self.root/'data/video.json').write_text(json.dumps(valid_script()))
        self.server=make_server(0,self.root)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.token=self.request('/api/config')[1]['token']

    def tearDown(self):
        self.server.editor_jobs.close(); self.server.shutdown(); self.server.server_close(); self.thread.join(); self.temp.cleanup()

    def request(self,path,data=None,headers=None):
        h={'Content-Type':'application/json','X-Editor-Token':getattr(self,'token','')}
        h.update(headers or {})
        req=Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=h)
        try:
            with urlopen(req,timeout=5) as result:
                return result.status,json.loads(result.read())
        except HTTPError as exc:
            return exc.code,json.loads(exc.read())

    def test_import_edit_conflict_and_mutation_token(self):
        self.assertEqual(self.request('/api/import',{'run':'demo'},{'X-Editor-Token':''})[0],403)
        code,project=self.request('/api/import',{'run':'demo'})
        self.assertEqual(code,201)
        doc=project['document']; doc['scenes'][0]['headline']='Edited title'
        path=f"/api/projects/{project['id']}/save"
        self.assertEqual(self.request(path,{'revision':1,'document':doc})[0],200)
        self.assertEqual(self.request(path,{'revision':1,'document':doc})[0],409)

    def test_foreign_origin_host_and_path_escape_rejected(self):
        self.assertEqual(self.request('/api/config',headers={'Origin':'https://untrusted.example'})[0],403)
        self.assertEqual(self.request('/api/config',headers={'Host':'untrusted.example'})[0],403)
        self.assertEqual(self.request('/api/import',{'run':'../../secret'})[0],400)
        self.assertEqual(self.request('/media/../../secret')[0],404)

    def test_second_server_cannot_share_editor_port(self):
        with self.assertRaises(OSError):
            make_server(self.server.server_port, self.root)

    def test_existing_same_origin_tab_can_save_after_server_token_rotation(self):
        headers={'X-Editor-Token':'previous-server-token','Origin':self.url,'Sec-Fetch-Site':'same-origin'}
        self.assertEqual(self.request('/api/import',{'run':'demo'},headers)[0],201)
        headers['Origin']='https://foreign.example'
        self.assertEqual(self.request('/api/import',{'run':'demo'},headers)[0],403)
        headers['Origin']=self.url;headers['Sec-Fetch-Site']='cross-site'
        self.assertEqual(self.request('/api/import',{'run':'demo'},headers)[0],403)

    def test_script_input_creates_directed_project_and_invalid_input_is_atomic(self):
        from backend.tests.test_director import SCRIPT
        release=threading.Event()
        self.server.editor_jobs._perform=lambda *args: release.wait(5)
        before=len(self.server.editor_store.list())
        self.assertEqual(self.request('/api/projects',{'mode':'script','title':'Library','text':'too short'})[0],400)
        self.assertEqual(len(self.server.editor_store.list()),before)
        try:
            code,project=self.request('/api/projects',{'mode':'script','text':SCRIPT})
            self.assertEqual(code,201)
            self.assertTrue(project['directed'])
            self.assertEqual(project['document']['title'],project['document']['scenes'][0]['headline'])
            self.assertEqual(project['source']['text'],SCRIPT)
            self.assertEqual(project['document']['scenes'][1]['visual']['kind'],'process')
            self.assertEqual(self.server.editor_jobs.status()['action'],'generate')
        finally: release.set()

    def test_audio_supports_byte_ranges(self):
        _,project=self.request('/api/import',{'run':'demo'})
        generate_incremental(self.root/'data/video.json',self.root/'data/generated.json',self.root/'renderer/public',synthesizer=fake_speech)
        uid=project['document']['scenes'][0]['uid']
        req=Request(self.url+f"/media/{project['id']}/audio/{uid}",headers={'Range':'bytes=0-11'})
        with urlopen(req) as response:
            self.assertEqual(response.status,206)
            data=response.read(); self.assertEqual(len(data),12); self.assertEqual(data[:4],b'RIFF')

    def test_invalid_job_and_busy_write_guard(self):
        _,project=self.request('/api/import',{'run':'demo'})
        path=f"/api/projects/{project['id']}/task"
        self.assertEqual(self.request(path,{'revision':1,'action':'regenerate','uid':'bad'})[0],400)
        release=threading.Event()
        self.server.editor_jobs._perform=lambda *args: release.wait(5)
        try:
            self.assertEqual(self.request(path,{'revision':1,'action':'audio'})[0],202)
            self.assertEqual(self.request(f"/api/projects/{project['id']}/save",{'revision':1,'document':project['document']})[0],409)
        finally: release.set()

    def test_new_topic_draft_persists_and_cancel_preserves_project(self):
        def draft(script, args, **kwargs):
            output = Path(args[args.index('--output')+1])
            output.write_text(json.dumps(valid_script()))
        with patch('backend.services.editor_jobs.python_stage', side_effect=draft):
            code, project = self.request('/api/projects', {'topic': valid_script()['topic']})
            self.assertEqual(code, 201)
            self.server.editor_jobs.thread.join(5)
        saved = self.request('/api/projects/'+project['id'])[1]
        self.assertEqual(len(saved['document']['scenes']), 3)
        self.assertEqual(self.server.editor_jobs.status()['status'], 'complete')
        before = copy.deepcopy(saved['document'])
        def wait_for_cancel(*args):
            self.server.editor_jobs.cancel.wait(5)
            raise InterruptedError('Cancelled')
        self.server.editor_jobs._perform = wait_for_cancel
        self.request('/api/projects/'+project['id']+'/task', {'revision': saved['revision'], 'action': 'audio'})
        self.assertEqual(self.request('/api/cancel', {})[0], 200)
        self.server.editor_jobs.thread.join(5)
        self.assertEqual(self.server.editor_jobs.status()['status'], 'cancelled')
        self.assertEqual(self.request('/api/projects/'+project['id'])[1]['document'], before)

    def test_corrupt_or_stale_preview_not_served(self):
        _, project = self.request('/api/import', {'run': 'demo'})
        uid = project['document']['scenes'][0]['uid']
        folder = self.server.editor_store.folder(project['id'])
        target = folder/'preview.png'; target.write_bytes(b'fixture')
        record = {'key': artifact_key(project['document'], self.server.editor_jobs.version, uid), 'file': target.name, 'sha256': file_hash(target)}
        self.server.editor_store.update_artifact(project['id'], 'preview', record, uid)
        self.assertIn(uid, self.request('/api/projects/'+project['id'])[1]['preview_urls'])
        target.write_bytes(b'corrupt')
        self.assertNotIn(uid, self.request('/api/projects/'+project['id'])[1]['preview_urls'])
        self.assertEqual(self.request(f"/media/{project['id']}/preview/{uid}")[0], 404)


if __name__=='__main__': unittest.main()
