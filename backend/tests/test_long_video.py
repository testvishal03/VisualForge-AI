import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.services.editor_store import EditorStore, document_from_video
from backend.services.editor_jobs import EditorJobs
from backend.services.long_video import initialize, chapters_store, save, plan_key, script_key, output_key, perform
from backend.services.workspaces import Workspaces
from backend.services.director import script_to_video, build_direction
from backend.tests.test_workspaces import WATER


class LongVideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = EditorStore(Path(self.tmp.name))
        self.p = initialize(self.store, 'Water in the environment', 7)
        self.children = chapters_store(self.store, self.p)
        for index in range(4):
            child = self.children.create(f'Water chapter {index + 1}', source={'mode': 'prompt', 'minutes': 1.75})
            self.p['long_video']['chapters'].append({'id': child['id'], 'title': child['topic'], 'focus': 'Explain this specific part of the water cycle.', 'visual_goal': 'Show the physical process.', 'seconds': 105})
        self.persist()

    def persist(self):
        from backend.services.script_generator import write_json_atomic
        write_json_atomic(self.store.folder(self.p['id']) / 'project.json', self.p)

    def populate(self):
        for row in self.p['long_video']['chapters']:
            child = self.children.load(row['id'])
            video = script_to_video(child['topic'], WATER)
            self.children.save(child['id'], child['revision'], document_from_video(video, build_direction(video)))

    def test_chapter_style_preview_does_not_require_or_grant_approval(self):
        self.populate()
        jobs=EditorJobs(Path(__file__).resolve().parents[2],self.store)
        first=self.children.load(self.p['long_video']['chapters'][0]['id'])
        uid=first['document']['scenes'][0]['uid']
        with patch.object(EditorJobs,'_perform') as nested:
            perform(jobs,self.p,'long_scene_style_preview',uid)
            self.assertEqual(nested.call_args.args[1],'style_preview')
            self.assertEqual(nested.call_args.args[0]['id'],first['id'])
        self.assertIsNone(self.store.load(self.p['id'])['long_video']['script_approved'])

    def test_bookends_belong_to_first_and_last_chapters_only(self):
        from backend.services.long_video import nested_jobs
        jobs=EditorJobs(Path(__file__).resolve().parents[2],self.store)
        workspace=jobs.workspaces.for_project(self.p['id'])
        jobs.workspaces.change(workspace['id'],'save',{'show_intro':True,'show_outro':True})
        nested=nested_jobs(jobs,self.p)
        flags=[nested.workspaces.style(c['id']) for c in self.p['long_video']['chapters']]
        self.assertEqual([f['showIntro'] for f in flags],[True,False,False,False])
        self.assertEqual([f['showOutro'] for f in flags],[False,False,False,True])

    def test_limits_and_exact_duration(self):
        for minutes in [6, 31, 7.0, True]:
            with self.assertRaises(ValueError):
                initialize(self.store, 'Topic', minutes)
        rows = copy.deepcopy(self.p['long_video']['chapters'])
        rows[0]['seconds'] += 1
        with self.assertRaisesRegex(ValueError, 'add up'):
            save(self.store, self.p, {'chapters': rows})

    def test_approvals_and_edits_invalidate_only_changed_chapter(self):
        self.populate()
        self.p = save(self.store, self.p, {'approve_outline': True, 'approve_script': True})
        self.assertEqual(self.p['long_video']['script_approved'], script_key(self.store, self.p))
        rows = copy.deepcopy(self.p['long_video']['chapters'])
        rows[0]['focus'] = 'Explain cloud formation in detail.'
        changed = save(self.store, self.p, {'chapters': rows})
        self.assertIsNone(changed['long_video']['script_approved'])
        self.assertIsNone(changed['long_video']['outline_approved'])
        self.assertIsNone(self.children.load(rows[0]['id'])['document'])
        self.assertIsNotNone(self.children.load(rows[1]['id'])['document'])

    def test_invalid_edit_is_not_published(self):
        self.populate()
        first = self.p['long_video']['chapters'][0]['id']
        second = self.p['long_video']['chapters'][1]['id']
        before = self.children.load(first)
        with self.assertRaises(ValueError):
            save(self.store, self.p, {'scripts': {first: WATER.replace('Water', 'Fresh water', 1), second: 'too short'}})
        self.assertEqual(self.children.load(first), before)

    def test_render_requires_current_script_approval(self):
        self.populate()
        jobs = EditorJobs(Path(__file__).resolve().parents[2], self.store)
        with self.assertRaisesRegex(ValueError, 'approve the scripts'):
            perform(jobs, self.p, 'long_render_draft', None)
        self.p = save(self.store, self.p, {'approve_script': True})
        before = output_key(jobs, self.p, 'draft')
        cid = self.p['long_video']['chapters'][0]['id']
        changed = save(self.store, self.p, {'scripts': {cid: WATER.replace('Water', 'Fresh water', 1)}})
        self.assertNotEqual(before, output_key(jobs, changed, 'draft'))

    def test_duplicate_is_independent_and_requires_review(self):
        self.populate()
        spaces = Workspaces(self.store)
        space = spaces.for_project(self.p['id'])
        duplicate = spaces.change(space['id'], 'duplicate', {})
        copied = self.store.load(duplicate['episodes'][0])
        self.assertIsNone(copied['long_video']['script_approved'])
        self.assertNotEqual(copied['long_video']['chapters'][0]['id'], self.p['long_video']['chapters'][0]['id'])
        self.assertIsNotNone(chapters_store(self.store, copied).load(copied['long_video']['chapters'][0]['id'])['document'])

    def test_present_does_not_adopt_chapters_as_workspaces(self):
        jobs = EditorJobs(Path(__file__).resolve().parents[2], self.store)
        result = jobs.present(self.p)
        self.assertEqual(len(result['chapter_details']), 4)
        self.assertEqual(len(jobs.workspaces.list()), 1)

    def test_completed_scripts_are_skipped_on_retry(self):
        self.populate()
        self.p = save(self.store, self.p, {'approve_outline': True})
        jobs = EditorJobs(Path(__file__).resolve().parents[2], self.store)
        with patch('backend.services.process_runner.python_stage') as stage:
            perform(jobs, self.p, 'long_scripts', None)
            stage.assert_not_called()

    def test_failed_approval_does_not_publish_outline_edits(self):
        self.populate()
        rows = copy.deepcopy(self.p['long_video']['chapters'])
        rows[0]['focus'] = 'A new focus that needs a new script.'
        before = self.children.load(rows[0]['id'])
        with self.assertRaisesRegex(ValueError, 'Every chapter'):
            save(self.store, self.p, {'chapters': rows, 'approve_script': True})
        self.assertEqual(self.children.load(rows[0]['id']), before)
        self.assertEqual(self.store.load(self.p['id']), self.p)

    def test_duration_edit_updates_only_affected_chapter_targets(self):
        rows = copy.deepcopy(self.p['long_video']['chapters'])
        rows[0]['seconds'], rows[1]['seconds'] = 90, 120
        save(self.store, self.p, {'chapters': rows})
        self.assertEqual(self.children.load(rows[0]['id'])['source']['minutes'], 1.5)
        self.assertEqual(self.children.load(rows[1]['id'])['source']['minutes'], 2)

    def test_worker_reuses_only_validated_cache(self):
        from backend.scripts.long_video_worker import ask
        from unittest.mock import Mock
        engine = Mock(cache_identity='test')
        engine.generate_json.side_effect = ['{"value":0}', '{"value":1}']
        def validate(data):
            if data['value'] != 1:
                raise ValueError('Use one')
            return data
        cache = Path(self.tmp.name) / 'cache'
        self.assertEqual(ask(engine, 'prompt', {}, validate, cache), {'value': 1})
        self.assertEqual(ask(engine, 'prompt', {}, validate, cache), {'value': 1})
        self.assertEqual(engine.generate_json.call_count, 2)
        self.assertIn('Use one', engine.generate_json.call_args.args[0])

    def test_semantic_replanning_preserves_scripts_and_requires_new_review(self):
        from backend.schemas.video_schema import VideoScript
        self.populate()
        self.p = save(self.store, self.p, {'approve_script': True})
        before = [self.children.load(c['id'])['document'] for c in self.p['long_video']['chapters']]
        jobs = EditorJobs(Path(__file__).resolve().parents[2], self.store)
        def stage(script, args, **kwargs):
            self.assertEqual(script.name, 'plan_visuals.py')
            plan = build_direction(VideoScript.model_validate_json(Path(args[0]).read_text()))
            for row in plan['scenes']: row['planned'] = True
            Path(args[1]).write_text(json.dumps(plan))
        with patch('backend.services.process_runner.python_stage', side_effect=stage):
            perform(jobs, self.p, 'long_visuals', None)
        self.assertIsNone(self.store.load(self.p['id'])['long_video']['script_approved'])
        for chapter, original in zip(self.p['long_video']['chapters'], before):
            updated = self.children.load(chapter['id'])['document']
            self.assertEqual([s['narration'] for s in updated['scenes']], [s['narration'] for s in original['scenes']])
            self.assertEqual([s['uid'] for s in updated['scenes']], [s['uid'] for s in original['scenes']])
            self.assertTrue(all(s['visual']['planned'] for s in updated['scenes']))

    def test_storyboard_document_edit_invalidates_approval_only_for_changed_chapter(self):
        self.populate()
        self.p=save(self.store,self.p,{'approve_script':True})
        first,second=[c['id'] for c in self.p['long_video']['chapters'][:2]]
        untouched=self.children.load(second)
        doc=copy.deepcopy(self.children.load(first)['document'])
        doc['scenes'][0]['visual']['motion']='focus'
        updated=save(self.store,self.p,{'documents':{first:doc}})
        self.assertIsNone(updated['long_video']['script_approved'])
        self.assertEqual(self.children.load(second),untouched)
        self.assertEqual(self.children.load(first)['document'],doc)

    def test_invalid_storyboard_batch_does_not_publish_valid_sibling_edits(self):
        self.populate()
        first,second=[c['id'] for c in self.p['long_video']['chapters'][:2]]
        before=self.children.load(first)
        good=copy.deepcopy(before['document']);good['scenes'][0]['visual']['motion']='focus'
        bad=copy.deepcopy(self.children.load(second)['document']);bad['scenes'][0]['visual']['motion']='unknown'
        with self.assertRaises(ValueError):save(self.store,self.p,{'documents':{first:good,second:bad}})
        self.assertEqual(self.children.load(first),before)


if __name__ == '__main__':
    unittest.main()
