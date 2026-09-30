from backend.tests.render_stubs import cached as cached_render_stub
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.tests import test_storyboard, test_editor, test_long_video
from backend.services.automatic_video import perform
from backend.services.workspaces import next_topic, Workspaces, GENERATIVE_AI_TOPICS
from backend.services.script_generator import write_json_atomic


class ReviewHTTPTests(unittest.TestCase):
    setUp = test_editor.EditorHTTPTests.setUp
    tearDown = test_editor.EditorHTTPTests.tearDown
    request = test_editor.EditorHTTPTests.request

    def test_new_creator_never_auto_approves_pasted_script(self):
        from backend.tests.test_director import SCRIPT
        with patch.object(self.server.editor_jobs, 'start'):
            status, p = self.request('/api/projects', {'mode':'script','text':SCRIPT,'automatic':True,'approval_required':True})
        self.assertEqual(status, 201)
        self.assertTrue(p['source']['review_first'])
        self.assertEqual(p['source']['minimum_seconds'], 0)
        self.assertFalse(p['storyboard_approved'])
        self.assertEqual(' '.join(s['narration'] for s in p['document']['scenes']), ' '.join(SCRIPT.split()))


class ReviewJobTests(unittest.TestCase):
    setUp = test_storyboard.StoryboardTests.setUp

    def setup_review(self):
        self.p['source'].update(automatic=True, approval_required=True, minimum_seconds=420, minutes=10, profile='draft')
        write_json_atomic(self.store.folder(self.p['id'])/'project.json', self.p)

    def test_no_audio_before_approval_and_direct_render_cannot_bypass(self):
        self.setup_review()
        with patch('backend.services.editor_jobs.python_stage') as stage:
            perform(self.jobs, self.p, self.store.folder(self.p['id']))
            stage.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'approve'):
                self.jobs._perform(self.p, 'render_draft', None, '', self.store.folder(self.p['id']))

    def test_short_approved_narration_renders_without_padding_or_mutation(self):
        from backend.services.incremental_audio import generate_incremental
        from backend.tests.test_pipeline import fake_speech
        self.setup_review()
        p = self.store.approve_storyboard(self.p['id'], self.p['revision'])
        original = copy.deepcopy(p['document'])
        def audio(script, args, **kwargs):
            if script.name == 'generate_audio.py':
                generate_incremental(Path(args[1]),Path(args[3]),self.root/'renderer/public',synthesizer=fake_speech,directed=True)
        def render(command, **kwargs):Path(command[4]).write_bytes(b'fixture')
        with patch('backend.services.editor_jobs.python_stage',side_effect=audio), patch('backend.services.editor_jobs.execute',side_effect=render),patch('backend.services.editor_jobs.node_executable',return_value='node'),patch('backend.services.scene_cache.render_cached',side_effect=cached_render_stub),patch('backend.services.scene_cache.thumbnails'):
            perform(self.jobs,p,self.store.folder(p['id']))
        self.assertEqual(self.store.load(p['id'])['document'], original)
        self.assertTrue(self.store.load(p['id'])['draft_render'])

    def test_atomic_save_retries_a_temporary_windows_file_lock(self):
        target = self.root / 'locked.json'
        original = Path.replace
        calls = []
        def replace(path, destination):
            calls.append(path)
            if len(calls) == 1:
                error = PermissionError('File is being read')
                error.winerror = 32
                raise error
            return original(path, destination)
        with patch.object(Path, 'replace', replace), patch('time.sleep'):
            write_json_atomic(target, {'complete':True})
        self.assertEqual(json.loads(target.read_text()), {'complete':True})
        self.assertEqual(len(calls), 2)


class ReviewChapterTests(unittest.TestCase):
    setUp = test_long_video.LongVideoTests.setUp
    populate = test_long_video.LongVideoTests.populate
    persist = test_long_video.LongVideoTests.persist

    def test_short_model_duration_is_preserved(self):
        from backend.services.editor_jobs import EditorJobs
        self.populate()
        self.p['source'].update(mode='prompt', automatic=True, approval_required=True, profile='draft')
        self.persist()
        jobs = EditorJobs(Path(__file__).resolve().parents[2], self.store)
        def plan(script, args, **kwargs):
            write_json_atomic(Path(args[1]), {'minutes':2, 'reason':'A brief topic'})
        original = copy.deepcopy(self.p['long_video']['chapters'])
        def draft(jobs, parent, action, uid):
            if action == 'long_outline':
                parent['long_video']['chapters'] = original
                write_json_atomic(self.store.folder(parent['id'])/'project.json', parent)
        with patch('backend.services.automatic_video.python_stage', side_effect=plan), patch('backend.services.long_video.perform', side_effect=draft):
            perform(jobs, self.p, self.store.folder(self.p['id']))
        saved = self.store.load(self.p['id'])
        self.assertEqual(saved['source']['minutes'], 2)
        self.assertIsNone(saved['long_video']['script_approved'])

    def test_automatic_drafting_stops_without_granting_approval(self):
        from backend.services.editor_jobs import EditorJobs
        self.populate()
        self.p['source'].update(automatic=True, approval_required=True, profile='draft')
        self.persist()
        jobs = EditorJobs(Path(__file__).resolve().parents[2], self.store)
        with patch('backend.services.long_video.perform') as worker:
            perform(jobs, self.p, self.store.folder(self.p['id']))
        self.assertEqual([c.args[2] for c in worker.call_args_list], ['long_scripts'])
        self.assertIsNone(self.store.load(self.p['id'])['long_video']['script_approved'])
        self.assertEqual(jobs.state['result_kind'], 'script_review')



class PlaylistTests(unittest.TestCase):
    def test_next_topic_respects_current_and_existing_episodes(self):
        w = Workspaces.new('Generative AI Visualized', 'series')
        self.assertEqual(w['topics'], GENERATIVE_AI_TOPICS)
        w['current_topic'] = 'Tokens and Context Windows'
        self.assertEqual(next_topic(w), 'Embeddings')
        self.assertEqual(next_topic(w, ['embeddings']), 'Vector Databases')
        w['current_topic'] = w['topics'][-1]
        self.assertIsNone(next_topic(w))

    def test_custom_sequences_are_validated(self):
        w = Workspaces.new('My course', 'series')
        w['topics']=['One', 'one']
        with self.assertRaises(ValueError): Workspaces.validate(w)
        w['topics']=['One'];w['current_topic']='Two'
        with self.assertRaises(ValueError): Workspaces.validate(w)
