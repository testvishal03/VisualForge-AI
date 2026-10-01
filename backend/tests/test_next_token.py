import math
from pathlib import Path
import tempfile
import unittest

from backend.services.next_token import measure, read, shown, validate


class FakeEngine:
    """Answers like llama.cpp's /tokenize and /completion (pre-sampling top_logprobs)."""
    def __init__(self, rows):
        self.rows, self.calls = rows, 0

    def _load(self):
        pass

    def _request(self, route, payload, timeout=10):
        self.calls += 1
        if route == '/tokenize':
            return {'tokens': list(range(len(payload['content'].split())))}
        assert payload['post_sampling_probs'] is False and payload['n_probs'] == 5
        return {'completion_probabilities': [{'top_logprobs': [{'token': t, 'logprob': math.log(p)} for t, p in self.rows]}]}


MODEL = {'model': 'qwen.gguf', 'sha256': 'abc'}


class NextTokenTests(unittest.TestCase):
    def test_measures_caches_and_shows_visible_tokens(self):
        engine = FakeEngine([(' mat', .666), (' windows', .134), ('\n', .05), (' sofa', .035), (' roof', .031)])
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            result = measure('the cat sat on the', engine, MODEL, cache)
            self.assertAlmostEqual(result['candidates'][0]['prob'], .666, places=5)
            tokens, probs = shown(result)
            self.assertEqual(tokens, ['mat', 'windows', 'sofa'], 'whitespace-only tokens are not shown as words')
            self.assertEqual(len(probs), 3)
            calls = engine.calls
            self.assertEqual(measure('the cat sat on the', engine, MODEL, cache), result)
            self.assertEqual(engine.calls, calls, 'a cached measurement does not query the model again')
            self.assertIsNone(read('the cat sat on the', {**MODEL, 'sha256': 'other'}, cache), 'another model file is not reused')

    def test_invalid_measurements_are_rejected(self):
        good = {'mode': 'next_token', 'candidates': [{'token': ' a', 'prob': .5}, {'token': ' b', 'prob': .2}]}
        validate(good)
        for bad in ({**good, 'candidates': [{'token': ' a', 'prob': .2}, {'token': ' b', 'prob': .5}]},
                    {**good, 'candidates': [{'token': ' a', 'prob': 1.5}]}, {**good, 'mode': 'other'}, {**good, 'candidates': []}):
            with self.assertRaises(ValueError):
                validate(bad)


if __name__ == '__main__':
    unittest.main()
