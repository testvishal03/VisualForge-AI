from backend.tests.render_stubs import cached as cached_render_stub
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.services.editor_store import EditorStore,document_from_video
from backend.services.editor_jobs import EditorJobs
from backend.services.director import script_to_video,build_direction
from backend.tests.test_workspaces import WATER
from backend.services.incremental_audio import generate_incremental
from backend.tests.test_pipeline import fake_speech

class StoryboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'renderer/src').mkdir(parents=True)
        (self.root/'renderer/remotion.config.ts').write_text('fixture')
        self.store=EditorStore(self.root/'projects')
        video=script_to_video('Water',WATER);plan=build_direction(video)
        for row in plan['scenes']:row['planned']=True
        self.p=self.store.create(video.topic,document_from_video(video,plan),source={'mode':'script','review_first':True})
        self.jobs=EditorJobs(self.root,self.store)

    def test_generation_stops_for_review_before_audio_or_render(self):
        with patch('backend.services.editor_jobs.python_stage') as stage,patch('backend.services.editor_jobs.execute') as render:
            self.jobs.start(self.p['id'],'generate');self.jobs.thread.join(5)
            self.assertEqual(self.jobs.status()['status'],'complete')
            self.assertEqual(self.jobs.status()['result_kind'],'storyboard')
            stage.assert_not_called();render.assert_not_called()
        with self.assertRaisesRegex(ValueError,'approve'):
            self.jobs.start(self.p['id'],'render_draft')

    def test_approval_is_invalidated_by_animation_edit_and_stale_revision_rejected(self):
        approved=self.store.approve_storyboard(self.p['id'],self.p['revision'])
        self.assertTrue(self.jobs.present(approved)['storyboard_approved'])
        with self.assertRaisesRegex(ValueError,'changed'):
            self.store.approve_storyboard(self.p['id'],self.p['revision'])
        doc=copy.deepcopy(approved['document']);doc['scenes'][0]['visual']['motion']='focus'
        changed=self.store.save(self.p['id'],approved['revision'],doc)
        self.assertFalse(self.jobs.present(changed)['storyboard_approved'])
        with self.assertRaisesRegex(ValueError,'approve'):
            self.jobs.start(self.p['id'],'render')

    def test_motion_preview_renders_only_selected_scene_and_preserves_siblings(self):
        uid=self.p['document']['scenes'][0]['uid'];before=copy.deepcopy(self.p['document']);inputs=[]
        def stage(script,args,**kwargs):
            if script.name=='generate_audio.py':
                inputs.append(json.loads(Path(args[1]).read_text())['scenes'])
                generate_incremental(Path(args[1]),Path(args[3]),self.root/'renderer/public',synthesizer=fake_speech,directed=True)
        def render(command,**kwargs):Path(command[4]).write_bytes(b'fixture')
        with patch('backend.services.editor_jobs.python_stage',side_effect=stage),patch('backend.services.editor_jobs.execute',side_effect=render),patch('backend.services.editor_jobs.node_executable',return_value='node'),patch('backend.services.scene_cache.render_cached',side_effect=cached_render_stub),patch('backend.services.scene_cache.thumbnails'):
            self.jobs.start(self.p['id'],'motion',uid);self.jobs.thread.join(5)
            self.assertEqual(self.jobs.status()['status'],'complete',self.jobs.status())
        self.assertEqual(len(inputs[0]),1)
        current=self.store.load(self.p['id']);self.assertEqual(current['document'],before)
        self.assertIn(uid,self.jobs.present(current)['motion_urls'])
        self.assertIsNone(current['render'])
        doc=copy.deepcopy(before);doc['scenes'][0]['visual']['motion']='focus'
        changed=self.store.save(current['id'],current['revision'],doc)
        self.assertNotIn(uid,self.jobs.present(changed)['motion_urls'])

    def test_style_sample_does_not_approve_or_replace_full_video(self):
        before=copy.deepcopy(self.p['document'])
        def stage(script,args,**kwargs):
            if script.name=='generate_audio.py':
                generate_incremental(Path(args[1]),Path(args[3]),self.root/'renderer/public',synthesizer=fake_speech,directed=True)
        def render(command,**kwargs):Path(command[4]).write_bytes(b'fixture')
        with patch('backend.services.editor_jobs.python_stage',side_effect=stage),patch('backend.services.editor_jobs.execute',side_effect=render),patch('backend.services.editor_jobs.node_executable',return_value='node'),patch('backend.services.scene_cache.render_cached',side_effect=cached_render_stub),patch('backend.services.scene_cache.thumbnails'):
            self.jobs.start(self.p['id'],'style_preview');self.jobs.thread.join(5)
            self.assertEqual(self.jobs.status()['status'],'complete',self.jobs.status())
        current=self.store.load(self.p['id']);self.assertEqual(current['document'],before)
        ready=self.jobs.present(current)
        self.assertTrue(ready['style_url']);self.assertFalse(ready['storyboard_approved'])
        self.assertIsNone(ready['draft_url']);self.assertIsNone(ready['video_url'])
        doc=copy.deepcopy(before);doc['scenes'][0]['visual']['motion']='focus'
        changed=self.store.save(current['id'],current['revision'],doc)
        self.assertIsNone(self.jobs.present(changed)['style_url'])

if __name__=='__main__':unittest.main()
