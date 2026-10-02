import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from backend.schemas.video_schema import Scene, VideoScript
from backend.services.visual_quality import score, weak_label, weak_scenes


def row(narration, kind='explanation'):
    return {'headline': 'Scene', 'body': 'Body text.', 'narration': narration, 'visual': {'kind': kind, 'items': []}}


class WeakLabelTests(unittest.TestCase):
    def test_vague_and_verb_like_labels_are_weak(self):
        for label in ('built', 'simplest', 'smarter trick', 'tiny bit', "embeddings don't", 'designed around', 'Choosing one'):
            self.assertTrue(weak_label(label), label)
        for label in ('vector database', 'HNSW', 'search engine', 'cluster centers', 'Metadata'):
            self.assertFalse(weak_label(label), label)

    def test_weakest_scenes_come_first_and_good_or_drawn_scenes_are_never_chosen(self):
        weak = row('So vector databases use a smarter trick called Approximate Nearest Neighbor search, or ANN. '
                   'Instead of checking everything, ANN checks only the most promising areas. It trades a tiny bit of accuracy for massive speed.')
        fine = row('A vector database stores embeddings and metadata. The index groups similar vectors into clusters.')
        title = row('Welcome to this lesson about vector databases and how they search.', kind='title')
        drawn = row('Now a user asks a question. The question is converted into an embedding. The vector database searches '
                    'for the closest chunks. Those chunks are retrieved and given to the language model, which writes the answer.')
        document = {'scenes': [fine, weak, title, drawn]}
        # The rule labels each scene would show, fixed so this tests the ranking, not the parser.
        shown = {weak['narration']: ['vector databases', 'smarter trick', 'tiny bit'], fine['narration']: ['vector database', 'similar vectors']}
        objects = lambda scene, visual: {'objects': [{'label': l} for l in shown.get(scene['narration'], ['lesson'])]}
        with patch('backend.services.choreography.compile_scene', objects):
            self.assertGreater(score(weak), score(fine))
            self.assertEqual(score(title), 0)
            chosen = weak_scenes(document, 5)
        self.assertEqual(chosen[0], 2)
        self.assertNotIn(3, chosen)
        self.assertNotIn(4, chosen, 'a scene drawn by an explainer keeps its explainer')
        self.assertEqual(weak_scenes(document, 0), [])


class LimitedPlanningTests(unittest.TestCase):
    def setUp(self):
        # Load the grammar parser outside the timed budgets below.
        from backend.services.key_terms import parser
        parser()

    def video(self, count):
        scenes = [Scene(id=n, headline=f'Topic {n}', body='Short body.', narration=f'The search index groups similar vectors for topic {n}. '
                        f'Each cluster center summarises nearby vectors in group {n}.') for n in range(1, count + 1)]
        return VideoScript(title='Indexes', topic='Indexes', scenes=scenes)

    def engine(self):
        calls = []
        def generate_json(prompt, schema, max_new_tokens):
            calls.append(prompt)
            return json.dumps({'kind': 'explanation', 'icon': 'rocket', 'elements': [], 'layout': 'auto', 'treatment': 'build', 'concepts': []})
        return SimpleNamespace(generate_json=generate_json, cache_identity='fake'), calls

    # The fake model's plans (icon "rocket") count as clearer unless a test says otherwise.
    clearer = staticmethod(lambda scene, visual: 0 if visual.get('icon') == 'rocket' else 1)

    def test_only_selected_scenes_reach_the_model(self):
        from unittest.mock import patch
        from backend.services.semantic_director import plan_video
        engine, calls = self.engine()
        with tempfile.TemporaryDirectory() as d, patch('backend.services.visual_quality.label_score', self.clearer):
            plan = plan_video(self.video(4), engine=engine, cache=Path(d), only=[4, 2])
        self.assertEqual(len(calls), 2)
        self.assertIn('topic 4', calls[0], 'selected scenes are planned worst-first, in the order given')
        self.assertIn('topic 2', calls[1])
        self.assertEqual(len(plan['scenes']), 4)
        self.assertEqual(plan['model_planned'], [2, 4])
        self.assertEqual(plan['warnings'], [])

    def test_a_tight_budget_plans_the_most_important_scene_first(self):
        import time
        from backend.services.semantic_director import plan_video
        engine, calls = self.engine()
        slow = engine.generate_json
        engine.generate_json = lambda *a, **k: (time.sleep(.6), slow(*a, **k))[1]
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d, patch('backend.services.visual_quality.label_score', self.clearer):
            plan = plan_video(self.video(3), engine=engine, cache=Path(d), only=[3, 1], budget_seconds=.5)
        self.assertEqual(plan['model_planned'], [3])
        self.assertIn('topic 3', calls[0])

    def test_an_ai_plan_that_is_not_clearer_is_discarded(self):
        from unittest.mock import patch
        from backend.services.semantic_director import plan_video
        engine, calls = self.engine()
        with tempfile.TemporaryDirectory() as d, patch('backend.services.visual_quality.label_score', lambda scene, visual: 1):
            plan = plan_video(self.video(3), engine=engine, cache=Path(d), only=[2])
        self.assertEqual(len(calls), 1)
        self.assertEqual(plan['model_planned'], [])
        self.assertNotEqual(plan['scenes'][1].get('icon'), 'rocket')

    def test_spent_budget_stops_new_scenes_after_the_current_one(self):
        import time
        from backend.services.semantic_director import plan_video
        engine, calls = self.engine()
        slow = engine.generate_json
        engine.generate_json = lambda *a, **k: (time.sleep(.6), slow(*a, **k))[1]
        with tempfile.TemporaryDirectory() as d:
            plan = plan_video(self.video(3), engine=engine, cache=Path(d), budget_seconds=.5)
        self.assertEqual(len(calls), 1, 'the scene started within the budget finishes; later ones are not started')
        self.assertTrue(all(r['planned'] for r in plan['scenes']))


class LongVideoMergeTests(unittest.TestCase):
    def test_only_the_planned_scenes_change(self):
        from unittest.mock import patch
        from backend.services.editor_jobs import EditorJobs
        from backend.services.editor_store import EditorStore, document_from_video
        from backend.services.director import build_direction, script_to_video
        paragraphs = [f'Topic {n} explains how a search index groups vectors so lookups stay fast for every query in group {n}.' for n in range(18)]
        # A paragraph whose rule labels are weak under either label extractor ("recap", vague "ones").
        paragraphs[5] = ("Let's recap what we built. The simplest ones work, the bigger ones scale, and the tiny ones stay cheap "
                         'whenever you choose between them for a new project.')
        video = script_to_video('Indexes', '\n\n'.join(paragraphs))
        with tempfile.TemporaryDirectory() as d:
            store = EditorStore(Path(d) / 'projects')
            jobs = EditorJobs(Path(__file__).resolve().parents[2], store)
            try:
                project = store.create(video.topic, document_from_video(video, build_direction(video)), source={'mode': 'script', 'review_first': True, 'profile': 'draft'})
                before = project['document']['scenes']
                if len(before) <= 16:
                    self.skipTest('script grouped into too few scenes')
                weak = weak_scenes(project['document'], 7)
                def stage(script, args, **kwargs):
                    output = Path(args[1])
                    scenes = [dict(s['visual'], id=n, icon='battery', planned=True) for n, s in enumerate(before, 1)]
                    # The model planned every selected scene except the last, which failed.
                    output.write_text(json.dumps({'scenes': scenes, 'warnings': [], 'model_planned': weak[:-1]}), encoding='utf-8')
                with patch('backend.services.editor_jobs.python_stage', side_effect=stage):
                    jobs._perform(store.load(project['id']), 'generate', None, '', store.folder(project['id']))
                after = store.load(project['id'])['document']['scenes']
            finally:
                jobs.close()
        self.assertTrue(weak)
        for n, (old, new) in enumerate(zip(before, after), 1):
            self.assertTrue(new['visual']['planned'])
            if n in weak[:-1]:
                self.assertEqual(new['visual']['icon'], 'battery')
            else:
                self.assertNotEqual(new['visual'].get('icon'), 'battery')
                self.assertEqual({k: v for k, v in new['visual'].items() if k != 'planned'}, {k: v for k, v in old['visual'].items() if k != 'planned'})


if __name__ == '__main__':
    unittest.main()
