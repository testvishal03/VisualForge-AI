import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.services import embeddings
from backend.services.embeddings import layout, measure, nearest_links, read, validate


class FakeEmbedder:
    """Two tight pairs and two loners, as unit vectors."""
    calls = 0
    VECTORS = {'Cat': [1, .1, 0, 0], 'Dog': [1, .2, 0, 0], 'King': [0, 0, 1, .1], 'Queen': [0, 0, 1, .2],
               'Banana': [.3, 1, 0, -.6], 'Database': [0, -.4, .3, 1]}

    def embed(self, texts):
        FakeEmbedder.calls += 1
        v = np.array([self.VECTORS[t] for t in texts], dtype=float)
        return v / np.linalg.norm(v, axis=1, keepdims=True)


class EmbeddingMapTests(unittest.TestCase):
    labels = ['Cat', 'Dog', 'King', 'Queen', 'Banana', 'Database']

    def test_layout_keeps_similar_points_closer_and_shares_one_scale(self):
        with tempfile.TemporaryDirectory() as d:
            result = measure(self.labels, FakeEmbedder(), Path(d))
        xy = np.array(result['xy'])
        dist = lambda a, b: np.hypot(*(xy[a] - xy[b]))
        self.assertLess(dist(0, 1), dist(0, 2))
        self.assertLess(dist(2, 3), dist(2, 4))
        self.assertAlmostEqual(max(np.ptp(xy[:, 0]), np.ptp(xy[:, 1])), 1, places=3)
        self.assertGreaterEqual(np.ptp(xy[:, 0]), np.ptp(xy[:, 1]), 'the widest spread runs across the screen')
        self.assertEqual(layout(result['similarity']), result['xy'], 'the same measurement always draws the same way')

    def test_links_join_each_point_to_its_nearest_neighbour_once(self):
        with tempfile.TemporaryDirectory() as d:
            result = measure(self.labels, FakeEmbedder(), Path(d))
        pairs = {(l['a'], l['b']) for l in nearest_links(result['similarity'])}
        self.assertIn((0, 1), pairs)
        self.assertIn((2, 3), pairs)
        self.assertEqual(len(pairs), len(nearest_links(result['similarity'])))

    def test_measurements_are_cached_per_labels_and_model(self):
        FakeEmbedder.calls = 0
        with tempfile.TemporaryDirectory() as d:
            first = measure(self.labels, FakeEmbedder(), Path(d))
            self.assertEqual(measure(self.labels, FakeEmbedder(), Path(d)), first)
            self.assertEqual(FakeEmbedder.calls, 1)
            self.assertIsNone(read(self.labels[:4], Path(d)))
            self.assertIsNone(read(self.labels, Path(d), model='another-model'))
        for bad in ({**first, 'labels': self.labels[:3]}, {**first, 'xy': [[2, 0]] * 6},
                    {**first, 'similarity': [[0.5] * 6] * 6}):
            with self.assertRaises(ValueError):
                validate(bad, self.labels)

    @unittest.skipUnless(embeddings.installed(), 'embedding model not installed')
    def test_installed_model_puts_narrated_pairs_together(self):
        model = embeddings.EmbeddingModel()
        try:
            with tempfile.TemporaryDirectory() as d:
                result = measure(self.labels, model, Path(d))
        finally:
            model.close()
        pairs = {(l['a'], l['b']) for l in nearest_links(result['similarity'])}
        self.assertTrue({(0, 1), (2, 3)} <= pairs, result['similarity'])


if __name__ == '__main__':
    unittest.main()
