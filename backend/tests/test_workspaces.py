from backend.tests.render_stubs import cached as cached_render_stub
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.workspaces import Workspaces
from backend.services.editor_store import EditorStore, document_from_video, validate_document
from backend.services.editor_jobs import EditorJobs
from backend.services.director import script_to_video, build_direction
from backend.services.duration import duration_report, word_budget
from backend.services.script_generator import generate_video_script
from backend.tests.test_script_generation import FakeLLM, valid_script, draft_responses
from backend.tests import test_editor
from backend.services.incremental_audio import generate_incremental
from backend.tests.test_pipeline import fake_speech

WATER='''Sunlight warms surface water, causing evaporation into the air. Cooling water vapor condenses and clouds form above the land. Precipitation falls as rain when droplets grow heavy. Water collects in rivers and flows back toward the ocean.

The water cycle moves water between the surface and the atmosphere. Local temperature and weather affect how quickly water evaporates and where precipitation falls.'''
COMPUTER='''A computer consists of a processor, memory, and storage. The processor carries out instructions, memory holds active work, and storage keeps files available after the power is turned off.

First, a keyboard sends your typed letters to the computer. Next, software processes those letters according to the instructions it follows. Finally, the screen displays the text so you can read your message.'''
TIMELINE='''Consider a fictional school garden with a three year plan. In 2020, students prepare soil and plant the first seeds. In 2021, they add beds for vegetables. In 2022, they build a compost area to reuse plant material.

Students can read a timeline to compare the stages of their garden project. Keeping events in order helps them see which work was completed before each later improvement.'''


class WorkspaceTests(unittest.TestCase):
    def test_adoption_trash_restore_duplicate_and_reorder_preserve_sources(self):
        with tempfile.TemporaryDirectory() as d:
            store=EditorStore(Path(d));spaces=Workspaces(store)
            v=script_to_video('Water cycle',WATER);doc=document_from_video(v,build_direction(v))
            p=store.create(v.topic,doc,source={'mode':'script'})
            raw=(store.folder(p['id'])/'project.json').read_bytes()
            adopted=spaces.list()[0]
            self.assertEqual(spaces.list()[0]['id'],adopted['id'])
            self.assertEqual((store.folder(p['id'])/'project.json').read_bytes(),raw)
            spaces.change(adopted['id'],'trash',{})
            with self.assertRaises(ValueError): spaces.require_active(p['id'])
            spaces.change(adopted['id'],'restore',{})
            clone=spaces.change(adopted['id'],'duplicate',{})
            self.assertNotEqual(clone['episodes'],adopted['episodes'])
            cp=store.load(clone['episodes'][0]);self.assertEqual(cp['document'],doc);self.assertIsNone(cp['render'])
            self.assertEqual((store.folder(p['id'])/'project.json').read_bytes(),raw)
            series=spaces.create({'name':'Science','kind':'series'})
            p2=store.create('Water cycle',doc);spaces.attach(series['id'],p2['id'])
            p3=store.create('Water cycle',doc);spaces.attach(series['id'],p3['id'])
            spaces.change(series['id'],'reorder',{'episodes':[p3['id'],p2['id']]})
            self.assertEqual(spaces.get(series['id'])['episodes'],[p3['id'],p2['id']])
            with self.assertRaises(ValueError): spaces.change(series['id'],'reorder',{'episodes':[p2['id'],p2['id']]})
            with self.assertRaises(ValueError): spaces.change(series['id'],'save',{'kind':'single'})
            self.assertEqual(spaces.get(series['id'])['kind'],'series')

    def test_meaning_specific_diagrams_and_grounded_fallbacks(self):
        for title,script,expected in [('Water cycle',WATER,'water_cycle'),('Computer',COMPUTER,'components'),('Garden',TIMELINE,'timeline')]:
            video=script_to_video(title,script);plan=build_direction(video)
            self.assertEqual(plan['scenes'][0]['kind'],expected)
            self.assertEqual(' '.join(s.narration for s in video.scenes),' '.join(script.split()))
            validate_document(document_from_video(video,plan))
        video=script_to_video('Incomplete water',WATER.replace('Precipitation falls as rain when droplets grow heavy.','Clouds contain many tiny droplets suspended in air.'))
        self.assertNotEqual(build_direction(video)['scenes'][0]['kind'],'water_cycle')
        video=script_to_video('Garden',TIMELINE.replace('In 2021','In 2019'))
        self.assertNotEqual(build_direction(video)['scenes'][0]['kind'],'timeline')
        video=script_to_video('Loop',COMPUTER.replace('Finally, the screen displays the text so you can read your message.','Finally, the screen displays the text and the cycle repeats.'))
        self.assertEqual(build_direction(video)['scenes'][1]['kind'],'cycle')

    def test_style_and_profile_invalidate_render_without_touching_narration(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'renderer/src').mkdir(parents=True);(root/'renderer/remotion.config.ts').write_text('fixture')
            store=EditorStore(root/'projects');video=script_to_video('Water cycle',WATER)
            p=store.create(video.topic,document_from_video(video,build_direction(video)),source={'mode':'prompt','minutes':3})
            jobs=EditorJobs(root,store);key=jobs.output_key(p)
            self.assertTrue(any(i['code']=='duration_target' for i in jobs.present(p)['quality']['issues']))
            self.assertNotEqual(key,jobs.output_key(p,profile='draft'))
            w=jobs.workspaces.for_project(p['id'])
            jobs.workspaces.change(w['id'],'save',{'theme':'forest'})
            self.assertNotEqual(key,jobs.output_key(p))
            self.assertEqual(p,store.load(p['id']))

    def test_draft_final_isolation_and_failed_validation_preserves_publication(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'renderer/src').mkdir(parents=True);(root/'renderer/remotion.config.ts').write_text('fixture')
            store=EditorStore(root/'projects');v=script_to_video('Water cycle',WATER)
            p=store.create(v.topic,document_from_video(v,build_direction(v)),source={'mode':'script','profile':'draft'})
            jobs=EditorJobs(root,store);commands=[];fail=False
            def stage(script,args,**kwargs):
                if script.name=='generate_audio.py':
                    generate_incremental(Path(args[1]),Path(args[3]),root/'renderer/public',synthesizer=fake_speech,directed=True)
                elif script.name=='plan_visuals.py':
                    plan=build_direction(v)
                    for row in plan['scenes']: row['planned']=True
                    Path(args[1]).write_text(json.dumps(plan))
                elif fail: raise ValueError('Fixture validation failure')
            def execute(command,**kwargs):
                commands.append(command);Path(command[4]).write_bytes(b'draft' if '--scale=0.6666666666666666' in command else b'final')
            with patch('backend.services.editor_jobs.python_stage',side_effect=stage),patch('backend.services.editor_jobs.execute',side_effect=execute),patch('backend.services.editor_jobs.node_executable',return_value='node'),patch('backend.services.scene_cache.render_cached',side_effect=cached_render_stub),patch('backend.services.scene_cache.thumbnails'):
                for action in ('generate','render'):
                    jobs.start(p['id'],action);jobs.thread.join(5);self.assertEqual(jobs.status()['status'],'complete',jobs.status())
                folder=store.folder(p['id']);self.assertEqual((folder/'draft.mp4').read_bytes(),b'draft');self.assertEqual((folder/'video.mp4').read_bytes(),b'final')
                ready=jobs.present(store.load(p['id']));self.assertTrue(ready['draft_url']);self.assertTrue(ready['video_url'])
                w=jobs.workspaces.for_project(p['id']);jobs.workspaces.change(w['id'],'save',{'theme':'sunset'})
                self.assertIsNone(jobs.present(store.load(p['id']))['video_url'])
                fail=True;jobs.start(p['id'],'render');jobs.thread.join(5)
                self.assertEqual(jobs.status()['status'],'failed')
                self.assertEqual((folder/'video.mp4').read_bytes(),b'final')
                self.assertEqual((folder/'draft.mp4').read_bytes(),b'draft')

    def test_measured_duration_and_word_budget(self):
        v=script_to_video('Water cycle',WATER);doc=document_from_video(v)
        estimate=duration_report(doc,{},30);self.assertIsNone(estimate['measured_seconds'])
        audio={s['uid']:{'duration':12.001} for s in doc['scenes']}
        actual=duration_report(doc,audio,10)
        self.assertAlmostEqual(actual['measured_seconds'],25.07)
        self.assertTrue(actual['outside_target'])
        self.assertLess(word_budget(.5,3)[1],word_budget(2,8)[1])

    def test_chart_uses_only_explicit_percentages_and_rejects_bad_values(self):
        script='''In this fictional survey, walking accounts for 40 percent of trips. Cycling accounts for 25 percent of trips in the same sample.

These invented figures demonstrate how a percentage chart compares categories. The remaining trips use other transport modes that are outside this example.'''
        v=script_to_video('Transport example',script);plan=build_direction(v)
        self.assertEqual(plan['scenes'][0]['kind'],'chart')
        self.assertEqual(plan['scenes'][0]['values'],[40,25])
        doc=document_from_video(v,plan)
        doc['scenes'][0]['visual']['values'][0]=101
        with self.assertRaises(ValueError): validate_document(doc)
        v=script_to_video('No data',script.replace('40 percent','many').replace('25 percent','some'))
        self.assertNotEqual(build_direction(v)['scenes'][0]['kind'],'chart')

    def test_over_budget_model_scene_gets_targeted_retry(self):
        good=valid_script();responses=draft_responses(good)
        responses.insert(2,{'narration':good['scenes'][0]['narration']+' Visitors can ask staff for more details about where each book is stored.'})
        llm=FakeLLM(responses)
        with tempfile.TemporaryDirectory() as d:
            video=generate_video_script(good['topic'],Path(d)/'video.json',.5,llm=llm)
        self.assertEqual(video.model_dump(),good)
        self.assertIn('requested duration',llm.prompts[3])

    def test_duration_fallback_keeps_valid_text_and_reuses_it_on_resume(self):
        good=valid_script();long=good['scenes'][0]['narration']+' Visitors can ask staff for more details about where each book is stored.'
        responses=draft_responses(good);responses[2:3]=[{'narration':long},{'narration':long}]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report=root/'report.json'
            video=generate_video_script(good['topic'],root/'video.json',.5,llm=FakeLLM(responses),checkpoint_dir=root/'drafts',report_path=report)
            self.assertEqual(video.scenes[0].narration,long)
            self.assertTrue(any(a['status']=='accepted_with_duration_warning' for a in json.loads(report.read_text())['attempts']))
            again=generate_video_script(good['topic'],root/'video.json',.5,llm=FakeLLM([]),checkpoint_dir=root/'drafts',report_path=report)
            self.assertEqual(video,again)
            self.assertTrue(any(a['status']=='reused_with_duration_warning' for a in json.loads(report.read_text())['attempts']))


class WorkspaceHTTPTests(unittest.TestCase):
    setUp = test_editor.EditorHTTPTests.setUp
    tearDown = test_editor.EditorHTTPTests.tearDown
    request = test_editor.EditorHTTPTests.request
    def test_workspace_routes_busy_guard_and_trash(self):
        code,w=self.request('/api/workspaces',{'name':'Series','kind':'series'})
        self.assertEqual(code,201)
        self.assertEqual(self.request('/api/workspaces',{'name':'bad','theme':'unknown'})[0],400)
        self.assertEqual(self.request(f"/api/workspaces/{w['id']}/trash",{})[0],200)
        self.assertEqual(self.request('/api/projects',{'workspace_id':w['id'],'mode':'script','text':WATER})[0],400)
        self.assertEqual(self.request(f"/api/workspaces/{w['id']}/restore",{})[0],200)
        with patch.object(self.server.editor_jobs,'start'):
            code,p=self.request('/api/projects',{'workspace_id':w['id'],'mode':'script','title':'Water cycle','text':WATER,'profile':'draft'})
            self.assertEqual(code,201)
        self.assertEqual(p['workspace']['id'],w['id'])
        self.assertEqual(self.request('/api/workspaces')[1][0]['episodes'],[p['id']])
        with patch.object(self.server.editor_jobs,'busy',return_value=True):
            self.assertEqual(self.request(f"/api/workspaces/{w['id']}/trash",{})[0],409)
        self.request(f"/api/workspaces/{w['id']}/trash",{})
        self.assertEqual(self.request(f"/api/projects/{p['id']}/save",{'revision':p['revision'],'document':p['document']})[0],400)
