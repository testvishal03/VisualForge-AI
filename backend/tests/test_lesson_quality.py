import copy
import unittest
from types import SimpleNamespace

from backend.services.lesson_quality import label_candidates, label_problem, improve_visual, automatic_example
from backend.services.scene_direction import visual_issues
from backend.llm.prompts import build_scene_prompt


class LessonQualityTests(unittest.TestCase):
    def test_export_allows_recap_but_still_blocks_invalid_visuals(self):
        from backend.schemas.video_schema import VideoScript
        from backend.services.editor_store import document_from_video, quality, require_export_quality
        video = VideoScript.model_validate({'title':'Context windows', 'topic':'Context windows', 'scenes':[
            {'id':1,'headline':'Temporary context','body':'The context contains information available during this generation.',
             'narration':'The context window is the amount of tokenized information a model can consider during one generation.'},
            {'id':2,'headline':'Remember the capacity','body':'Input and output share the available context capacity.',
             'narration':'The context window is the amount of tokenized information the model can consider during a generation.'}]})
        document = document_from_video(video)
        issues = quality(document)['issues']
        self.assertTrue(any(i['code']=='repeated_explanation' and i['severity']=='warning' for i in issues))
        require_export_quality(document)
        document['scenes'][1]['visual'] = {'kind':'code','items':[]}
        with self.assertRaisesRegex(ValueError, 'Scene 2: No code was supplied'):
            require_export_quality(document)

    def test_candidates_reject_known_truncations(self):
        choices = label_candidates('Sunlight warms water at the surface.')
        self.assertNotIn('Sunlight warms water at the', choices)
        self.assertIn('Sunlight warms water at the surface', choices)
        self.assertTrue(label_problem('Some water molecules gain enough'))
        self.assertFalse(label_problem('numerical vectors'))

    def test_repairs_preserve_narration_values_and_are_idempotent(self):
        scene = SimpleNamespace(narration='Sunlight warms water at the surface. Some water molecules gain enough energy to escape.')
        visual = {'kind':'chart','items':['Sunlight warms water at the','Some water molecules gain enough'], 'cues':[0,1], 'values':[30,70]}
        old = copy.deepcopy(visual)
        result = improve_visual(scene, visual)
        self.assertEqual(visual, old)
        self.assertEqual(result['values'], [30,70])
        self.assertEqual(result['items'][0], 'Sunlight warms water at the surface')
        self.assertTrue(all(not label_problem(s) for s in result['items']))
        self.assertEqual(improve_visual(scene, result), result)

    def test_repeated_layout_changes_without_changing_concepts(self):
        scene = SimpleNamespace(narration='Input moves through a filter and becomes output.')
        visual = {'kind':'process','items':['Input','filter','output'],'cues':[0,0,0]}
        result = improve_visual(scene, visual, [visual,visual])
        self.assertEqual(result['layout'], 'detail')
        self.assertEqual(result['items'],visual['items'])

    def test_only_explicit_tokenizer_inputs_get_measured_examples(self):
        text = 'The tokenizer splits the input text "Hello world" into pieces. Each piece has a token ID.'
        spec = automatic_example(text)
        self.assertEqual(spec['input'], 'Hello world')
        self.assertEqual([s['action'] for s in spec['steps']], ['tokens','ids'])
        self.assertIsNone(automatic_example('A teacher reads the text "Hello world" to the class.'))
        self.assertIsNone(automatic_example(text.replace('into pieces', 'into exactly three tokens')))
        self.assertIsNone(automatic_example('A tokenizer splits text into pieces.'))

    def test_export_reports_unsupported_chart_and_incomplete_label(self):
        row = {'body':'Water changes state.', 'narration':'Water becomes vapor.', 'visual':{'kind':'chart','items':['Water at the','vapor'], 'values':[30,70]}}
        errors = {i['code'] for i in visual_issues({'scenes':[row]}) if i['severity']=='error'}
        self.assertEqual(errors, {'unsupported_statistic','incomplete_label'})

    def test_narration_prompt_carries_teaching_context(self):
        prompt = build_scene_prompt('Water', {'point':'Explain evaporation'}, 'narration', teaching_plan=[{'point':'Follow a puddle'}], previous_narration='A puddle forms after rain.')
        self.assertIn('Follow a puddle', prompt)
        self.assertIn('A puddle forms after rain.', prompt)


if __name__ == '__main__':
    unittest.main()
