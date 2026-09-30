import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from backend.tests import test_storyboard
from backend.tests import test_editor
from backend.services.creator_workflow import accept, accepted, delete_projects
from backend.services.script_projects import create
from backend.services.visual_storytelling import plan_document, timed_plan
from backend.services.script_generator import write_json_atomic


class CreatorFlowTests(unittest.TestCase):
    setUp=test_storyboard.StoryboardTests.setUp

    def test_playlist_waits_for_acceptance_and_edits_reopen_review(self):
        w=self.jobs.workspaces.create({'name':'Generative AI Visualized','kind':'series','current_topic':'Tokens and Context Windows'})
        doc=copy.deepcopy(self.p['document']);doc['topic']='Embeddings'
        p=self.store.create('Embeddings',doc)
        self.jobs.workspaces.attach(w['id'],p['id'])
        pending=self.jobs.workspaces.get(w['id'])
        self.assertIsNone(pending['next_topic'])
        self.assertEqual(pending['active_project'],p['id'])
        with patch.object(self.jobs,'artifact_ready',return_value=False):
            with self.assertRaises(ValueError):accept(self.jobs,p)
        p['draft_render']={'sha256':'verified','key':'key'}
        with patch.object(self.jobs,'artifact_ready',side_effect=lambda p,a:bool(a)):
            p=accept(self.jobs,p)
        self.assertTrue(accepted(self.store,p))
        self.assertEqual(self.jobs.workspaces.get(w['id'])['next_topic'],'Vector Databases')
        document=copy.deepcopy(p['document']);document['scenes'][0]['body']='A revised explanation to review.'
        p=self.store.save(p['id'],p['revision'],document)
        self.assertFalse(accepted(self.store,p))
        self.assertIsNone(self.jobs.workspaces.get(w['id'])['next_topic'])

    def test_long_scripts_split_without_losing_narration_or_duration_cap(self):
        text='\n\n'.join(f'Example {i} shows water moving through a different part of the environment. Energy from sunlight helps liquid water evaporate into the air, where cooling can later produce droplets and clouds.' for i in range(180))
        p=create(self.store,'Water examples',text,{'mode':'script','automatic':True,'approval_required':True,'profile':'draft'})
        self.assertGreater(p['source']['minutes'],30)
        self.assertEqual(p['source']['minimum_seconds'],0)
        from backend.services.long_video import chapters_store
        children=chapters_store(self.store,p)
        narration=' '.join(scene['narration'] for row in p['long_video']['chapters'] for scene in children.load(row['id'])['document']['scenes'])
        self.assertEqual(narration,' '.join(text.split()))
        self.assertIsNone(p['long_video']['script_approved'])

    def test_short_scripts_are_not_expanded(self):
        p=create(self.store,'Short lesson','Water evaporates.',{'mode':'script'})
        self.assertEqual(p['document']['scenes'][0]['narration'],'Water evaporates.')
        self.assertLess(p['source']['minutes'],1)

    def test_new_export_clears_finished_status(self):
        p=self.p;p['accepted_export']={'content':'old','sha256':'old'}
        write_json_atomic(self.store.folder(p['id'])/'project.json',p)
        self.store.update_artifact(p['id'],'draft_render',{'key':'new','sha256':'new','file':'draft.mp4'})
        self.assertNotIn('accepted_export',self.store.load(p['id']))

    def test_permanent_delete_removes_only_the_selected_project(self):
        p=self.store.create('Another lesson',self.p['document'])
        self.jobs.workspaces.list()
        folder=self.store.folder(p['id']);(folder/'video.mp4').write_bytes(b'fixture')
        delete_projects(self.store,self.jobs.workspaces,[p['id']])
        self.assertFalse(folder.exists())
        self.assertTrue(self.store.folder(self.p['id']).exists())
        self.assertFalse(any(p['id'] in w['episodes'] for w in self.jobs.workspaces.list()))
        with self.assertRaises(ValueError):delete_projects(self.store,self.jobs.workspaces,['../outside'])

    def test_linked_deletion_target_is_rejected(self):
        with patch.object(Path,'is_junction',return_value=True):
            with self.assertRaises(ValueError):delete_projects(self.store,self.jobs.workspaces,[self.p['id']])
        self.assertTrue(self.store.folder(self.p['id']).exists())

    def test_visual_plan_is_source_linked_and_flags_fallback_and_repetition(self):
        doc=copy.deepcopy(self.p['document'])
        row=doc['scenes'][0]
        row['visual']={'kind':'explanation','items':[]}
        row['narration']='An embedding converts text into a vector. The model represents meaning with numbers.'
        doc['scenes']=[{**copy.deepcopy(row),'uid':str(i)} for i in range(3)]
        plan=plan_document(doc)
        self.assertEqual([r['view'] for r in plan['scenes']],['overview','detail','overview'])
        self.assertEqual(plan['scenes'][1]['transition'],'continue')
        self.assertTrue(plan['warnings'])
        self.assertTrue(all(o in row['narration'].lower() for o in plan['scenes'][0]['objects']))
        timed=timed_plan(plan['scenes'][0],[{'start':0},{'start':3}])
        self.assertEqual(timed['at'],[0,3])
        row['narration']='The library opens early each morning.';doc['scenes']=[row]
        self.assertEqual(plan_document(doc)['scenes'][0]['kind'],'fallback')


class DeleteHTTPTests(unittest.TestCase):
    setUp=test_editor.EditorHTTPTests.setUp
    tearDown=test_editor.EditorHTTPTests.tearDown
    request=test_editor.EditorHTTPTests.request

    def test_reopen_removes_acceptance_without_deleting_content(self):
        store=self.server.editor_store;p=store.create('Disposable test')
        p['accepted_export']={'content':'test','sha256':'test'}
        write_json_atomic(store.folder(p['id'])/'project.json',p)
        code,result=self.request(f"/api/projects/{p['id']}/reopen",{'revision':p['revision']})
        self.assertEqual(code,200)
        self.assertNotIn('accepted_export',result)
        self.assertTrue(store.folder(p['id']).exists())

    def test_workspace_delete_requires_confirmation_and_removes_children(self):
        store=self.server.editor_store;p=store.create('Disposable test')
        w=self.server.editor_jobs.workspaces.for_project(p['id'])
        route=f"/api/workspaces/{w['id']}/delete"
        self.assertEqual(self.request(route,{})[0],400)
        self.assertEqual(self.request(route,{'confirmation':'DELETE'})[0],200)
        self.assertFalse(store.folder(p['id']).exists())
        self.assertNotIn(w['id'],[w['id'] for w in self.server.editor_jobs.workspaces.list()])

    def test_delete_requires_confirmation_and_revision(self):
        store=self.server.editor_store
        p=store.create('Disposable test')
        code,_=self.request(f"/api/projects/{p['id']}/delete",{'revision':p['revision']})
        self.assertEqual(code,400)
        code,_=self.request(f"/api/projects/{p['id']}/delete",{'revision':p['revision']+1,'confirmation':'DELETE'})
        self.assertEqual(code,409)
        self.assertTrue(store.folder(p['id']).exists())
        code,_=self.request(f"/api/projects/{p['id']}/delete",{'revision':p['revision'],'confirmation':'DELETE'})
        self.assertEqual(code,200)
        self.assertFalse(store.folder(p['id']).exists())
