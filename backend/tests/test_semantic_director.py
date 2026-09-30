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


class ConceptSelectionTests(unittest.TestCase):
    """The planning model chooses which narrated concepts an explanation scene shows."""
    def setUp(self):
        self.scene = Scene(id=1, headline='We cannot send every document to the model', body='Documents are split into smaller pieces first.',
            narration='We cannot send every document to the language model. Instead we split each document into smaller pieces. Each chunk is stored in a vector database.')
        self.data = {'kind':'explanation','icon':'book','elements':[],'layout':'auto','treatment':'build','concepts':[
            {'label':'language model','sentence':0},{'label':'smaller pieces','sentence':1},{'label':'vector database','sentence':2}]}

    def test_chosen_concepts_are_offered_phrases_in_spoken_order(self):
        row = validate_decision(self.data, self.scene, 0)
        self.assertEqual([c['label'] for c in row['concepts']], ['language model', 'smaller pieces', 'vector database'])
        for bad in ([{'label':'human consciousness','sentence':0},{'label':'smaller pieces','sentence':1}],
                    [{'label':'smaller pieces','sentence':1},{'label':'language model','sentence':0}],
                    [{'label':'split','sentence':1},{'label':'vector database','sentence':2}]):
            with self.assertRaises(ValueError):
                validate_decision({**self.data,'concepts':bad}, self.scene, 0)
        with self.assertRaisesRegex(ValueError,'Only explanation'):
            validate_decision({'kind':'process','icon':'chip','elements':[{'label':'every document','sentence':0,'icon':'book'},
                {'label':'smaller pieces','sentence':1,'icon':'book'},{'label':'vector database','sentence':2,'icon':'database'}],
                'concepts':[{'label':'language model','sentence':0}]}, self.scene, 0)

    def test_planner_offers_only_noun_phrases_and_the_scene_draws_the_choice(self):
        prompts = []
        def generate_json(prompt, schema, max_new_tokens):
            prompts.append((prompt, schema))
            return json.dumps(self.data)
        engine = SimpleNamespace(generate_json=generate_json, cache_identity='fake')
        video = VideoScript(title='RAG', topic='Retrieval', scenes=[self.scene])
        with tempfile.TemporaryDirectory() as directory:
            plan = plan_video(video, engine=engine, cache=Path(directory))
        prompt, schema = prompts[0]
        offered = [o['properties']['label']['enum'] for o in schema['$defs']['Concept']['anyOf']]
        self.assertIn('vector database', offered[2])
        self.assertNotIn('split', offered[1], 'verbs are never offered as concepts')
        row = plan['scenes'][0]
        self.assertEqual([o['label'] for o in row['choreography']['objects']], ['language model', 'smaller pieces', 'vector database'])
        document = document_from_video(video, {'scenes':[row]})
        validate_document(document)

    def test_stale_concepts_after_a_narration_edit_fall_back_to_rules(self):
        from backend.services.choreography import compile_scene
        scene = {'narration':'A query becomes a vector. The database returns the closest chunks.', 'headline':'Search', 'body':'A query vector finds chunks.',
                 'visual':{'kind':'explanation','items':[],'concepts':[{'label':'language model','sentence':0},{'label':'smaller pieces','sentence':1}]}}
        plan = compile_scene(scene)
        for obj in plan['objects']:
            self.assertNotIn(obj['label'], ('language model', 'smaller pieces'))


class SalvageTests(unittest.TestCase):
    def test_duplicate_picks_become_concepts_instead_of_another_attempt(self):
        from backend.services.semantic_director import decide
        scene = Scene(id=1, headline='Chunking documents', body='Documents are split into chunks.',
            narration='Each document is split into chunks. Every chunk becomes an embedding. The embeddings go into a vector database.')
        data = {'kind':'process','icon':'book','layout':'auto','treatment':'build','concepts':[],'elements':[
            {'label':'chunks','sentence':0,'icon':'book'},{'label':'chunk','sentence':1,'icon':'book'},{'label':'vector database','sentence':2,'icon':'database'}]}
        row = decide(data, scene, 0)
        self.assertEqual(row['kind'], 'explanation')
        self.assertEqual([c['label'] for c in row['concepts']], ['chunks', 'vector database'])
        with self.assertRaises(ValueError):
            decide({**data, 'elements':[{'label':'nonsense words','sentence':0,'icon':'book'}]*3}, scene, 0)
