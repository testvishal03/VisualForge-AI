import unittest

from backend.scripts.create_tokens_lesson import make_document
from backend.services.visual_actions import plan,timed


class VisualActionTests(unittest.TestCase):
    def test_tokens_episode_uses_distinct_diagram_families(self):
        scenes=make_document()['scenes']
        self.assertEqual([plan(s)['form'] if plan(s) else None for s in scenes[1:7]],
                         ['flow','split',None,'mapping','compare','window'])
        for scene in scenes[1:3]:
            result=plan(scene)
            self.assertEqual(len(result['beats']),len(__import__('backend.services.director',fromlist=['sentences']).sentences(scene['narration'])))
            self.assertTrue(all(row['text'] in scene['narration'] for row in result['beats']))

    def test_actions_follow_measured_sentences_and_only_cited_objects(self):
        scene={'narration':'A seed absorbs water. Roots carry water to the stem. The stem moves water to leaves.',
               'visual':{'kind':'process','items':['seed','Roots','leaves'],'cues':[0,1,2]}}
        beats=[{'text':'A seed absorbs water.','start':0,'end':2},
               {'text':'Roots carry water to the stem.','start':2.2,'end':4},
               {'text':'The stem moves water to leaves.','start':4.2,'end':6}]
        result=timed(scene,beats)
        self.assertEqual(result['form'],'flow')
        self.assertEqual([row['start'] for row in result['beats']],[0,2.2,4.2])
        self.assertEqual([row['verb'] for row in result['beats']],['reveal','reveal','reveal'])
        self.assertTrue(all(row['targets'] for row in result['beats']))

    def test_eviction_requires_actual_removal_step(self):
        scene={'narration':'Instructions occupy the context window. The current question arrives next. An application can remove older messages outside the context window.',
               'visual':{'kind':'explanation','items':[]}}
        result=plan(scene)
        self.assertEqual(result['form'],'window')
        self.assertEqual(result['beats'][-1]['verb'],'evict')


class LayoutVarietyTests(unittest.TestCase):
    def scene(self, narration, kind='explanation'):
        return {'narration': narration, 'headline': 'Search', 'body': narration.split('.')[0] + '.', 'visual': {'kind': kind, 'items': []}}

    def test_layouts_follow_meaning(self):
        from backend.services.visual_actions import form_for
        cases = {
            'Every tool is described with three parts: a name, a description, and parameters. The name identifies the tool.': 'split',
            'A model can use tools such as a calculator, a search engine, and a calendar. The model picks the right tool.': 'grid',
        }
        three = {'layout': 'sequence', 'objects': [{'label': x, 'sentence': 0} for x in ('a', 'b', 'c')]}
        for narration, expected in cases.items():
            self.assertEqual(form_for(self.scene(narration), three), expected, narration)
        # "such as" without a list is not a list of examples.
        self.assertNotEqual(form_for(self.scene('Start with input text, such as a question. A tokenizer converts it.'), three), 'grid')

    def test_neighbouring_scenes_do_not_repeat_a_neutral_layout(self):
        from collections import Counter
        narrations = [f'The {w} database stores records for the {w} team. The {w} index finds results for every {w} query.'
                      for w in ('first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth')]
        recent = []
        for narration in narrations:
            result = plan(self.scene(narration), recent)
            recent.append(result['form'])
        self.assertTrue(all(a != b for a, b in zip(recent, recent[1:])), recent)
        self.assertGreaterEqual(len(set(recent)), 4, recent)
        self.assertLessEqual(max(Counter(recent).values()), 3, recent)


if __name__=='__main__':unittest.main()
