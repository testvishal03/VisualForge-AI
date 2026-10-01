from backend.tests.render_stubs import stub_output, stub_props
import copy
import json
import unittest
from backend.tests import test_storyboard
from backend.services.episode_review import review, candidate, decide
from backend.services.scene_cache import segments, intact
from backend.services.run_state import fingerprint,file_hash
from backend.services.script_generator import write_json_atomic


class EpisodeReviewTests(unittest.TestCase):
    setUp=test_storyboard.StoryboardTests.setUp

    def seed_candidate(self):
        p=self.store.load(self.p['id']);scene=p['document']['scenes'][0]
        clip=self.store.folder(p['id'])/'candidate.mp4';clip.write_bytes(b'verified fixture')
        visual=copy.deepcopy(scene['visual']);visual['motion']='focus'
        record={'uid':scene['uid'],'base':fingerprint(p['document']),'revision':p['revision'],'visual':visual,'file':clip.name,'sha256':file_hash(clip)}
        write_json_atomic(self.store.folder(p['id'])/'visual-candidate.json',record)
        return p,record

    def test_discard_preserves_every_scene_and_approval(self):
        self.store.approve_storyboard(self.p['id'],1)
        p,_=self.seed_candidate();decide(self.jobs,p,False)
        self.assertEqual(self.store.load(p['id']),p)
        self.assertIsNone(candidate(self.jobs,p))

    def test_accept_changes_only_the_visual_and_preserves_approved_narration(self):
        self.store.approve_storyboard(self.p['id'],1)
        p,record=self.seed_candidate();after=decide(self.jobs,p,True)
        self.assertEqual(after['document']['scenes'][0]['visual'],record['visual'])
        self.assertEqual(after['document']['scenes'][1:],p['document']['scenes'][1:])
        self.assertEqual(after['document']['scenes'][0]['narration'],p['document']['scenes'][0]['narration'])
        self.assertEqual(after['storyboard_approved'],fingerprint(after['document']))

    def test_stale_and_tampered_candidates_cannot_be_accepted(self):
        p,_=self.seed_candidate();changed=self.store.save(p['id'],p['revision'],p['document'])
        with self.assertRaises(ValueError):decide(self.jobs,changed,True)
        p,record=self.seed_candidate();(self.store.folder(p['id'])/record['file']).write_bytes(b'changed')
        with self.assertRaises(ValueError):decide(self.jobs,p,True)

    def test_timeline_marks_estimates_and_adds_real_bookend_offset(self):
        result=self.jobs.present(self.p)
        report=review(result)
        self.assertFalse(report['measured']);self.assertEqual(report['scenes'][0]['start'],3)
        self.assertEqual(len(report['scenes']),len(self.p['document']['scenes']))
        self.assertTrue(all(s['seconds']>0 for s in report['scenes']))

    def test_frame_cache_invalidates_edited_scene_and_transition_neighbors(self):
        rows=[{'scene':{'id':i,'body':str(i)},'from':i*30,'durationInFrames':30} for i in range(5)]
        timeline={'scenes':rows,'introFrames':0,'outroFrames':0,'outroFrom':150}
        old=segments({'title':'Test'},timeline,'renderer','draft')
        changed=copy.deepcopy(timeline);changed['scenes'][2]['scene']['body']='Updated'
        new=segments({'title':'Test'},changed,'renderer','draft')
        self.assertEqual([i for i in range(5) if old[i]['key']!=new[i]['key']],[1,2,3])
        self.assertNotEqual(old[0]['key'],segments({'title':'Test'},timeline,'new renderer','draft')[0]['key'])
        self.assertNotEqual(old[0]['key'],segments({'title':'Test'},timeline,'renderer','final')[0]['key'])

    def test_corrupt_cached_clip_is_not_reused(self):
        root=self.store.folder(self.p['id']);(root/'cache.mp4').write_bytes(b'original')
        write_json_atomic(root/'cache.json',{'sha256':file_hash(root/'cache.mp4'),'frames':30})
        self.assertIsNotNone(intact(root,'cache'))
        (root/'cache.mp4').write_bytes(b'corrupt');self.assertIsNone(intact(root,'cache'))

    def test_thumbnail_failure_does_not_replace_previous_published_scene(self):
        from pathlib import Path
        from unittest.mock import patch
        from backend.services.incremental_audio import generate_incremental
        from backend.tests.test_pipeline import fake_speech
        p=self.store.load(self.p['id']);uid=p['document']['scenes'][0]['uid'];folder=self.store.folder(p['id'])
        published=folder/f'motion-{uid}.mp4';published.write_bytes(b'previous verified clip')
        def stage(script,args,**kwargs):
            if script.name=='generate_audio.py':generate_incremental(Path(args[1]),Path(args[3]),self.root/'renderer/public',synthesizer=fake_speech,directed=True)
        def render(command,**kwargs):stub_output(command).write_bytes(b'new unpublished clip')
        with patch('backend.services.editor_jobs.python_stage',side_effect=stage),patch('backend.services.editor_jobs.execute',side_effect=render),patch('backend.services.scene_cache.thumbnails',side_effect=ValueError('Thumbnail fixture failure')):
            with self.assertRaisesRegex(ValueError,'Thumbnail'):self.jobs._perform(p,'motion',uid,'',folder)
        self.assertEqual(published.read_bytes(),b'previous verified clip')


if __name__=='__main__':unittest.main()
