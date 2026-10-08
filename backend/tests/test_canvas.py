import unittest
from pathlib import Path

from backend.services.canvas import CanvasError, extract, timed, validate

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = '''Guardrails keep AI safe. They sit around the model.

```visual
{"elements": [
 {"id": "model", "type": "box", "x": 960, "y": 400, "text": "AI MODEL", "color": "yellow", "at": 0},
 {"id": "risk", "type": "box", "x": 500, "y": 700, "text": "Made-up facts", "color": "red", "at": 1, "delay": 0.2},
 {"type": "arrow", "from": "model", "to": "risk", "color": "red", "at": 1, "word": "around"}
]}
```

A plain paragraph without its own visual follows here.'''


class ExtractTests(unittest.TestCase):
    def test_blocks_attach_to_the_paragraph_before_them_and_are_not_narrated(self):
        narration, specs, errors = extract(SCRIPT)
        self.assertEqual(errors, [])
        self.assertNotIn('```', narration)
        self.assertNotIn('{', narration)
        self.assertEqual(len(narration.split('\n\n')), 2)
        self.assertEqual(len(specs[0]['elements']), 3)
        self.assertIsNone(specs[1])

    def test_scripts_without_blocks_are_unchanged(self):
        self.assertEqual(extract('Just narration.\n\nMore narration.'), ('Just narration.\n\nMore narration.', [], []))

    def test_broken_json_is_reported_with_its_scene(self):
        _, _, errors = extract('First paragraph here.\n\n```visual\n{"elements": [\n```')
        self.assertEqual(errors[0][0], 1)
        self.assertIn('not valid JSON', errors[0][1])


class ValidateTests(unittest.TestCase):
    sentences = ['Guardrails keep AI safe.', 'They sit around the model.']

    def spec(self, **change):
        element = {'type': 'box', 'x': 960, 'y': 400, 'text': 'AI MODEL', 'at': 0, **change}
        return {'elements': [element]}

    def test_problems_name_the_element_and_the_rule(self):
        for change, message in [({'color': 'gold'}, 'color'), ({'x': 5000}, 'x'), ({'type': 'video'}, 'type'),
                                ({'speed': 3}, 'unknown speed'), ({'text': 'x' * 200}, 'text')]:
            with self.assertRaisesRegex(CanvasError, message):
                validate(self.spec(**change), self.sentences)
        with self.assertRaisesRegex(CanvasError, 'unknown element "nowhere"'):
            validate({'elements': [{'type': 'arrow', 'from': 'nowhere', 'to': [10, 10]}]}, self.sentences)

    def test_a_cue_past_the_last_sentence_waits_for_the_last_sentence(self):
        self.assertEqual(validate(self.spec(at=5), self.sentences)['elements'][0]['at'], 1)


class TimingTests(unittest.TestCase):
    def test_elements_land_on_sentences_delays_and_spoken_words(self):
        _, specs, _ = extract(SCRIPT)
        beats = [{'text': 'Guardrails keep AI safe.', 'start': 0.0, 'end': 1.6, 'words': []},
                 {'text': 'They sit around the model.', 'start': 1.9, 'end': 3.6,
                  'words': [{'text': 'They', 'start': 1.9, 'end': 2.1}, {'text': 'sit', 'start': 2.1, 'end': 2.4},
                            {'text': 'around', 'start': 2.4, 'end': 2.8}, {'text': 'the', 'start': 2.8, 'end': 2.9},
                            {'text': 'model.', 'start': 2.9, 'end': 3.6}]}]
        result = timed(validate(specs[0], [b['text'] for b in beats]), beats)
        times = [e['t'] for e in result['elements']]
        self.assertEqual(times[0], 0.0)
        self.assertAlmostEqual(times[1], 2.1, places=3)       # sentence 1 start + 0.2 s
        self.assertLess(times[2], 2.4)                        # just before "around" is spoken
        self.assertGreater(times[2], 2.0)
        self.assertNotIn('at', result['elements'][0])


class ExampleTests(unittest.TestCase):
    def test_the_bundled_example_is_valid_for_every_scene(self):
        from backend.services.director import script_to_video, sentences
        narration, specs, errors = extract((ROOT / 'data/examples/tool-calling-visual.txt').read_text(encoding='utf-8'))
        self.assertEqual(errors, [])
        video = script_to_video('Tool Calling', narration, keep_paragraphs=True)
        self.assertEqual(len(video.scenes), len(specs))
        for scene, spec in zip(video.scenes, specs):
            validate(spec, sentences(scene.narration))


if __name__ == '__main__':
    unittest.main()
