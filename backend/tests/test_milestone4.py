import json
from pathlib import Path
import tempfile
import unittest
import sys
import time
from contextlib import redirect_stderr
import io
from unittest.mock import patch

from backend.schemas.video_schema import Scene, VideoScript
from backend.services.quality import review_video, scene_issues
from backend.services.run_state import RunState, fingerprint, run_lock
from backend.services.script_generator import generate_video_script
from backend.services.visuals import build_visuals, ProcessLabels
from backend.services.process_runner import execute, python_stage
from backend.tests.test_script_generation import FakeLLM, valid_script, draft_responses


class ResumeTests(unittest.TestCase):
    def test_cli_rejects_invalid_input_and_missing_prerequisites_before_inference(self):
        from backend.scripts.generate_video import main
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(['   ']), 1)
            self.assertEqual(main(['Topic', '--stage-timeout', '0']), 1)
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                cli = folder/'renderer/node_modules/@remotion/cli/remotion-cli.js'
                cli.parent.mkdir(parents=True)
                cli.touch()
                with patch('backend.scripts.generate_video.ROOT', folder), patch('backend.scripts.generate_video.node_executable', return_value='node'):
                    self.assertEqual(main(['Topic']), 1)
                self.assertFalse((folder/'data').exists())

    def test_subprocess_timeout_stops_stage_and_keeps_log(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            marker = folder/'should-not-exist'
            with self.assertRaises(TimeoutError):
                execute([sys.executable, '-u', '-c', 'import time,sys; from pathlib import Path; print("started", flush=True); time.sleep(3); Path(sys.argv[1]).write_text("late")', marker], cwd=folder, log=folder/'stage.log', timeout=1)
            time.sleep(2.2)
            self.assertFalse(marker.exists())
            self.assertIn('started', (folder/'stage.log').read_text())

    def test_stage_worker_records_memory_and_exit_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            script = folder/'work.py'
            script.write_text('print("local stage finished")')
            root = Path(__file__).resolve().parents[2]
            metrics = python_stage(script, [], root=root, folder=folder, name='test', timeout=20)
            self.assertGreater(metrics['peak_working_set_bytes'], 0)
            script.write_text('raise RuntimeError("intentional failure")')
            with self.assertRaises(RuntimeError):
                python_stage(script, [], root=root, folder=folder, name='test', timeout=20)
            self.assertIn('intentional failure', (folder/'logs/test.log').read_text())

    def test_verified_outputs_reused_and_tampering_regenerated(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            artifact = folder/'output.txt'
            calls = []
            def action():
                calls.append(1)
                artifact.write_text('valid')
            manager = RunState(folder, progress=lambda _: None)
            manager.stage('script', 'key', action, [artifact])
            RunState(folder, progress=lambda _: None).stage('script', 'key', action, [artifact])
            self.assertEqual(len(calls), 1)
            artifact.write_text('tampered')
            RunState(folder, progress=lambda _: None).stage('script', 'key', action, [artifact])
            self.assertEqual(len(calls), 2)
            RunState(folder, progress=lambda _: None).stage('script', 'new-settings', action, [artifact])
            self.assertEqual(len(calls), 3)

    def test_failure_then_resume_keeps_previous_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source, video = folder/'source', folder/'video'
            manager = RunState(folder, progress=lambda _: None)
            manager.stage('script', 'a', lambda: source.write_text('saved') and None, [source])
            def interrupt():
                raise KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                manager.stage('render', 'b', interrupt, [video])
            self.assertEqual(json.loads((folder/'run.json').read_text())['status'], 'interrupted')
            resumed = RunState(folder, progress=lambda _: None)
            resumed.stage('script', 'a', lambda: self.fail('Script must not run again'), [source])
            resumed.stage('render', 'b', lambda: video.write_text('rendered') and None, [video])
            self.assertEqual(resumed.reused, ['script'])
            self.assertEqual(resumed.executed, ['render'])

    def test_missing_output_not_marked_complete_and_retries_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            calls = []
            with self.assertRaises(ValueError):
                RunState(folder, progress=lambda _: None).stage('render', 'key', lambda: calls.append(1), [folder/'missing'], attempts=2)
            self.assertEqual(len(calls), 2)
            self.assertEqual(json.loads((folder/'run.json').read_text())['stages']['render']['status'], 'failed')

    def test_lock_prevents_same_run_concurrently_and_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with run_lock(folder):
                with self.assertRaises(ValueError):
                    with run_lock(folder):
                        self.fail('second lock acquired')
            with run_lock(folder):
                pass

    def test_content_stage_resumes_valid_fields_after_late_failure(self):
        good = valid_script()
        responses = draft_responses(good)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            output = folder/'video.json'
            checkpoint = folder/'drafts'
            with self.assertRaises(ValueError):
                generate_video_script(good['topic'], output, .5, llm=FakeLLM(responses[:4]+['bad']),
                                      checkpoint_dir=checkpoint, attempts=1)
            self.assertFalse(output.exists())
            remaining = FakeLLM(responses[4:])
            result = generate_video_script(good['topic'], output, .5, llm=remaining, checkpoint_dir=checkpoint)
            self.assertEqual(result.model_dump(), good)
            self.assertEqual(len(remaining.prompts), len(responses)-4)
            no_inference = FakeLLM([])
            generate_video_script(good['topic'], output, .5, llm=no_inference, checkpoint_dir=checkpoint)
            self.assertEqual(no_inference.prompts, [])

    def test_corrupt_field_checkpoint_is_regenerated(self):
        good = valid_script()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            generate_video_script(good['topic'], folder/'video.json', .5, llm=FakeLLM(draft_responses(good)), checkpoint_dir=folder/'drafts')
            cache = next((folder/'drafts').glob('scene-1-body-*.json'))
            cache.write_text('{broken')
            engine = FakeLLM([{'body': good['scenes'][0]['body']}])
            generate_video_script(good['topic'], folder/'video.json', .5, llm=engine, checkpoint_dir=folder/'drafts')
            self.assertEqual(len(engine.prompts), 1)


class QualityVisualTests(unittest.TestCase):
    def test_quoted_concrete_input_is_an_example_without_keyword_marker(self):
        scene = Scene(**valid_script()['scenes'][0]).model_copy(update={'headline':'An example', 'narration':"When Sarah types 'bake a cake with chocolate', the model splits the input into tokens and uses those tokens as context."})
        self.assertFalse(any(i['code']=='weak_example' for i in scene_issues(scene, [])))

    def test_weak_example_is_targeted_error(self):
        scene = Scene(**valid_script()['scenes'][0]).model_copy(update={'headline': 'An example', 'narration': 'This approach provides many benefits for different situations. It supports learning and helps people do things more efficiently.'})
        self.assertTrue(any(i['code']=='weak_example' and i['severity']=='error' for i in scene_issues(scene, [])))

    def test_repeated_sentence_detected_but_summary_allowed(self):
        first = Scene(**valid_script()['scenes'][0])
        second = Scene(**valid_script()['scenes'][1]).model_copy(update={'narration': first.narration.split('. ')[0]+'. Returning materials helps other visitors access books.'})
        self.assertTrue(any(i['code']=='repeated_explanation' for i in scene_issues(second, [first])))
        self.assertFalse(any(i['code']=='repeated_explanation' for i in scene_issues(second.model_copy(update={'headline':'Final Takeaway'}), [first])))

    def test_warnings_reported_without_claiming_fact_check(self):
        video = VideoScript.model_validate(valid_script())
        video.scenes[0].narration = video.scenes[0].narration.replace('A library', 'An amazing library')
        review = review_video(video)
        self.assertEqual(review['status'], 'needs_review')
        self.assertEqual(review['fact_check'], 'not_performed')

    def test_process_labels_retry_and_safe_fallback(self):
        video = VideoScript.model_validate(valid_script())
        video.scenes[1].headline = 'How the process works'
        engine = FakeLLM([{'items':['One']}, {'items':['Choose a book','Borrow the book','Return it on time']}])
        plan = build_visuals(video, engine=engine)
        self.assertEqual(plan['scenes'][1]['kind'], 'process')
        self.assertEqual(len(engine.prompts), 2)
        fallback = build_visuals(video, engine=FakeLLM(['bad']*3))
        self.assertEqual(fallback['scenes'][1]['kind'], 'explanation')
        self.assertEqual(len(fallback['warnings']), 1)

    def test_process_labels_reject_duplicates_and_excess_text(self):
        for items in [['Same']*3, ['word '*15,'Two','Three']]:
            with self.assertRaises(ValueError):
                ProcessLabels(items=items)


if __name__ == '__main__':
    unittest.main()
