import copy
import unittest
from backend.services.choreography import compile_scene, validate, timed
from backend.services.editor_store import validate_document
from backend.scripts.create_tokens_lesson import make_document


class ChoreographyTests(unittest.TestCase):
    def setUp(self):
        self.scene={'narration':'Instructions occupy the context window. The current question arrives next. An application can remove older messages outside the context window.', 'visual':{'kind':'explanation','items':[]}}

    def test_grounded_actions_wait_for_their_sentences(self):
        spec=compile_scene(self.scene)
        self.assertEqual(spec['layout'],'workspace')
        question=next(i for i,o in enumerate(spec['objects']) if o['label']=='current question')
        self.assertFalse(any(s['sentence']==0 and question in s['targets'] for s in spec['steps']))
        result=timed(spec,[{'start':0,'end':4},{'start':4.2,'end':7},{'start':7.2,'end':12}])
        self.assertTrue(all(s['start']==4.2 for s in result['steps'] if s['sentence']==1))
        self.assertTrue(any(s['action']=='remove' for s in result['steps']))

    def test_invented_objects_and_early_actions_rejected(self):
        spec=compile_scene(self.scene)
        changed=copy.deepcopy(spec);changed['objects'][0]['label']='imaginary network'
        with self.assertRaises(ValueError):validate(changed,self.scene['narration'])
        changed=copy.deepcopy(spec);changed['steps'][0]['targets']=[len(spec['objects'])-1]
        with self.assertRaises(ValueError):validate(changed,self.scene['narration'])

    def test_no_unspoken_causal_edges(self):
        scene={'narration':'Tokens and punctuation are parts of text.', 'visual':{'kind':'explanation','items':[]}}
        spec=compile_scene(scene)
        self.assertFalse(any(s['action']=='connect' for s in spec['steps']))
        spec['steps'].append({'sentence':0,'action':'connect','targets':[0,1]})
        with self.assertRaises(ValueError):validate(spec,scene['narration'])

    def test_other_topics_use_exact_spoken_labels_and_sentence_cues(self):
        scene={'narration':'A seed absorbs water. Roots carry water to the stem. The stem moves water to leaves.',
               'visual':{'kind':'process','items':['seed','Roots','leaves'],'cues':[0,1,2]}}
        spec=compile_scene(scene)
        self.assertEqual(spec['layout'],'sequence')
        self.assertEqual([o['sentence'] for o in spec['objects']],[0,1,2])
        self.assertEqual([o['label'] for o in spec['objects']],['seed','Roots','leaves'])
        unsupported={**scene,'visual':{**scene['visual'],'items':['seed','imaginary step','leaves']}}
        self.assertNotIn('imaginary step',[o['label'] for o in compile_scene(unsupported)['objects']])

    def test_lesson_has_narrated_bookends_real_tokens_and_correct_budget(self):
        doc=make_document();validate_document(doc)
        self.assertEqual(doc['scenes'][0]['visual']['choreography']['layout'],'intro')
        self.assertEqual(doc['scenes'][-1]['visual']['choreography']['layout'],'outro')
        self.assertEqual(doc['scenes'][3]['visual']['worked']['input'],'The sky is')
        budget=doc['scenes'][10]['visual']['choreography']
        self.assertEqual(budget['layout'],'budget')
        self.assertEqual([o['label'] for o in budget['objects']],['1,000 tokens','200 tokens','800 tokens'])
        self.assertEqual(doc['scenes'][14]['visual']['choreography']['layout'],'comparison')

    def test_narration_edit_invalidates_stored_visual_cues(self):
        doc=make_document();doc['scenes'][0]['narration']='This new script describes a different subject entirely.'
        with self.assertRaises(ValueError):validate_document(doc)

    def test_numeric_allocation_cannot_invent_capacity(self):
        doc=make_document();row=doc['scenes'][10];spec=copy.deepcopy(row['visual']['choreography'])
        spec['objects'][1]['label']='900 tokens'
        with self.assertRaises(ValueError):validate(spec,row['narration'])

    def test_review_reel_includes_bookends_and_real_example_without_cutting_audio(self):
        from backend.services.scene_direction import preview_scenes
        doc=make_document()
        rows=[{'id':i+1,**s} for i,s in enumerate(doc['scenes'])]
        selected=preview_scenes(rows)
        self.assertEqual([r['id'] for r in selected],[1,4,11,25])
        self.assertTrue(all(r in rows for r in selected))
        self.assertLessEqual(sum(len(r['narration'].split())/2.2+1 for r in selected),120)


if __name__=='__main__':unittest.main()
