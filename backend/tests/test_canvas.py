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

    def test_blocks_copied_from_a_chat_window_without_fences_still_work(self):
        copied = '\n'.join(['Guardrails keep AI safe. They sit around the model.', '', 'visual', '{"elements": [',
                            '{"type": "box", "x": 960, "y": 400, "text": "Model", "at": 0}', ']}', '', 'The next paragraph has no visual.'])
        narration, specs, errors = extract(copied)
        self.assertEqual(errors, [])
        self.assertNotIn('{', narration)
        self.assertNotIn('visual', narration.split('\n\n')[0])
        self.assertEqual(specs[0]['elements'][0]['text'], 'Model')
        self.assertIsNone(specs[1])
        # The word "visual" inside narration is left alone.
        self.assertEqual(extract('A visual\nexplanation of data.')[1], [])

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



class MachineLearningVisualTests(unittest.TestCase):
    plot = {'id': 'p', 'type': 'plot', 'x': 960, 'y': 500, 'w': 1000, 'h': 500, 'xRange': [0, 10], 'yRange': [-50, 100]}

    def test_formula_curves_become_points_across_the_plot(self):
        spec = {'elements': [self.plot, {'type': 'curve', 'plot': 'p', 'shape': {'type': 'line', 'slope': 2, 'intercept': 1}},
                             {'type': 'curve', 'plot': 'p', 'shape': {'type': 'sigmoid', 'k': 2, 'x0': 5}}]}
        line, sigmoid = validate(spec, ['One.'])['elements'][1:]
        self.assertEqual(line['data'][0], [0, 1])
        self.assertEqual(line['data'][-1], [10, 21])
        self.assertAlmostEqual(sigmoid['data'][len(sigmoid['data']) // 2][1], .5, delta=.05)

    def test_plotted_elements_use_data_coordinates_and_must_name_a_plot(self):
        spec = {'elements': [self.plot, {'type': 'dot', 'plot': 'p', 'x': 4, 'y': -30}]}
        self.assertEqual(validate(spec, ['One.'])['elements'][1]['y'], -30)
        for bad, message in [({'type': 'points', 'plot': 'q', 'data': [[1, 2], [3, 4]]}, 'plot "q"'),
                             ({'type': 'curve', 'plot': 'p', 'data': [[1, 2], [3, 4]], 'start': [[0, 0], [1, 1], [2, 2]]}, 'as many points'),
                             ({'type': 'table', 'x': 10, 'y': 10, 'rows': [['a', 'b']], 'highlight': [[2, 0, 'red']]}, 'outside the table'),
                             ({'type': 'network', 'x': 960, 'y': 500, 'w': 600, 'h': 300, 'layers': [3, 40]}, 'neuron counts')]:
            with self.assertRaisesRegex(CanvasError, message):
                validate({'elements': [self.plot, bad]}, ['One.'])

    def test_the_linear_regression_example_is_valid(self):
        from backend.services.director import script_to_video, sentences
        narration, specs, errors = extract((ROOT / 'data/examples/ml-linear-regression-visual.txt').read_text(encoding='utf-8'))
        self.assertEqual(errors, [])
        video = script_to_video('Linear Regression', narration, keep_paragraphs=True)
        for scene, spec in zip(video.scenes, specs):
            validate(spec, sentences(scene.narration))



class LayoutCheckTests(unittest.TestCase):
    def issues(self, *elements):
        from backend.services.canvas import layout_issues
        return layout_issues(validate({'elements': list(elements)}, ['One.', 'Two.']))

    def test_clashes_off_frame_and_caption_area_are_reported(self):
        a = {'type': 'box', 'x': 600, 'y': 500, 'w': 400, 'h': 150, 'text': 'Data', 'at': 0}
        b = {'type': 'box', 'x': 700, 'y': 520, 'w': 400, 'h': 150, 'text': 'Model', 'at': 1}
        self.assertTrue(any('overlaps' in m for m in self.issues(a, b)))
        self.assertTrue(any('caption' in m for m in self.issues({**a, 'y': 900})))
        self.assertTrue(any('edge' in m for m in self.issues({**a, 'x': 1850})))

    def test_intended_overlays_are_not_reported(self):
        box = {'id': 'm', 'type': 'box', 'x': 600, 'y': 500, 'w': 400, 'h': 150, 'text': 'Model', 'at': 0}
        later = {**box, 'id': 'n', 'at': 1, 'fill': 'tint'}             # the same box redrawn to recolour it
        badge = {'type': 'check', 'x': 790, 'y': 430, 'at': 1}           # a badge on its corner
        gone = {'type': 'pill', 'x': 600, 'y': 500, 'text': 'Old', 'at': 0, 'out': {'at': 1}}
        self.assertEqual(self.issues(box, later, badge), [])
        self.assertEqual(self.issues({**box, 'at': 1}, gone), [], 'one leaves before the other arrives')
        self.assertEqual(self.issues({'type': 'text', 'x': 960, 'y': 300, 'text': 'What is Machine Learning?', 'size': 'title', 'at': 0}), [],
                         'oversized text is drawn smaller to fit')


class EpisodePromptTests(unittest.TestCase):
    def test_the_prompt_places_the_episode_in_its_playlist(self):
        from backend.services.claude_prompt import episode_prompt
        from backend.services.workspaces import MACHINE_LEARNING_TOPICS as topics
        prompt = episode_prompt('Linear Regression', 4, 'Machine Learning', topics)
        self.assertIn('about: Linear Regression', prompt.splitlines()[0])
        self.assertIn('episode 9 of 20', prompt)
        self.assertIn('The next episode is "Logistic Regression"', prompt)
        self.assertIn('Overfitting and Underfitting', prompt)
        self.assertIn('"type": "plot"', prompt.replace('plot: {"id"', '"type": "plot"'))
        first = episode_prompt('What is Machine Learning?', 4, 'Machine Learning', topics)
        self.assertIn('first episode', first)
        self.assertNotIn('SERIES CONTEXT', episode_prompt('Anything', 3))


if __name__ == '__main__':
    unittest.main()
