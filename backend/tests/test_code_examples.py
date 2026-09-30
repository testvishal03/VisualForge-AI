from backend.tests.render_stubs import cached as cached_render_stub
import copy
import unittest
import json
from pathlib import Path
from unittest.mock import patch
from backend.services.code_examples import compute,select_spec,validate_spec,narration_issues,timed_example


class CodeExampleTests(unittest.TestCase):
    def spec(self,kind,values=None,threshold=15):
        return {'kind':kind,'values':values or [12,25,8],'threshold':threshold,'sentence':0}

    def test_real_python_results_and_iteration_states(self):
        self.assertEqual(compute(self.spec('python_variables'))['output'],['37'])
        self.assertEqual(compute(self.spec('python_condition'))['output'],['False'])
        true=compute(self.spec('python_condition',threshold=12));self.assertEqual(true['output'],['True'])
        self.assertEqual(true['steps'][2]['line'],3)
        loop=compute(self.spec('python_loop'))
        self.assertEqual(loop['output'],['45'])
        self.assertEqual([s['variables']['total'] for s in loop['steps'] if s['line']==3],[12,37,45])

    def test_sql_results_are_computed_from_shared_data(self):
        filtered=compute(self.spec('sql_filter'));joined=compute(self.spec('sql_join'))
        self.assertEqual(filtered['rows'],[[2,25]])
        self.assertEqual(joined['rows'],[[1,'Alice',12],[2,'Bob',25],[3,'Alice',8]])
        self.assertEqual(filtered['orders'],joined['orders'])
        self.assertEqual(compute(self.spec('sql_filter',threshold=100))['rows'],[])

    def test_untrusted_code_and_unbounded_inputs_are_rejected(self):
        for changes in [{'values':['__import__("os")',2]}, {'values':[True,2]}, {'values':list(range(6))},{'threshold':1.5},{'code':'import os'},{'kind':'python_arbitrary'}]:
            with self.assertRaises(ValueError):validate_spec({**self.spec('python_loop'),**changes},'Example narration.')

    def test_selection_requires_relevant_topic_and_preserves_explicit_numeric_examples(self):
        self.assertIsNone(select_spec({'narration':'A water cycle repeats in a loop.'}))
        self.assertEqual(select_spec({'topic':'Python','narration':'A loop adds each amount to a running total.'})['kind'],'python_loop')
        self.assertIsNone(select_spec({'narration':'Python prints 42 after this loop.'}))
        self.assertIsNone(select_spec({'narration':'SQL LEFT JOIN retains unmatched rows.'}))
        self.assertEqual(select_spec({'topic':'Python and SQL','narration':'SQL filters orders using a WHERE condition.'})['kind'],'sql_filter')
        self.assertIsNone(select_spec({'narration':'SQL filters orders below the chosen threshold.'}))
        self.assertIsNone(select_spec({'narration':'Python uses loops.','visual':{'demo':{'kind':'off'}}}))

    def test_explicit_output_mismatch_blocks_and_inputs_remain_unchanged(self):
        scene={'narration':'This Python example prints 99.','visual':{'demo':self.spec('python_variables')}}
        before=copy.deepcopy(scene)
        self.assertEqual(narration_issues(scene)[0]['code'],'example_output_mismatch')
        self.assertEqual(scene,before)
        scene['narration']='This Python example prints 37.'
        self.assertEqual(narration_issues(scene),[])

    def test_timing_uses_measured_start_and_remains_within_narration(self):
        scene={'narration':'Python loops add each amount to a running total.','visual':{'demo':self.spec('python_loop')}}
        result=timed_example(scene,[{'start':2,'end':10}])
        self.assertEqual(result['at'][0],2)
        self.assertLess(result['at'][-1],10)
        self.assertEqual(result['at'],sorted(result['at']))


if __name__=='__main__':unittest.main()


class ExampleWorkflowTests(unittest.TestCase):
    from backend.tests.test_storyboard import StoryboardTests
    setUp=StoryboardTests.setUp

    def test_scene_preview_injects_trace_and_preserves_authored_inputs(self):
        from backend.services.incremental_audio import generate_incremental
        from backend.tests.test_pipeline import fake_speech
        doc=copy.deepcopy(self.p['document']);row=doc['scenes'][0]
        row['narration']='A Python loop adds each amount to a running total and prints the sum after the final iteration.'
        row['visual']['demo']={'kind':'python_loop','values':[2,4,6],'threshold':5,'sentence':0}
        p=self.store.save(self.p['id'],self.p['revision'],doc);uid=row['uid']
        captured=[]
        def stage(script,args,**kwargs):
            if script.name=='generate_audio.py':
                generate_incremental(Path(args[1]),Path(args[3]),self.root/'renderer/public',synthesizer=fake_speech,directed=True)
        def render(command,**kwargs):
            props=Path(str(command[5]).split('=',1)[1]);captured.append(json.loads(props.read_text()))
            Path(command[4]).write_bytes(b'preview fixture')
        with patch('backend.services.editor_jobs.python_stage',side_effect=stage),patch('backend.services.editor_jobs.execute',side_effect=render),patch('backend.services.editor_jobs.node_executable',return_value='node'),patch('backend.services.scene_cache.render_cached',side_effect=cached_render_stub),patch('backend.services.scene_cache.thumbnails'):
            self.jobs._perform(p,'motion',uid,'',self.store.folder(p['id']))
        scene=captured[0]['videoData']['scenes'][0]
        self.assertEqual(scene['demonstration']['output'],['12'])
        self.assertEqual(scene['teaching']['component'],'python')
        self.assertEqual(scene['narration'],row['narration'])
        self.assertEqual(self.store.load(p['id'])['document'],p['document'])
