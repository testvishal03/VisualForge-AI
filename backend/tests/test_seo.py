import unittest

from backend.services.seo import extract, title_notes, validate

BLOCK = '{"titles": ["Machine Learning Explained Visually for Beginners", "What Is Machine Learning? (Visual Guide)"],' \
        ' "description": "Machine learning explained with simple visuals.", "tags": ["machine learning", "ml for beginners"],' \
        ' "hashtags": ["#MachineLearning", "AI", "DataScience"]}'


class PublishBlockTests(unittest.TestCase):
    def test_fenced_and_copied_blocks_are_removed_from_the_narration(self):
        for text in [f'One paragraph of narration.\n\n```publish\n{BLOCK}\n```\n', f'One paragraph of narration.\n\npublish\n{BLOCK}\n']:
            rest, block, error = extract(text)
            self.assertIsNone(error)
            self.assertEqual(rest, 'One paragraph of narration.')
            self.assertEqual(block['titles'][0], 'Machine Learning Explained Visually for Beginners')
            self.assertEqual(block['hashtags'], ['MachineLearning', 'AI', 'DataScience'])

    def test_scripts_without_a_block_are_unchanged(self):
        self.assertEqual(extract('Just narration.'), ('Just narration.', None, None))

    def test_youtube_limits_are_enforced(self):
        with self.assertRaisesRegex(ValueError, '100 characters'):
            validate({'titles': ['x' * 101]})
        with self.assertRaisesRegex(ValueError, '< or >'):
            validate({'titles': ['Fine'], 'description': 'Use <b>bold</b>'})
        many = validate({'titles': ['Fine'], 'tags': [f'machine learning tag number {n}' for n in range(40)]})
        self.assertLessEqual(len(','.join(many['tags'])), 500, 'tags are trimmed to YouTube\'s 500 characters')
        _, _, error = extract('Narration.\n\n```publish\n{"titles": [\n```')
        self.assertIn('Publish block', error)

    def test_thumbnail_words_scene_and_badge_are_checked(self):
        good = validate({'titles': ['Fine'], 'thumbnail': {'text': 'How Machines Learn', 'highlight': 'Learn', 'scene': 7, 'badge': 'Episode 1'}})
        self.assertEqual(good['thumbnail']['scene'], 7)
        for bad, message in [({'text': 'one two three four five', 'scene': 1}, '1 to 4 words'),
                             ({'text': 'How Machines Learn', 'highlight': 'Data', 'scene': 1}, 'one of the thumbnail words'),
                             ({'text': 'Learn', 'scene': 0}, 'scene number')]:
            with self.assertRaisesRegex(ValueError, message):
                validate({'titles': ['Fine'], 'thumbnail': bad})

    def test_title_notes(self):
        self.assertIn('cut off', ' '.join(title_notes('x' * 70)))
        self.assertEqual(title_notes('Machine Learning Explained Visually for Beginners'), [])

    def test_the_description_leads_with_seo_text_and_keeps_measured_chapters(self):
        from backend.services.publishing import description
        scenes = [{'headline': f'Part {n}', 'body': 'b', 'narration': 'Some words here.', 'duration': 20, 'beats': []} for n in range(4)]
        text, meta = description('T', 'Topic', scenes, {}, seo=validate(eval(BLOCK.replace('true', 'True'))))
        self.assertTrue(text.startswith('Machine learning explained with simple visuals.'))
        self.assertIn('Chapters:', text)
        self.assertIn('#MachineLearning #AI #DataScience', text)
        self.assertGreaterEqual(meta['chapters'], 3)


if __name__ == '__main__':
    unittest.main()
