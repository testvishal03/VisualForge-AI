import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.services.music import IN_GAPS, UNDER_SPEECH, bed, mix

RATE = 24000


def speech(seconds):
    """Voice-like noise at the levelled narration loudness (RMS 0.1)."""
    rng = np.random.default_rng(1)
    return rng.normal(0, .1, round(seconds * RATE)).clip(-.9, .9)


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)))


class MusicBedTests(unittest.TestCase):
    def test_bed_is_deterministic(self):
        self.assertTrue(np.array_equal(bed(10, RATE), bed(10, RATE)))
        self.assertAlmostEqual(rms(bed(10, RATE)), 1, places=6)

    def test_bed_ducks_under_speech_and_rises_in_long_pauses(self):
        voice = np.concatenate([np.zeros(6 * RATE), speech(8), np.zeros(6 * RATE)])
        music = mix(voice, RATE) - voice
        under = rms(music[8 * RATE:13 * RATE])
        pause = rms(music[16 * RATE:17 * RATE])
        self.assertAlmostEqual(under, UNDER_SPEECH, delta=UNDER_SPEECH * .35)
        self.assertGreater(pause, under * 1.6)
        self.assertLess(pause, IN_GAPS * 1.4)

    def test_short_sentence_pauses_stay_ducked(self):
        voice = np.concatenate([speech(4), np.zeros(round(.28 * RATE)), speech(4)])
        music = mix(voice, RATE) - voice
        gap = music[4 * RATE:4 * RATE + round(.28 * RATE)]
        self.assertLess(rms(gap), UNDER_SPEECH * 1.6)

    def test_narration_stays_dominant_and_track_fades(self):
        voice = np.concatenate([np.zeros(3 * RATE), speech(20), np.zeros(5 * RATE)])
        out = mix(voice, RATE)
        self.assertGreater(np.corrcoef(voice, out)[0, 1], .99, 'the render check needs > 0.98 per scene')
        self.assertLess(abs(out[0]), 1e-6)
        self.assertLess(abs(out[-1]), 1e-6)
        self.assertLessEqual(np.abs(out).max(), 1)


class MusicSettingTests(unittest.TestCase):
    def test_music_is_off_for_new_workspaces_and_reaches_the_render_style_when_on(self):
        from backend.services.editor_store import EditorStore
        from backend.services.workspaces import Workspaces
        with tempfile.TemporaryDirectory() as d:
            spaces = Workspaces(EditorStore(Path(d)))
            plain = spaces.create({'name': 'Plain', 'kind': 'single'})
            self.assertFalse(plain['music'])
            with self.assertRaises(ValueError):
                spaces.create({'name': 'Bad', 'kind': 'single', 'music': 'yes'})
            scored = spaces.create({'name': 'Scored', 'kind': 'single', 'music': True})
            self.assertTrue(scored['music'])


if __name__ == '__main__':
    unittest.main()
