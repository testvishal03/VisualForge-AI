import json
from pathlib import Path
import tempfile
import unittest

from backend.services.incremental_audio import cached_speech, generate_incremental
from backend.tests.test_pipeline import fake_speech
from backend.utils.word_timing import align_words, estimate_words, offset_words, phoneme_words, validate_words


def rows(phonemes, step=0.1):
    """Phoneme timing rows spaced evenly, as Kokoro reports them."""
    return [(p, i*step, (i+1)*step) for i, p in enumerate(phonemes)]


# Stand-in for espeak: one spoken word per letter group, numbers expand to two words.
def phonemize(word):
    return 'twɛnti fˈɔːɹ' if word.strip('.,') == '24' else word.lower()


class WordTimingTests(unittest.TestCase):
    def test_phoneme_groups_ignore_punctuation_for_word_ends(self):
        groups = phoneme_words(rows('ab, cd.'))
        self.assertEqual(len(groups), 2)
        self.assertAlmostEqual(groups[0][-1][2], 0.2)  # comma excluded from the first word
        self.assertAlmostEqual(groups[1][-1][2], 0.6)  # full stop excluded from the second

    def test_words_espeak_joins_share_their_group_by_sound(self):
        # espeak speaks "on the" as one group "ɔnðə" and "does not" as "dʌznˌɑːt".
        alone = {'on': 'ˈɔn', 'the': 'ðə', 'does': 'dˈʌz', 'not': 'nˈɑːt'}
        words, measured = align_words('on the cd does not', rows('ɔnðə cd dʌznˌɑːt'), lambda w: alone.get(w, w))
        self.assertTrue(measured)
        spans = [(w['text'], round(w['start'], 2), round(w['end'], 2)) for w in words]
        self.assertEqual(spans, [('on', 0, .2), ('the', .2, .4), ('cd', .5, .7), ('does', .8, 1.1), ('not', 1.1, 1.6)])

    def test_reduced_joins_match_how_espeak_speaks_the_phrase(self):
        # Alone "for" is "fɔːɹ", but "for a request" is spoken "fɚɹɚ ɹᵻkwˈɛst".
        speech = {'for': 'fˈɔːɹ', 'a': 'ɐ', 'for a': 'fɚɹɚ', 'for a request.': 'fɚɹɚ ɹᵻkwˈɛst.'}
        words, measured = align_words('for a request.', rows('fɚɹɚ ɹᵻkwˈɛst.'), lambda w: speech.get(w, w))
        self.assertTrue(measured)
        self.assertEqual([w['text'] for w in words], ['for', 'a', 'request.'])
        self.assertLess(words[0]['end'], words[1]['end'])
        _, measured = align_words('for a request.', rows('fɚɹɚ ɹᵻkwˈɛst.'), lambda w: {'for': 'fˈɔːɹ', 'a': 'ɐ'}.get(w, w))
        self.assertFalse(measured)  # no exact sound evidence: estimate rather than guess

    def test_alignment_maps_expanded_numbers_to_one_text_word(self):
        timings = rows('ab twɛnti fˈɔːɹ cd.')
        words, measured = align_words('ab 24 cd.', timings, phonemize)
        self.assertTrue(measured)
        self.assertEqual([w['text'] for w in words], ['ab', '24', 'cd.'])
        self.assertAlmostEqual(words[1]['start'], 0.3)
        self.assertAlmostEqual(words[1]['end'], 1.5)
        self.assertAlmostEqual(words[2]['start'], 1.6)

    def test_silent_tokens_and_mismatches_stay_complete(self):
        words, measured = align_words('ab — cd.', rows('ab — cd.'), phonemize)
        self.assertTrue(measured)
        self.assertEqual(words[1]['start'], words[1]['end'])
        words, measured = align_words('ab cd ef.', rows('ab cd.'), phonemize)
        self.assertFalse(measured)
        self.assertEqual([w['text'] for w in words], ['ab', 'cd', 'ef.'])
        self.assertAlmostEqual(words[-1]['end'], 0.5)

    def test_offset_and_validation_keep_words_inside_the_sentence(self):
        shifted = offset_words(estimate_words('One longer sentence.', 0, 2), 4.2, 6.2)
        validate_words(shifted, 'One longer sentence.', 4.2, 6.2)
        self.assertEqual(shifted[0]['start'], 4.2)
        self.assertEqual(shifted[-1]['end'], 6.2)
        with self.assertRaises(ValueError):
            validate_words(shifted[:-1], 'One longer sentence.', 4.2, 6.2)
        with self.assertRaises(ValueError):
            validate_words(shifted, 'One longer sentence.', 4.2, 5)

    def test_directed_speech_records_words_and_regenerates_old_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root/'source.json', root/'out.json'
            narration = 'Text becomes tokens. Tokens become numbers.'
            source.write_text(json.dumps({'title': 'T', 'scenes': [{'id': 1, 'headline': 'H', 'body': 'B', 'narration': narration}]}))

            def timed(text, path, voice):
                fake_speech(text, path, voice)
                return {'words': [{'text': w, 'start': i*.3, 'end': i*.3+.25} for i, w in enumerate(text.split())], 'measured': True}

            beats = generate_incremental(source, output, root, synthesizer=timed, directed=True)['scenes'][0]['beats']
            self.assertEqual([b['wordTiming'] for b in beats], ['model', 'model'])
            self.assertEqual(beats[1]['words'][0], {'text': 'Tokens', 'start': 1.28, 'end': 1.53})
            self.assertEqual(beats[1]['words'][-1]['start'], 1.88)

            estimated = generate_incremental(source, output, root, synthesizer=fake_speech, directed=True)
            self.assertEqual(estimated['cache']['generated_scene_ids'], [])
            sidecar = root/estimated['scenes'][0]['audio']
            record = json.loads(sidecar.with_suffix('.json').read_text())
            for beat in record['beats']:
                del beat['words']
            sidecar.with_suffix('.json').write_text(json.dumps(record))
            self.assertIsNone(cached_speech(root, narration, directed=True))
            repaired = generate_incremental(source, output, root, synthesizer=fake_speech, directed=True)
            self.assertEqual(repaired['cache']['generated_scene_ids'], [1])
            self.assertEqual(repaired['scenes'][0]['beats'][0]['wordTiming'], 'estimated')
            # Estimated sentences from an older aligner are retried; current ones are reused.
            self.assertIsNotNone(cached_speech(root, narration, directed=True))
            record = json.loads(sidecar.with_suffix('.json').read_text())
            record['alignment'] = 1
            sidecar.with_suffix('.json').write_text(json.dumps(record))
            self.assertIsNone(cached_speech(root, narration, directed=True))


NARRATION = 'Start with input text typed into a chat box. A tokenizer converts that input text into tokens.'


def worded_beats(with_words=True):
    from backend.services.director import sentences
    parts = sentences(NARRATION)
    spans = [(0, 4.5), (4.62, 9.2)]
    return [{'text': text, 'start': start, 'end': end,
             **({'words': [{'text': w, 'start': start+i*.5, 'end': start+i*.5+.4} for i, w in enumerate(text.split())]} if with_words else {})}
            for text, (start, end) in zip(parts, spans)]


class WordCueTests(unittest.TestCase):
    def test_phrase_and_pattern_cues(self):
        from backend.utils.word_timing import cue_time, pattern_time, phrase_time
        beat = worded_beats()[1]
        self.assertAlmostEqual(phrase_time(beat, 'input text'), 6.62)
        self.assertAlmostEqual(phrase_time(beat, 'Tokens'), 8.12)
        self.assertAlmostEqual(phrase_time(beat, 'token'), 8.12)  # "tokens", not the earlier "tokenizer"        self.assertIsNone(phrase_time(beat, 'model weights'))
        self.assertAlmostEqual(pattern_time(beat, r'\bconvert\w*'), 5.62)
        self.assertEqual(cue_time(beat, 4.65), 4.62)  # the lead never leaves the sentence
        self.assertEqual(cue_time(beat, None), 4.62)

    def test_choreography_reveals_objects_and_arrows_on_spoken_words(self):
        from backend.services.choreography import compile_scene, timed
        scene = {'narration': NARRATION, 'visual': {'kind': 'explanation', 'items': []}}
        result = timed(compile_scene(scene), worded_beats())
        self.assertEqual([(o['label'], o['at']) for o in result['objects']],
                         [('input text', 0.85), ('tokenizer', 4.97), ('tokens', 7.97)])
        connect = next(s for s in result['steps'] if s['action'] == 'connect')
        # "converts that input text into tokens": the arrow runs input text -> tokens, drawn once tokens is spoken.
        self.assertEqual([result['objects'][i]['label'] for i in connect['targets']], ['input text', 'tokens'])
        self.assertEqual((connect['start'], connect['end']), (7.97, 9.2))
        # Without measured words every cue stays on its sentence boundary.
        legacy = timed(compile_scene(scene), worded_beats(False))
        self.assertEqual([o['at'] for o in legacy['objects']], [0, 4.62, 4.62])
        self.assertTrue(all(s['start'] == [0, 4.62][s['sentence']] for s in legacy['steps']))

    def test_actions_wait_for_their_verb_and_objects(self):
        from backend.services.visual_actions import timed
        rows = timed({'narration': NARRATION, 'visual': {'kind': 'explanation', 'items': []}}, worded_beats())['beats']
        self.assertEqual([(r['start'], r['at']) for r in rows], [(0, 0.85), (4.62, 7.97)])

    def test_diagram_reveals_quoted_items_in_order(self):
        from backend.services.director import timed_visual
        visual = {'kind': 'relationship', 'items': ['tokens', 'input text'], 'cues': [1, 1], 'directed': True}
        self.assertEqual(timed_visual(visual, NARRATION, worded_beats())['revealAt'], [7.97, 7.97])
        visual['items'] = ['A summary label', 'tokens']
        self.assertEqual(timed_visual(visual, NARRATION, worded_beats())['revealAt'], [4.62, 7.97])


if __name__ == '__main__':
    unittest.main()


class PacingTests(unittest.TestCase):
    def test_pauses_follow_punctuation_and_scenes_are_levelled(self):
        import numpy as np
        from backend.services.incremental_audio import level, pause_after
        self.assertGreater(pause_after('Why does this work?'), pause_after('It works.'))
        quiet = (np.sin(np.linspace(0, 200, 24000)) * 1500).astype('<i2')
        loud = (np.sin(np.linspace(0, 200, 24000)) * 30000).astype('<i2')
        rms = lambda pcm: float(np.sqrt(np.mean((np.frombuffer(pcm, '<i2') / 32768.0) ** 2)))
        self.assertGreater(rms(level(quiet.tobytes())), rms(quiet.tobytes()) * 2, 'quiet narration is raised')
        self.assertLessEqual(np.abs(np.frombuffer(level(loud.tobytes()), '<i2')).max(), 32767 * .98, 'loud narration never clips')
        self.assertEqual(level(np.zeros(100, '<i2').tobytes()), np.zeros(100, '<i2').tobytes())
