import unittest
from unittest.mock import patch

import backend.services.key_terms as key_terms
from backend.services.key_terms import candidates, parser


@unittest.skipIf(parser() is None, 'spaCy English model not installed')
class GrammarLabelTests(unittest.TestCase):
    """Real sentences from a 25-scene script whose word-shape labels were wrong."""
    cases = {
        'This is exactly what a vector database is built for.': ['vector database'],                        # not "built"
        'No matching keywords, but the meaning lines up perfectly.': ['matching', 'meaning'],               # not "meaning lines"
        'So vector databases use a smarter trick called Approximate Nearest Neighbor search, or ANN.':
            ['vector databases', 'Approximate Nearest Neighbor search', 'ANN'],                             # no "smarter trick"
        'It trades a tiny bit of accuracy for massive speed.': ['accuracy', 'massive speed'],               # no "tiny bit"
        'Choosing one depends on your needs.': [],                                                         # no "Choosing one"
        "It's a next-word guesser.": ['next-word guesser'],
        'Imagine you have ten million documents.': ['ten million documents'],
        'Vector databases store embeddings with their metadata.': ['Vector databases', 'embeddings', 'metadata'],
        'A vector database stores embeddings and metadata.': ['vector database', 'embeddings', 'metadata'],
        'The query embedding is compared with every single stored embedding.': ['query embedding', 'embedding'],
        'They use indexes like HNSW and IVF to make similarity search lightning fast.': ['indexes', 'HNSW', 'IVF', 'similarity search'],
        'For example, "find the user where id equals 42".': ['user', 'id'],
        'Managed options like Pinecone handle scaling for you.': ['Pinecone'],
    }

    def test_labels_are_the_sentences_real_noun_phrases(self):
        for sentence, expected in self.cases.items():
            self.assertEqual(candidates(sentence), expected, sentence)

    def test_every_label_is_quoted_verbatim(self):
        for sentence in self.cases:
            for label in candidates(sentence):
                self.assertIn(label, sentence.replace('’', "'"))


@unittest.skipIf(parser() is None, 'spaCy English model not installed')
class VerbInsideLabelTests(unittest.TestCase):
    def test_labels_containing_the_sentences_verb_are_weak(self):
        from backend.services.visual_quality import verb_inside
        narration = ('The database returns a chunk from the HR policy about "annual paid time off". '
                     'No matching keywords, but the meaning lines up perfectly.')
        self.assertTrue(verb_inside('database returns a chunk', narration))
        self.assertTrue(verb_inside('meaning lines', narration))
        self.assertFalse(verb_inside('HR policy', narration))
        self.assertFalse(verb_inside('annual paid time off', narration), 'a participle modifying a noun is not a verb')


class FallbackTests(unittest.TestCase):
    def test_without_the_parser_the_word_shape_rules_still_work(self):
        with patch.object(key_terms, 'grammar_candidates', lambda text: None):
            self.assertIn('input text', candidates('The tokenizer splits input text into tokens.'))


if __name__ == '__main__':
    unittest.main()
