from backend.tests.render_stubs import cached as cached_render_stub
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.schemas.video_schema import VideoScript

from backend.services.director import sentences, script_to_video, build_direction, timed_visual, direct_scene
from backend.services.editor_store import EditorStore, document_from_video, validate_document
from backend.services.editor_jobs import EditorJobs
from backend.services.incremental_audio import generate_incremental, cached_speech
from backend.tests.test_pipeline import fake_speech
from backend.llm.prompts import build_video_prompt
from backend.services.quality import review_video


SCRIPT = '''A library connects readers with books and reliable information. Its catalog helps visitors locate a title, while librarians can guide questions about unfamiliar subjects.

First, search the catalog to find an interesting book. Next, use the shelf location to collect your chosen title. Finally, borrow the book with your membership card and note its return date.

Printed books work without batteries and can be shared in person. In contrast, digital books can provide adjustable text and remote access on compatible devices.

Access to a shared collection depends on readers returning borrowed books. Returning a title on time lets another reader use the same copy without buying it.

Remember that a library combines organized collections with helpful people. Search the catalog, ask for guidance when needed, and return borrowed materials for the next visitor.'''


class DirectorTests(unittest.TestCase):
    def test_script_preserves_narration_and_extracts_supported_diagrams(self):
        video = script_to_video('How a library works', SCRIPT)
        self.assertEqual(' '.join(s.narration for s in video.scenes), ' '.join(SCRIPT.split()))
        plan = build_direction(video)
        self.assertEqual([s['kind'] for s in plan['scenes']], ['title','process','comparison','relationship','takeaway'])
        self.assertEqual(plan['scenes'][1]['cues'], [0,1,2])
        self.assertEqual(plan['scenes'][3]['cues'], [0,0])
        self.assertIn('depends on', plan['scenes'][3]['items'][1])
        self.assertEqual(video.scenes[1].headline,'Search the catalog to find an interesting book')
        self.assertEqual(video.scenes[2].headline,'Printed books work without batteries')
        validate_document(document_from_video(video,plan))

    def test_script_without_title_gets_an_extractive_title(self):
        video=script_to_video(None,SCRIPT)
        self.assertEqual(video.title,video.scenes[0].headline)
        self.assertEqual(video.topic,video.title)

    def test_short_prompt_does_not_require_six_separate_teaching_sections(self):
        self.assertIn('three core points',build_video_prompt('Libraries',.5))
        self.assertNotIn('benefits, limitations, one final takeaway',build_video_prompt('Libraries',.5))
        self.assertIn('benefits, limitations, one final takeaway',build_video_prompt('Libraries',2))

    def test_conflicting_model_claim_is_flagged_without_rewriting_narration(self):
        video=script_to_video('Library',SCRIPT)
        video.scenes[2].narration='You can keep a book for as long as you like, but you must return it on time.'
        self.assertIn('conflicting_conditions',[i['code'] for i in review_video(video)['issues']])
        self.assertIn('as long as you like',video.scenes[2].narration)

    def test_internal_but_does_not_compare_unrelated_sentences(self):
        video=script_to_video('Library',SCRIPT)
        scene=video.scenes[2]
        scene.headline='Borrowing example'
        scene.narration='First, visit the circulation desk. Next, ask about borrowing a book. You can borrow a book, but you must return it by its due date.'
        self.assertEqual(direct_scene(scene,2,5)['kind'],'example')

    def test_bad_script_is_rejected_without_truncating(self):
        for value in ['', 'word '*4001, ('word '*61)+'.\n\n'+SCRIPT]:
            with self.assertRaises(ValueError): script_to_video('Test',value)
        self.assertEqual(sentences('Dr. Smith reads a book. Then she returns it.'), ['Dr. Smith reads a book.', 'Then she returns it.'])

    def test_measured_beats_cache_reuse_and_corruption_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source.json'; output=root/'audio.json'
            video=script_to_video('Library',SCRIPT);source.write_text(video.model_dump_json())
            calls=[]
            def synth(text,path,voice):
                calls.append(text);fake_speech(text,path,voice)
            data=generate_incremental(source,output,root/'public',synthesizer=synth,directed=True)
            second=data['scenes'][1]
            self.assertAlmostEqual(second['duration'],3.56)  # 3 x 1 s sentences + two 0.28 s pauses
            self.assertEqual([b['start'] for b in second['beats']], [0,1.28,2.56])
            visual=timed_visual(build_direction(video)['scenes'][1],second['narration'],second['beats'])
            self.assertEqual(visual['revealAt'],[0,1.28,2.56])
            count=len(calls)
            again=generate_incremental(source,output,root/'public',synthesizer=synth,directed=True)
            self.assertEqual(again['cache']['generated_scene_ids'],[]);self.assertEqual(len(calls),count)
            self.assertIsNone(cached_speech(root/'public',second['narration']))
            record=root/'public'/second['audio']; sidecar=record.with_suffix('.json')
            bad=json.loads(sidecar.read_text());bad['beats'][1]['start']=99;sidecar.write_text(json.dumps(bad))
            repaired=generate_incremental(source,output,root/'public',synthesizer=synth,directed=True)
            self.assertEqual(repaired['cache']['generated_scene_ids'],[2])

    def test_narration_edit_replans_only_affected_scene(self):
        with tempfile.TemporaryDirectory() as directory:
            store=EditorStore(Path(directory));video=script_to_video('Library',SCRIPT)
            doc=document_from_video(video,build_direction(video)); project=store.create(video.topic,doc,source={'mode':'script'})
            before=copy.deepcopy(doc)
            doc['scenes'][1]['narration']='A librarian can help readers locate useful reference material. For example, a student researching local history can ask which newspapers are available in the collection.'
            saved=store.save(project['id'],1,doc)['document']
            self.assertEqual(saved['scenes'][1]['visual']['kind'],'example')
            for i in [0,2,3,4]: self.assertEqual(saved['scenes'][i],before['scenes'][i])

    def test_automatic_prompt_job_runs_all_stages_and_can_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'renderer/src').mkdir(parents=True);(root/'renderer/remotion.config.ts').write_text('fixture')
            store=EditorStore(root/'projects');project=store.create('Library',source={'mode':'prompt','text':'Library','minutes':.5})
            jobs=EditorJobs(root,store); calls=[]
            def stage(script,args,**kwargs):
                calls.append(script.name)
                if script.name=='generate_script.py':
                    Path(args[args.index('--output')+1]).write_text(script_to_video('Library',SCRIPT).model_dump_json())
                elif script.name=='generate_audio.py':
                    generate_incremental(Path(args[1]),Path(args[3]),root/'renderer/public',synthesizer=fake_speech,directed=True)
                elif script.name=='plan_visuals.py':
                    video=VideoScript.model_validate_json(Path(args[0]).read_text())
                    plan=build_direction(video)
                    for row in plan['scenes']: row['planned']=True
                    Path(args[1]).write_text(json.dumps(plan))
                else:
                    props=json.loads(Path(args[2]).read_text())['videoData']
                    self.assertEqual(props['scenes'][1]['visual']['revealAt'],[0,1.28,2.56])
                    Path(args[4]).write_text('{"fullDecode":"fixture"}')
            def execute(command,**kwargs): Path(command[4]).write_bytes(b'fixture MP4')
            with patch('backend.services.editor_jobs.python_stage',side_effect=stage),patch('backend.services.editor_jobs.execute',side_effect=execute),patch('backend.services.editor_jobs.node_executable',return_value='node'),patch('backend.services.scene_cache.render_cached',side_effect=cached_render_stub),patch('backend.services.scene_cache.thumbnails'):
                jobs.start(project['id'],'generate');jobs.thread.join(10)
                self.assertEqual(jobs.status()['status'],'complete',jobs.status())
                self.assertEqual(calls,['generate_script.py','plan_visuals.py','generate_audio.py','validate_render.py'])
                saved=store.load(project['id']);self.assertTrue(saved['render']);self.assertTrue(jobs.present(saved)['video_url'])
                jobs.start(project['id'],'generate');jobs.thread.join(10)
                self.assertEqual(len(calls),4)
                self.assertIn('Reused',jobs.status()['message'])


if __name__=='__main__':unittest.main()
