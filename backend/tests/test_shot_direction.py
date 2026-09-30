import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.scripts.create_tokens_lesson import make_document
from backend.services.editor_store import EditorStore,validate_document
from backend.services.run_state import fingerprint
from backend.services.shot_direction import plan,select_contiguous,set_override,timed


class ShotDirectionTests(unittest.TestCase):
    def test_shots_follow_every_spoken_sentence_and_keep_labels_grounded(self):
        scene=make_document()['scenes'][1]
        rows=plan(scene)
        self.assertGreaterEqual(len(rows),3)
        self.assertEqual(rows[0]['mode'],'wide')
        self.assertTrue(all(row['label'] is None or row['label'] in [o['label'] for o in scene['visual']['choreography']['objects']] for row in rows))
        beats=[{'start':i*2,'end':(i+1)*2,'text':row['text']} for i,row in enumerate(rows)]
        self.assertEqual([shot['start'] for shot in timed(scene,beats)],[i*2 for i in range(len(rows))])

    def test_only_selected_shot_changes_and_approved_narration_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            store=EditorStore(Path(directory));document=make_document()
            project=store.create(document['topic'],document,source={'mode':'script'})
            project=store.approve_storyboard(project['id'],project['revision'])
            before=copy.deepcopy(project['document'])
            jobs=SimpleNamespace(store=store)
            changed=set_override(jobs,project,before['scenes'][1]['uid'],1,'detail')
            self.assertEqual(changed['document']['scenes'][1]['visual']['shotOverrides'],{'1':'detail'})
            self.assertEqual(changed['document']['scenes'][1]['narration'],before['scenes'][1]['narration'])
            self.assertEqual(changed['document']['scenes'][0],before['scenes'][0])
            self.assertEqual(changed['storyboard_approved'],fingerprint(changed['document']))
            restored=set_override(jobs,changed,before['scenes'][1]['uid'],1,'auto')
            self.assertEqual(restored['document'],before)
            invalid=copy.deepcopy(restored['document']);invalid['scenes'][1]['visual']['shotOverrides']={'100':'wide'}
            with self.assertRaises(ValueError):validate_document(invalid)

    def test_two_minute_preview_selects_complete_consecutive_scenes(self):
        scenes=[{'uid':str(i),'narration':'x'} for i in range(7)]
        selected=select_contiguous(scenes,'1',{str(i):20 for i in range(7)})
        self.assertEqual([s['uid'] for s in selected],['1','2','3','4','5'])
        with self.assertRaises(ValueError):select_contiguous(scenes,'unknown',{str(i):20 for i in range(7)})


if __name__=='__main__':unittest.main()
