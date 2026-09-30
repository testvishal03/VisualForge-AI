import unittest

from backend.services.choreography import compile_scene, flow_pair
from backend.services.director import sentences
from backend.services.key_terms import candidates, key_terms, spoken


def scene(narration, headline, body, kind='explanation'):
    return {'narration': narration, 'headline': headline, 'body': body, 'visual': {'kind': kind, 'items': []}}


class KeyTermTests(unittest.TestCase):
    def test_candidates_skip_verbs_adverbs_and_filler(self):
        self.assertEqual(candidates('The application may select only the most relevant information.'), ['application', 'relevant information'])
        self.assertEqual(candidates('This is what allows the model to follow a conversation.'), ['model', 'conversation'])
        self.assertNotIn('quickly', candidates('Tokens move quickly through the model.'))

    def test_labels_are_verbatim_quotes_of_their_sentence(self):
        self.assertEqual(spoken('The model’s parameters contain learned patterns.', "model's parameters"), 'model’s parameters')
        self.assertEqual(spoken('Several Embeddings sit close together.', 'embedding'), 'Embeddings')
        parts = sentences('A user query becomes a vector. The database compares that vector with stored embeddings. The closest documents are returned.')
        terms = key_terms('How search compares vectors', 'A query vector is compared with stored embeddings.', parts)
        for term in terms:
            self.assertIn(term['label'].casefold(), parts[term['sentence']].casefold())
        self.assertEqual(sorted({t['sentence'] for t in terms}), [0, 1, 2], 'the diagram grows sentence by sentence')

    def test_generic_explanations_become_grounded_diagrams_with_a_cue_per_sentence(self):
        text = ('Your prompt is context. Conversation history is also part of that context. '
                'Retrieved documents can be added too. All of this has to fit inside the window.')
        plan = compile_scene(scene(text, 'Your prompt is context', 'your prompt is context.'))
        self.assertIsNotNone(plan)
        parts = sentences(text)
        self.assertEqual({s['sentence'] for s in plan['steps']}, set(range(len(parts))), 'every sentence has a visual cue')
        for obj in plan['objects']:
            self.assertIn(obj['label'].casefold(), parts[obj['sentence']].casefold())

    def test_curly_apostrophes_never_break_planning(self):
        text = 'And context is different from the knowledge learned during training. The model’s parameters contain learned patterns.'
        plan = compile_scene(scene(text, 'And context is different from the knowledge learned', 'Context differs from knowledge learned in training.'))
        if plan:
            for obj in plan['objects']:
                self.assertIn(obj['label'], ' '.join(sentences(text)))

    def test_arrows_follow_reading_order_around_the_verb(self):
        part = 'A tokenizer converts the input text into tokens.'
        objects = [{'label': 'tokenizer'}, {'label': 'input text'}, {'label': 'tokens'}]
        present = sorted(range(3), key=lambda i: part.find(objects[i]['label']))
        self.assertEqual(flow_pair(present, objects, part, part.find('converts')), [1, 2])
        part = 'Retrieval feeds the answer.'
        objects = [{'label': 'Retrieval'}, {'label': 'answer'}]
        self.assertEqual(flow_pair([0, 1], objects, part, part.find('feeds')), [0, 1])

    def test_negated_relationships_draw_no_arrow(self):
        text = 'We cannot send every document to the language model. Instead the system splits each document into smaller pieces.'
        plan = compile_scene(scene(text, 'We cannot send every document to the language model', 'Documents are split into smaller pieces.'))
        arrows = [[plan['objects'][i]['label'] for i in s['targets']] for s in plan['steps'] if s['action'] == 'connect']
        self.assertNotIn(['document', 'language model'], arrows)
        self.assertIn(['document', 'smaller pieces'], arrows)

    def test_specialized_scenes_keep_their_renderers(self):
        chart = scene('Sales rose 40 percent. Costs fell 10 percent.', 'Sales and costs', 'Sales rose while costs fell.', kind='chart')
        self.assertIsNone(compile_scene(chart))


if __name__ == '__main__':
    unittest.main()
