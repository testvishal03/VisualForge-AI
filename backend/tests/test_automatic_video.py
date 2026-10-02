import json
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from backend.scripts.plan_length import choose_length
from backend.services.automatic_video import perform
from backend.tests import test_editor,test_storyboard,test_long_video

class LengthTests(unittest.TestCase):
    def test_model_selects_supported_length_and_explains_it(self):
        engine=Mock();engine.generate_json.return_value='{"minutes":7,"reason":"Several concepts need a worked example."}'
        self.assertEqual(choose_length('A detailed tutorial',engine)['minutes'],7)
        self.assertIn('A detailed tutorial',engine.generate_json.call_args.args[0])
    def test_bad_model_result_fails_explicitly(self):
        for value in [True,5,100,'3']:
            engine=Mock();engine.generate_json.return_value=json.dumps({'minutes':value,'reason':'Scope'})
            with self.assertRaises(ValueError):choose_length('Topic',engine)

class AutomaticHTTPTests(unittest.TestCase):
    setUp=test_editor.EditorHTTPTests.setUp
    tearDown=test_editor.EditorHTTPTests.tearDown
    request=test_editor.EditorHTTPTests.request
    def test_prompt_needs_no_duration_or_review_step(self):
        with patch.object(self.server.editor_jobs,'start') as start:
            code,p=self.request('/api/projects',{'mode':'prompt','text':'Explain the water cycle','automatic':True,'profile':'draft'})
        self.assertEqual(code,201,p);self.assertTrue(p['source']['automatic']);self.assertFalse(p['source']['review_first'])
        self.assertEqual(start.call_args.args,(p['id'],'auto_generate'))
    def test_script_preserves_narration_and_derives_length(self):
        from backend.tests.test_director import SCRIPT
        with patch.object(self.server.editor_jobs,'start'):
            code,p=self.request('/api/projects',{'mode':'script','text':SCRIPT,'automatic':True,'profile':'draft'})
        self.assertEqual(code,201,p)
        self.assertEqual(' '.join(s['narration'] for s in p['document']['scenes']),' '.join(SCRIPT.split()))
        self.assertGreater(p['source']['minutes'],0)

class AutomaticJobTests(unittest.TestCase):
    setUp=test_storyboard.StoryboardTests.setUp
    def test_long_script_persists_planning_before_reusing_output(self):
        import copy
        from backend.services.run_state import file_hash
        doc=copy.deepcopy(self.p['document'])
        template=doc['scenes'][0]
        doc['scenes']=[]
        for index in range(17):
            row=copy.deepcopy(template)
            row.update(uid=f'{index+1:012x}',headline=f'Explanation {index+1}',narration=template['narration']+f' This is example {index+1}.')
            row['visual']={'kind':'explanation','items':[],'directed':True}
            doc['scenes'].append(row)
        p=self.store.create(doc['topic'],doc,source={'mode':'script','review_first':False,'profile':'draft'})
        planned=copy.deepcopy(p)
        for row in planned['document']['scenes']:row['visual']['planned']=True
        folder=self.store.folder(p['id']);output=folder/'draft.mp4';output.write_bytes(b'verified fixture')
        self.store.update_artifact(p['id'],'draft_render',{'key':self.jobs.output_key(planned,profile='draft'),'file':'draft.mp4','sha256':file_hash(output),'profile':'draft','styled':True})
        with patch('backend.services.editor_jobs.python_stage') as stage:
            self.jobs._perform(self.store.load(p['id']),'generate',None,'',folder)
            # Long scripts plan only their weakest scenes, within a time budget. This stage writes
            # no plan, so the video keeps its rule-based visuals and still reuses its export.
            # The planner runs at most once, and only when some scenes' labels are weak.
            self.assertLessEqual(stage.call_count, 1)
            if stage.call_count:
                args = stage.call_args[0][1]
                self.assertIn('--only', args)
                self.assertIn('--budget', args)
        saved=self.store.load(p['id'])
        self.assertTrue(all(s['visual'].get('planned') for s in saved['document']['scenes']))
        self.assertTrue(self.jobs.artifact_ready(saved,saved['draft_render']))
        self.assertTrue(self.jobs.present(saved)['draft_url'])
        self.jobs.version='new-renderer-version'
        presented=self.jobs.present(saved)
        self.assertIsNone(presented['draft_url'])
        self.assertIn('previous=1',presented['previous_export_url'])
        output.write_bytes(b'corrupted export')
        self.assertIsNone(self.jobs.present(saved)['previous_export_url'])

    def test_plan_is_saved_and_retry_reuses_it(self):
        p=self.p;p['source'].update(automatic=True,mode='prompt');folder=self.store.folder(p['id'])
        def stage(script,args,**kwargs):Path(args[1]).write_text(json.dumps({'minutes':2,'reason':'A focused explanation.'}))
        with patch('backend.services.automatic_video.python_stage',side_effect=stage) as planner,patch.object(self.jobs,'_perform') as generate:
            perform(self.jobs,p,folder)
            self.assertEqual(generate.call_args.args[1],'generate')
            saved=self.store.load(p['id']);self.assertEqual(saved['source']['length_plan']['minutes'],2)
            perform(self.jobs,saved,folder);self.assertEqual(planner.call_count,1)
    def test_long_prompt_converts_to_chapter_pipeline(self):
        from backend.services.long_video import chapters_store
        from backend.services.script_generator import write_json_atomic
        p=self.p;p['source'].update(automatic=True,mode='prompt',profile='draft');folder=self.store.folder(p['id'])
        def stage(script,args,**kwargs):Path(args[1]).write_text(json.dumps({'minutes':7,'reason':'A full tutorial.'}))
        calls=[]
        def chapter(jobs,parent,action,uid):
            calls.append(action)
            if action=='long_outline':
                children=chapters_store(self.store,parent)
                child=children.create(p['topic'],p['document'])
                parent['long_video']['chapters']=[{'id':child['id'],'title':p['topic'],'seconds':420}]
                write_json_atomic(folder/'project.json',parent)
        with patch('backend.services.automatic_video.python_stage',side_effect=stage),patch('backend.services.long_video.perform',side_effect=chapter):
            perform(self.jobs,p,folder)
        self.assertEqual(calls,['long_outline','long_scripts','long_render_draft'])
        self.assertIn('long_video',self.store.load(p['id']))

    def test_cancelled_job_does_not_start_model(self):
        self.p['source']['automatic']=True;self.jobs.cancel.set()
        with patch('backend.services.automatic_video.python_stage') as planner:
            with self.assertRaises(InterruptedError):perform(self.jobs,self.p,self.store.folder(self.p['id']))
        planner.assert_not_called()

class AutomaticChapterTests(unittest.TestCase):
    setUp=test_long_video.LongVideoTests.setUp
    populate=test_long_video.LongVideoTests.populate
    persist=test_long_video.LongVideoTests.persist
    def test_long_automatic_flow_continues_without_frontend_chaining(self):
        from backend.services.editor_jobs import EditorJobs
        self.populate();self.p['source'].update(automatic=True,profile='draft');self.persist()
        jobs=EditorJobs(Path(__file__).resolve().parents[2],self.store)
        with patch('backend.services.long_video.perform') as task:
            perform(jobs,self.p,self.store.folder(self.p['id']))
        self.assertEqual([call.args[2] for call in task.call_args_list],['long_scripts','long_render_draft'])


class WorkerEncodingTests(unittest.TestCase):
    def test_unicode_logs_remain_utf8_and_legacy_console_is_safe(self):
        import io,sys,tempfile
        from backend.services.process_runner import execute,console_progress
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            execute([sys.executable,'-c',"print(chr(0x2192)+chr(0x1f4a7))"],cwd=folder,log=folder/'unicode.log')
            self.assertEqual((folder/'unicode.log').read_text(encoding='utf-8').strip(),chr(0x2192)+chr(0x1f4a7))
        raw=io.BytesIO();console=io.TextIOWrapper(raw,encoding='cp1252')
        with patch('sys.stdout',console):console_progress('stage '+chr(0xfffd))
        self.assertIn(b'stage ?',raw.getvalue())
