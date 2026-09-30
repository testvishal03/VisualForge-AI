import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from backend.schemas.video_schema import Scene, VideoScript
from backend.services.semantic_director import validate_decision, plan_video
from backend.services.editor_store import document_from_video, validate_document
from backend.services.director import choose_icon


class SemanticDirectorTests(unittest.TestCase):
    def setUp(self):
        self.scene = Scene(id=1, headline='From text to numbers', body='Tokens connect written text with numerical model inputs.',
            narration='A tokenizer splits input text into tokens. Each token maps to a token ID in a vocabulary. The model converts these identifiers into numerical vectors for processing.')
        self.data = {'kind':'process', 'icon':'chip', 'elements':[
            {'label':'input text','sentence':0,'icon':'book'},
            {'label':'token ID','sentence':1,'icon':'database'},
            {'label':'numerical vectors','sentence':2,'icon':'network'}]}

    def test_labels_are_grounded_and_cues_preserve_measured_sentence_order(self):
        row = validate_decision(self.data, self.scene, 0)
        self.assertEqual(row['cues'], [0,1,2])
        self.assertTrue(row['planned'])
        bad = json.loads(json.dumps(self.data))
        bad['elements'][0]['label'] = 'human consciousness'
        with self.assertRaisesRegex(ValueError, 'exact short phrase'):
            validate_decision(bad, self.scene, 0)
        bad['elements'][0] = {'label':'input text', 'sentence':2, 'icon':'book'}
        with self.assertRaises(ValueError):
            validate_decision(bad, self.scene, 0)

    def test_composition_must_match_the_teaching_form(self):
        row=validate_decision({**self.data,'layout':'pipeline'},self.scene,0)
        self.assertEqual(row['layout'],'pipeline')
        with self.assertRaisesRegex(ValueError,'compatible'):
            validate_decision({**self.data,'layout':'layers'},self.scene,0)
        video=VideoScript(title='Test lesson',topic='Language models',scenes=[self.scene,self.scene.model_copy(update={'id':2,'headline':'Representations','narration':self.scene.narration.replace('A tokenizer','The tokenizer')})])
        document=document_from_video(video,{'scenes':[row]})
        validate_document(document)
        document['scenes'][0]['visual']['layout']='branching'
        with self.assertRaisesRegex(ValueError,'Composition'):
            validate_document(document)

    def test_model_training_is_not_rain_and_unrelated_domain_icons_are_replaced(self):
        self.assertEqual(choose_icon('The model learns from training data.'), 'database')
        bad = json.loads(json.dumps(self.data))
        bad['elements'][0]['icon'] = 'rain'
        self.assertNotEqual(validate_decision(bad, self.scene, 0)['icons'][0], 'rain')

    def test_caching_keeps_narration_unchanged_and_output_is_renderable(self):
        second = self.scene.model_copy(update={'id':2, 'headline':'Representations', 'narration':self.scene.narration.replace('A tokenizer', 'The tokenizer')})
        video = VideoScript(title='Language models',topic='Language models',scenes=[self.scene,second])
        engine = SimpleNamespace(cache_identity='test', generate_json=Mock(return_value=json.dumps(self.data)))
        with tempfile.TemporaryDirectory() as tmp:
            before = video.model_dump()
            plan = plan_video(video,engine=engine,cache=Path(tmp))
            again = plan_video(video,engine=engine,cache=Path(tmp))
            self.assertEqual(plan, again)
            self.assertEqual(engine.generate_json.call_count, 2)
            self.assertEqual(before, video.model_dump())
            self.assertEqual(validate_document(document_from_video(video,plan)), video)

    def test_invalid_model_output_has_bounded_retries_and_explicit_fallback(self):
        video = self.scene.model_copy() # A single scene is enough to exercise planning.
        engine = SimpleNamespace(cache_identity='test',generate_json=Mock(return_value='{}'))
        with tempfile.TemporaryDirectory() as tmp:
            plan=plan_video(SimpleNamespace(topic='Any topic',scenes=[video]),engine=engine,cache=Path(tmp))
        self.assertEqual(engine.generate_json.call_count,3)
        self.assertEqual(len(plan['warnings']),1)
        self.assertEqual(plan['scenes'][0]['id'],1)

if __name__ == '__main__': unittest.main()
