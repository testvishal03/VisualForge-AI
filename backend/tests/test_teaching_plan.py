import copy
import unittest
from backend.services.teaching_plan import plan_scene,validate_plan,timed_plan,toy_vectors
from backend.services.director import sentences


class TeachingPlanTests(unittest.TestCase):
    def scene(self,narration):
        return {'headline':'A concrete explanation','body':'Follow the example through each step.', 'narration':narration}

    def test_topics_produce_distinct_demonstrations(self):
        examples = {
            'embedding':'An embedding represents text using a numerical vector. Its values are learned by an embedding model.',
            'vector_search':'Vector search compares a query vector with stored vectors. Cosine similarity compares their directions to find close matches.',
            'rag':'Retrieval finds relevant documents for a question. The passages become context for the language model. The model generates an answer using those sources.',
            'explanation':'A library provides books for its readers. Returning a book makes it available for someone else.'}
        for component,text in examples.items():
            scene=self.scene(text);plan=plan_scene(scene)
            self.assertEqual(plan['component'],component)
            self.assertEqual(plan['takeaway'],sentences(text)[-1])
            self.assertEqual(validate_plan(plan,text),plan)

    def test_numeric_script_does_not_get_conflicting_toy_vectors(self):
        plan=plan_scene(self.scene('An embedding vector contains 768 numerical values. The model computes this vector from the input text.'))
        self.assertEqual(plan['component'],'explanation')

    def test_grounding_and_sentence_order_are_validated(self):
        scene=self.scene('An embedding is a numerical vector. A model computes its values from text.')
        plan=plan_scene(scene)
        bad=copy.deepcopy(plan);bad['steps'][0]['label']='invented source'
        with self.assertRaises(ValueError):validate_plan(bad,scene['narration'])
        bad=copy.deepcopy(plan);bad['steps'].reverse()
        with self.assertRaises(ValueError):validate_plan(bad,scene['narration'])
        bad=copy.deepcopy(plan);bad['evidence']='source'
        with self.assertRaises(ValueError):validate_plan(bad,scene['narration'])

    def test_measured_cues_and_computed_cosine(self):
        scene=self.scene('An embedding is a numerical vector. Cosine similarity compares vector directions.')
        beats=[{'text':s,'start':i*3,'end':(i+1)*3} for i,s in enumerate(sentences(scene['narration']))]
        result=timed_plan(scene,beats)
        self.assertEqual(result['at'],[0,3])
        self.assertEqual([p['cosine'] for p in result['example']['points']],[1,.8,0])
        self.assertEqual(result['example']['provenance'],'illustrative')
        with self.assertRaises(ValueError):timed_plan(scene,beats[:1])

    def test_incidental_rag_and_reversed_flow_are_not_animated_as_pipeline(self):
        self.assertEqual(plan_scene(self.scene('RAG is one approach to answering questions. Other methods use different architectures.'))['component'],'explanation')
        self.assertEqual(plan_scene(self.scene('The answer is generated first. Retrieval finds documents afterward.'))['component'],'explanation')


if __name__=='__main__':unittest.main()
