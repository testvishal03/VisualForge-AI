import unittest

from backend.services.director import sentences
from backend.services.explainers import EXAMPLE_CANDIDATES, plan, timed


def scene(narration, kind='explanation'):
    return {'narration': narration, 'headline': 'H', 'body': 'B', 'visual': {'kind': kind, 'items': []}}


def beats(narration, step=.4):
    rows, start = [], 0.0
    for text in sentences(narration):
        words = [{'text': w, 'start': round(start + i*step, 3), 'end': round(start + i*step + .3, 3)} for i, w in enumerate(text.split())]
        rows.append({'text': text, 'start': start, 'end': words[-1]['end'] + .05, 'words': words})
        start = rows[-1]['end'] + .12
    return rows


class ExplainerTests(unittest.TestCase):
    def test_next_token_uses_the_quoted_example_and_cues_on_spoken_words(self):
        text = 'It is a next-word guesser. Give it "the cat sat on the" and it picks the next piece. Then it repeats that thousands of times.'
        spec = plan(scene(text))
        self.assertEqual((spec['kind'], spec['prompt'], spec['source']), ('next_token', 'the cat sat on the', 'narration'))
        self.assertEqual(spec['candidates'], EXAMPLE_CANDIDATES, 'only the built-in example carries illustrative candidates')
        timing = beats(text)
        result = timed(spec, timing)
        guess = next(w for w in timing[0]['words'] if w['text'].startswith('next'))
        self.assertAlmostEqual(result['at']['guess'], guess['start'] - .15)
        repeat = next(w for w in timing[2]['words'] if w['text'] == 'repeats')
        self.assertAlmostEqual(result['at']['repeat'], repeat['start'] - .15)
        custom = plan(scene('It predicts the next token. Give it "once upon a" and see.'))
        self.assertEqual((custom['prompt'], custom['candidates']), ('once upon a', []), 'no invented candidates for other prompts')

    def test_denoise_resolves_into_the_named_shape(self):
        spec = plan(scene('Image models start with static noise. Then they clean it up step by step until it looks like a heart.'))
        self.assertEqual((spec['kind'], spec['subject'], spec['named']), ('denoise', 'heart', True))
        self.assertEqual(plan(scene('Diffusion turns noise into an image.'))['subject'], 'star')

    def test_contrast_takes_titles_and_bins_from_the_narration(self):
        spec = plan(scene('Old-school AI judges: is this a cat or a dog? Generative AI creates something new.'))
        self.assertEqual(spec['kind'], 'contrast')
        self.assertEqual((spec['left']['title'], spec['right']['title'], spec['bins']), ('Old-school AI', 'Generative AI', ['cat', 'dog']))

    def test_caveat_cards_follow_spoken_order(self):
        spec = plan(scene('It copies bias from its data. It can also be wrong, a hallucination. Always fact-check it.'))
        self.assertEqual([c['key'] for c in spec['cards']], ['bias', 'wrong', 'editor'])
        result = timed(spec, beats('It copies bias from its data. It can also be wrong, a hallucination. Always fact-check it.'))
        self.assertLess(result['at']['bias'], result['at']['wrong'])

    def test_learning_steps_become_numbered_cards_from_their_own_clauses(self):
        text = ('How does it get so good? First, it is fed billions of texts, images and code. '
                'Next, it finds patterns by tuning millions of tiny dials. Finally, you prompt it, and it remixes those patterns.')
        spec = plan(scene(text, kind='process'))
        self.assertEqual([(s['key'], s['detail']) for s in spec['steps']],
                         [('feed', 'it is fed billions of texts'), ('patterns', 'it finds patterns'), ('prompt', 'you prompt it')])
        for step in spec['steps']:
            self.assertIn(step['detail'], text, 'card details are the narration’s own words')
        self.assertIsNone(plan(scene('First, search the catalog. Next, find the shelf. Finally, borrow the book.', kind='process')),
                          'other ordered scenes keep their process diagrams')

    def test_hoodie_is_drawn_only_when_spoken(self):
        self.assertTrue(plan(scene('Old-school AI sorts a cat or a dog. Generative AI creates a cat in a hoodie.'))['hoodie'])
        self.assertFalse(plan(scene('Old-school AI sorts a cat or a dog. Generative AI creates a new cat.'))['hoodie'])

    def test_plain_explanations_and_bookend_cards_keep_their_treatment(self):
        self.assertIsNone(plan(scene('It finds patterns by tuning millions of tiny dials called parameters.')))
        self.assertIsNone(plan(scene('Generative AI is a super-powered autocomplete.', kind='takeaway')))
        self.assertIsNone(plan(scene('Welcome! It predicts the next word.', kind='title')))


if __name__ == '__main__':
    unittest.main()


class ExplainerPlanTests(unittest.TestCase):
    def test_metaphors_do_not_trigger_and_review_panel_knows_explainers(self):
        self.assertIsNone(plan(scene('Generative AI is a super-powered autocomplete. It is a great co-pilot.')),
                          'calling AI an "autocomplete" is not an explanation of next-token prediction')
        from backend.services.visual_storytelling import plan_document
        narrations = ['Old-school AI judges a cat or a dog. Generative AI creates a cat in a hoodie.',
                      'It is a next-word guesser. It picks the next token, then repeats.',
                      'Image models start with static noise and clean it up step by step, like a heart.']
        document = {'topic': 'AI', 'scenes': [{'uid': str(i), 'headline': f'Scene {i}', 'body': 'Summary.', 'narration': n,
                                               'visual': {'kind': 'explanation', 'items': []}} for i, n in enumerate(narrations)]}
        result = plan_document(document)
        self.assertEqual([r['explainer'] for r in result['scenes']], ['contrast', 'next_token', 'denoise'])
        self.assertEqual(result['warnings'], [], 'distinct explainers are neither fallbacks nor repetition')


class ExplainerPackTwoTests(unittest.TestCase):
    def test_embedding_map_groups_only_what_the_narration_calls_close(self):
        text = ('If two concepts are similar, their vectors sit closer together. “Cat” and “Dog” may appear close together. '
                '“King” and “Queen” may also be close. But “Banana” may be much farther away from “Database.”')
        spec = plan(scene(text))
        self.assertEqual(spec['kind'], 'embedding_map')
        groups = {p['label']: p['group'] for p in spec['points']}
        self.assertEqual(groups['Cat'], groups['Dog'])
        self.assertEqual(groups['King'], groups['Queen'])
        self.assertNotEqual(groups['Cat'], groups['King'])
        self.assertNotEqual(groups['Banana'], groups['Database'], '"farther away" is not a grouping')
        self.assertIsNone(plan(scene('A record stores an embedding plus “Department”, “Title”, “Date” and “Source” as metadata fields.')),
                          'a list of fields without closeness is not a map')

    def test_retrieval_draws_only_the_stages_the_narration_names(self):
        text = ('The user question is converted into an embedding. The vector database searches for the closest chunks. '
                'Those chunks are retrieved and given to the language model, which writes the answer.')
        spec = plan(scene(text))
        self.assertEqual([s['key'] for s in spec['stages']], ['question', 'embedding', 'search', 'chunks', 'llm', 'answer'])
        self.assertIsNone(plan(scene('Retrieval helps, but a long answer still needs careful review by people.')))

    def test_tokenization_uses_a_quoted_or_narrated_sentence(self):
        spec = plan(scene('Text is broken into tokens before a model reads it. For example, "Embeddings turn meaning into geometry" becomes several tokens.'))
        self.assertEqual((spec['kind'], spec['text']), ('tokens', 'Embeddings turn meaning into geometry'))
        self.assertEqual((spec['pieces'], spec['ids']), ([], []), 'pieces come only from the model measurement')

    def test_tokenization_measurement_rebuilds_the_exact_text(self):
        import tempfile
        from pathlib import Path
        from backend.services.next_token import measure_tokens, read_tokens, validate_tokens
        class Engine:
            calls = 0
            def _load(self): pass
            def _request(self, route, payload, timeout=10):
                Engine.calls += 1
                return {'tokens': [{'id': 1, 'piece': 'Emb'}, {'id': 2, 'piece': 'eddings'}, {'id': 3, 'piece': ' work'}]}
        with tempfile.TemporaryDirectory() as d:
            result = measure_tokens('Embeddings work', Engine(), {'model': 'm'}, Path(d))
            self.assertEqual((result['pieces'], result['ids']), (['Emb', 'eddings', ' work'], [1, 2, 3]))
            self.assertEqual(read_tokens('Embeddings work', {'model': 'm'}, Path(d)), result)
            self.assertIsNone(read_tokens('Embeddings work', {'model': 'other'}, Path(d)))
        with self.assertRaises(ValueError):
            validate_tokens({**result, 'pieces': ['Emb', 'edding', ' work']})
