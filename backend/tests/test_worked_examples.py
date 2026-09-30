from backend.tests.render_stubs import cached as cached_render_stub
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.services.worked_examples import prepare,validate_spec,validate_result,narration_issues,key_for
from backend.services.editor_store import validate_document
from backend.tests import test_storyboard

MODEL={'model':'fixture.gguf','runtime':'fixture'}
SPEC={'input':'Hi','label':'Example','steps':[{'action':'tokens','sentence':0}]}

def result():
    return {'input':'Hi','tokens':[{'id':42,'piece':'Hi'}],'generated_ids':[7,8],
            'prefixes':[' there',' there!'],'continuation':' there!','model':MODEL,
            'key':key_for('Hi',MODEL),'mode':'raw_completion','seed':42}

class Engine:
    def __init__(self):self.calls=[]
    def _load(self):pass
    def _request(self,route,payload,**kwargs):
        self.calls.append((route,payload))
        if route=='/tokenize':return {'tokens':[{'id':42,'piece':'Hi'}]}
        if route=='/completion':return {'tokens':[7,8],'content':' there!'}
        return {'content':' there!' if len(payload['tokens'])==2 else ' there'}

class WorkedExamplesTests(unittest.TestCase):
    def test_measures_raw_ids_and_reuses_only_same_model_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine=Engine();cache=Path(tmp)
            measured=prepare('Hi',engine,MODEL,cache)
            self.assertEqual(measured,result())
            self.assertEqual(engine.calls[1][1]['prompt'],[42])
            self.assertFalse(engine.calls[0][1]['parse_special'])
            calls=len(engine.calls);prepare('Hi',engine,MODEL,cache)
            self.assertEqual(len(engine.calls),calls)
            prepare('Hi',engine,{**MODEL,'runtime':'updated'},cache)
            self.assertGreater(len(engine.calls),calls)

    def test_trace_and_bytes_are_verified(self):
        value=result();value['tokens']=[{'id':1,'piece':[72,105]}];validate_result(value)
        for field,bad in [('tokens',[{'id':1,'piece':'wrong'}]),('generated_ids',[True]),('prefixes',['wrong'])]:
            value=result();value[field]=bad
            with self.assertRaises(ValueError):validate_result(value)

    def test_spec_rejects_overloaded_or_out_of_range_cues(self):
        validate_spec(SPEC,'Split text into tokens.')
        for steps in [[{'action':[],'sentence':0}],[{'action':'tokens','sentence':0},{'action':'ids','sentence':0}],[{'action':'tokens','sentence':1}]]:
            with self.assertRaises(ValueError):validate_spec({**SPEC,'steps':steps},'One sentence.')
        with self.assertRaises(ValueError):validate_spec({**SPEC,'input':'x'*81},'One sentence.')

    def test_numeric_contradiction_is_blocking(self):
        scene={'visual':{'worked':SPEC},'narration':'Split this into 3 tokens.'}
        self.assertTrue(any(i['severity']=='error' for i in narration_issues(scene,result())))

class WorkedJobsTests(unittest.TestCase):
    setUp=test_storyboard.StoryboardTests.setUp

    def add_example(self):
        doc=copy.deepcopy(self.p['document']);doc['scenes'][0]['visual']['worked']=copy.deepcopy(SPEC)
        self.p=self.store.save(self.p['id'],self.p['revision'],doc)
        return doc['scenes'][0]['uid']

    def test_authored_document_cannot_supply_measured_data(self):
        self.add_example();doc=copy.deepcopy(self.p['document'])
        doc['scenes'][0]['visual']['workedData']=result()
        with self.assertRaises(ValueError):validate_document(doc)

    def test_preparation_is_selected_and_does_not_approve_or_mutate(self):
        uid=self.add_example();before=copy.deepcopy(self.p)
        calls=[]
        def stage(script,args,**kwargs):
            calls.append(script.name)
            self.assertEqual(json.loads(Path(args[0]).read_text()),['Hi'])
            Path(args[1]).write_text(json.dumps({'Hi':result()}))
        with patch('backend.services.editor_jobs.python_stage',side_effect=stage),patch('backend.services.editor_jobs.model_dependency',return_value=MODEL):
            self.jobs.start(self.p['id'],'prepare_example',uid);self.jobs.thread.join(5)
            self.assertEqual(self.jobs.status()['status'],'complete',self.jobs.status())
        self.assertEqual(calls,['prepare_examples.py'])
        self.assertEqual(self.store.load(self.p['id']),before)

    def test_narration_edit_preserves_example_and_model_changes_invalidate(self):
        uid=self.add_example();doc=copy.deepcopy(self.p['document'])
        doc['scenes'][0]['narration']='The tokenizer splits text into pieces. Each piece has a numerical identifier that the language model can use.'
        updated=self.store.save(self.p['id'],self.p['revision'],doc)
        self.assertEqual(updated['document']['scenes'][0]['visual']['worked'],SPEC)
        with patch('backend.services.editor_jobs.model_dependency',return_value=MODEL):old=self.jobs.output_key(updated,uid)
        with patch('backend.services.editor_jobs.model_dependency',return_value={**MODEL,'runtime':'new'}):new=self.jobs.output_key(updated,uid)
        self.assertNotEqual(old,new)


    def test_motion_injects_measured_data_without_saving_it_in_document(self):
        from backend.services.incremental_audio import generate_incremental
        from backend.tests.test_pipeline import fake_speech
        uid=self.add_example();before=copy.deepcopy(self.p['document']);order=[]
        def stage(script,args,**kwargs):
            order.append(script.name)
            if script.name=='prepare_examples.py':Path(args[1]).write_text(json.dumps({'Hi':result()}))
            if script.name=='generate_audio.py':generate_incremental(Path(args[1]),Path(args[3]),self.root/'renderer/public',synthesizer=fake_speech,directed=True)
        def render(command,**kwargs):Path(command[4]).write_bytes(b'fixture')
        with patch('backend.services.editor_jobs.python_stage',side_effect=stage),patch('backend.services.editor_jobs.model_dependency',return_value=MODEL),patch('backend.services.editor_jobs.execute',side_effect=render),patch('backend.services.editor_jobs.node_executable',return_value='node'),patch('backend.services.scene_cache.render_cached',side_effect=cached_render_stub),patch('backend.services.scene_cache.thumbnails'):
            self.jobs.start(self.p['id'],'motion',uid);self.jobs.thread.join(5)
            self.assertEqual(self.jobs.status()['status'],'complete',self.jobs.status())
        props=json.loads((self.store.folder(self.p['id'])/f'motion-{uid}-props.json').read_text())
        self.assertEqual(len(props['videoData']['scenes']),1)
        self.assertEqual(props['videoData']['scenes'][0]['visual']['workedData'],result())
        self.assertLess(order.index('prepare_examples.py'),order.index('generate_audio.py'))
        self.assertEqual(self.store.load(self.p['id'])['document'],before)

class WorkedChapterTests(unittest.TestCase):
    from backend.tests import test_long_video as fixtures
    setUp=fixtures.LongVideoTests.setUp
    populate=fixtures.LongVideoTests.populate
    persist=fixtures.LongVideoTests.persist

    def test_chapter_task_routes_and_preserves_approval(self):
        from backend.services.long_video import perform
        from backend.services.editor_jobs import EditorJobs
        self.populate()
        child=self.children.load(self.p['long_video']['chapters'][0]['id'])
        uid=child['document']['scenes'][0]['uid']
        self.p['long_video']['script_approved']='unchanged';self.persist()
        jobs=EditorJobs(Path(__file__).resolve().parents[2],self.store)
        with patch.object(EditorJobs,'_perform') as task:
            perform(jobs,self.p,'long_scene_prepare_example',uid)
            self.assertEqual(task.call_args.args[1],'prepare_example')
            self.assertEqual(task.call_args.args[0]['id'],child['id'])
        self.assertEqual(self.store.load(self.p['id'])['long_video']['script_approved'],'unchanged')
