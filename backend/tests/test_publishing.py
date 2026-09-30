import json
from pathlib import Path
import tempfile
import unittest

from backend.services.editor_store import EditorStore
from backend.services.publishing import chapters, description, hashtags, scene_seconds, sections, stamp
from backend.services.render_assets import prepare_public, with_public_dir
from backend.services.workspaces import Workspaces
from backend.tts.kokoro_tts import DEFAULT_VOICE, RECOMMENDED_VOICE


def scene(headline, duration, body='A short summary.', narration='First idea here. Then more.'):
    return {'headline': headline, 'body': body, 'narration': narration, 'duration': duration}


class PublishingTests(unittest.TestCase):
    def test_chapter_times_follow_renderer_frames_and_youtube_rules(self):
        self.assertAlmostEqual(scene_seconds({'duration': 19.171916}), 591/30)
        scenes = [scene('Text becomes input', 19.17), scene('Tokens are pieces', 19.39), scene('Context windows', 20.3)]
        rows, total = sections([(s['headline'], scene_seconds(s)) for s in scenes], {'showIntro': True, 'showOutro': True})
        marks = chapters(rows)
        self.assertEqual(marks[0], (0, 'Text becomes input'), 'the intro folds into a first chapter at 0:00')
        self.assertAlmostEqual(marks[1][0], 3 + 591/30)
        self.assertAlmostEqual(total, 3 + sum(scene_seconds(s) for s in scenes) + 5)
        self.assertEqual(stamp(marks[1][0]), '0:22')
        self.assertEqual(stamp(3725), '1:02:05')

    def test_short_sections_merge_and_too_few_chapters_are_omitted(self):
        rows, _ = sections([('A', 12), ('B', 4), ('C', 15), ('D', 11)], {})
        self.assertEqual([t for _, t in chapters(rows)], ['A', 'C', 'D'])
        rows, _ = sections([('A', 12), ('B', 12)], {})
        self.assertIsNone(chapters(rows))

    def test_description_uses_only_script_content_and_discloses_ai_voice(self):
        scenes = [scene('What tokens are', 15, 'Text becomes tokens.', 'A tokenizer splits text into tokens. It uses a vocabulary.'),
                  scene('Why counts differ', 15, 'Vocabulary decides pieces.'), scene('Context windows', 15, 'The window is finite.')]
        text, meta = description('Tokens Explained', 'Tokens and Context Windows', scenes, {'voice': 'af_heart', 'nextTopic': 'Embeddings'})
        self.assertIn('A tokenizer splits text into tokens.', text)
        self.assertNotIn('It uses a vocabulary', text.split('\n')[2])
        self.assertIn('• What tokens are - Text becomes tokens.', text)
        self.assertIn('0:00 What tokens are', text)
        self.assertIn('Next in this series: Embeddings', text)
        self.assertIn('Kokoro "Heart" voice', text)
        self.assertEqual(meta['chapters'], 3)
        short, meta = description('T', 'T', scenes[:1], {})
        self.assertNotIn('Chapters:', short)
        self.assertIn('too short', meta['chapters_note'])
        self.assertEqual(hashtags('Tokens and Context Windows'), '#TokensContextWindows #Tokens #Context #Explained #Learning')


class RenderAssetTests(unittest.TestCase):
    def test_renders_get_only_their_narration(self):
        with tempfile.TemporaryDirectory() as directory:
            root, folder = Path(directory), Path(directory)/'project'
            for name in ('a', 'b', 'c'):
                (root/'renderer/public/audio'/name).mkdir(parents=True)
                (root/'renderer/public/audio'/name/'scene-1.wav').write_bytes(b'RIFF' + name.encode())
            props = root/'props.json'
            props.write_text(json.dumps({'videoData': {'scenes': [{'audio': 'audio/a/scene-1.wav'}, {'audio': 'audio/b/scene-1.wav'}]}}))
            command = with_public_dir(root, folder, ['render', 'VisualForgeVideo', 'out.mp4', f'--props={props}'])
            public = Path(command[-1].split('=', 1)[1])
            self.assertEqual(command[:4], ['render', 'VisualForgeVideo', 'out.mp4', f'--props={props}'], 'argument positions unchanged')
            self.assertEqual(sorted(p.relative_to(public).as_posix() for p in public.rglob('*.wav')), ['audio/a/scene-1.wav', 'audio/b/scene-1.wav'])
            props.write_text(json.dumps({'videoData': {'scenes': [{'audio': 'audio/c/scene-1.wav'}]}}))
            prepare_public(root, folder, props)
            self.assertEqual([p.relative_to(public).as_posix() for p in public.rglob('*.wav')], ['audio/c/scene-1.wav'], 'stale narration is removed')
            self.assertEqual(with_public_dir(root, folder, ['bundle', 'x']), ['bundle', 'x'])


class WorkspaceVoiceTests(unittest.TestCase):
    def test_new_videos_get_natural_voice_and_bookends_old_projects_keep_theirs(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EditorStore(Path(directory)); spaces = Workspaces(store)
            old = store.create('Older lesson')
            self.assertEqual(spaces.style(old['id'])['voice'], DEFAULT_VOICE, 'adopted projects keep recorded narration')
            fresh = store.create('New lesson')
            spaces.home(None, fresh['id'], 'New lesson')
            style = spaces.style(fresh['id'])
            self.assertEqual(style['voice'], RECOMMENDED_VOICE)
            self.assertTrue(style['showIntro'] and style['showOutro'])
            w = spaces.for_project(fresh['id'])
            spaces.change(w['id'], 'save', {'voice': 'bm_george'})
            self.assertEqual(spaces.style(fresh['id'])['voice'], 'bm_george')
            with self.assertRaises(ValueError):
                spaces.change(w['id'], 'save', {'voice': 'not_a_voice'})

    def test_series_outro_names_the_next_playlist_topic(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EditorStore(Path(directory)); spaces = Workspaces(store)
            w = spaces.create({'name': 'Series', 'kind': 'series', 'topics': ['Tokens', 'Embeddings', 'RAG']})
            first = store.create('Tokens'); spaces.attach(w['id'], first['id'])
            self.assertEqual(spaces.style(first['id'])['nextTopic'], 'Embeddings')


if __name__ == '__main__':
    unittest.main()
