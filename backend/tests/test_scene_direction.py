import copy
import unittest
from backend.services.scene_direction import preview_scenes,visual_issues

class DirectionTests(unittest.TestCase):
    def test_sample_is_contiguous_bounded_and_prefers_variety(self):
        rows=[{'id':i,'narration':'example','visual':{'kind':kind}} for i,kind in enumerate(['process','process','process','comparison','components'],1)]
        chosen=preview_scenes(rows,{r['id']:16 for r in rows})
        self.assertEqual([r['id'] for r in chosen],[3,4,5])
        self.assertLessEqual(len(chosen)*16,60)
        self.assertEqual(len(preview_scenes(rows[:1],{1:9})),1)
        with self.assertRaisesRegex(ValueError,'Split'):
            preview_scenes(rows[:1],{1:61})

    def test_visual_checks_are_warnings_and_detect_runs(self):
        row={'body':'Short explanation','narration':'word '*50,'visual':{'kind':'explanation','items':[]}}
        issues=visual_issues({'scenes':[copy.deepcopy(row) for _ in range(3)]})
        self.assertEqual(sum(i['code']=='repeated_layout' for i in issues),1)
        self.assertTrue(all(i['severity']=='warning' for i in issues))
        self.assertIn('static_explanation',{i['code'] for i in issues})

if __name__=='__main__':unittest.main()
