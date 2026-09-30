import unittest
from types import SimpleNamespace
from backend.services.director import script_to_video, build_direction, sentences
from backend.services.topic_visuals import topic_visual
from backend.services.editor_store import document_from_video, validate_document
from backend.schemas.video_schema import words


class StorytellingTests(unittest.TestCase):
    def test_line_by_line_script_preserves_words_and_groups_related_sentences(self):
        script = '\n\n'.join([
            'A token is a unit of text.', 'It can be a word or part of a word.',
            'The tokenizer splits text into tokens.', 'Those tokens are mapped to numerical IDs.',
            'Now consider the context window.', 'The context can include system instructions.',
            'Previous messages occupy some space.', 'Your current prompt consumes more capacity.',
            'The generated response also uses the available space.',
            'These categories share a limited amount of space during generation.',
            'Keep relevant information available and remove unrelated details from a long conversation.'
        ])
        video = script_to_video('Tokens and context windows',script)
        self.assertEqual(' '.join(s.narration for s in video.scenes), ' '.join(script.split()))
        self.assertLessEqual(len(video.scenes),3)
        self.assertTrue(all(15<=len(words(s.narration))<=60 and len(s.narration)<=600 for s in video.scenes))
        validate_document(document_from_video(video,build_direction(video)))

    def test_context_inventory_uses_only_present_source_categories(self):
        scene = SimpleNamespace(narration='The context can include system instructions. Previous messages and your current prompt consume space. The generated response also uses capacity.')
        visual = topic_visual(scene)
        self.assertEqual(visual['kind'],'components')
        self.assertEqual(visual['items'],['system instructions','Previous messages','current prompt','generated response'])
        for item,cue in zip(visual['items'],visual['cues']):
            self.assertIn(item,sentences(scene.narration)[cue])
        self.assertNotIn('values',visual)

    def test_token_pipeline_requires_all_stages_and_mechanism(self):
        visual=topic_visual(SimpleNamespace(narration='A tokenizer splits input text into tokens. These are mapped to token IDs.'))
        self.assertEqual(visual['items'],['input text','tokens','token IDs'])
        self.assertEqual(visual['cues'],[0,0,1])
        self.assertIsNone(topic_visual(SimpleNamespace(narration='A tokenizer is useful. Different models use different tokenizers.')))
        self.assertIsNone(topic_visual(SimpleNamespace(narration='A context window is a temporary space.')))

    def test_unrelated_topic_does_not_get_token_diagram(self):
        self.assertIsNone(topic_visual(SimpleNamespace(narration='The library contains books and documents. Readers can borrow books for their studies.')))


if __name__=='__main__':unittest.main()
