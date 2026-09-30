import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from backend.llm.gguf_llm import GGUFLLM, create_local_llm
from backend.services.script_generator import generate_video_script
from backend.tests.test_script_generation import FakeLLM, valid_script, outline, draft_responses
from backend.scripts.setup_gguf import download, download_chunks


class GGUFTests(unittest.TestCase):
    def engine(self):
        return GGUFLLM(config={'runtime_version': 'test'})

    def test_schema_and_limits_reach_local_runtime(self):
        engine = self.engine()
        engine._load = Mock()
        engine._request = Mock(return_value={'choices': [{'finish_reason': 'stop', 'message': {'content': '{"body":"Books"}'}}], 'usage': {'completion_tokens': 7}})
        schema = {'type': 'object', 'properties': {'body': {'type': 'string'}}}
        self.assertEqual(engine.generate_json('Explain books', 180, 0, schema), '{"body":"Books"}')
        payload = engine._request.call_args.args[1]
        self.assertEqual(payload['response_format']['schema'], schema)
        self.assertEqual(payload['max_tokens'], 180)
        self.assertEqual(engine.last_token_count, 7)
        with self.assertRaises(ValueError):
            engine.generate('bad', 100000)
        self.assertEqual(engine._load.call_count, 1)

    def test_truncated_response_is_not_accepted(self):
        engine = self.engine()
        engine._load = Mock()
        engine._request = Mock(return_value={'choices': [{'finish_reason': 'length', 'message': {'content': '{'}}]})
        with self.assertRaisesRegex(RuntimeError, 'token limit'):
            engine.generate('prompt')

    def test_close_stops_only_owned_process_and_is_idempotent(self):
        engine = self.engine()
        process = Mock()
        process.poll.return_value = None
        engine.process = process
        engine.close()
        engine.close()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=10)

    def test_startup_failure_closes_worker(self):
        engine = GGUFLLM(config={'server': 'missing-server', 'model': 'missing-model'})
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            engine._load()
        self.assertIsNone(engine.process)

    def test_explicit_legacy_backend(self):
        with patch.dict('os.environ', {'VISUALFORGE_LLM': 'transformers'}):
            self.assertEqual(create_local_llm(offline=True).model_name, 'Qwen/Qwen2.5-1.5B-Instruct')
        with patch.dict('os.environ', {'VISUALFORGE_LLM': 'typo'}):
            with self.assertRaises(ValueError):
                create_local_llm()

    def test_owned_engine_closed_when_validation_fails(self):
        engine = FakeLLM(['bad'] * 3)
        engine.close = Mock()
        with tempfile.TemporaryDirectory() as directory, patch('backend.services.script_generator.create_local_llm', return_value=engine):
            with self.assertRaises(ValueError):
                generate_video_script('Library', Path(directory) / 'video.json', .5)
        engine.close.assert_called_once()

    def test_model_change_invalidates_checkpoint(self):
        good = valid_script()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            for identity in ['legacy', 'gguf']:
                # Seed a valid outline through a first attempt, then fail body generation.
                engine = FakeLLM([json.dumps(outline(good)), 'bad', 'bad', 'bad'])
                engine.cache_identity = identity
                with self.assertRaises(ValueError):
                    generate_video_script(good['topic'], directory / 'video.json', .5, llm=engine, checkpoint_dir=directory / 'drafts')
                self.assertIn('topic', engine.prompts[0])
            self.assertEqual(len(list((directory / 'drafts').glob('outline-*.json'))), 2)

    def test_schema_generation_reports_actual_profile_and_closes(self):
        engine = FakeLLM(draft_responses(valid_script()))
        engine.metadata = {'model': 'test-gguf', 'dtype': 'Q4_K_M', 'backend': 'llama.cpp'}
        engine.close = Mock()
        schemas = []
        def generate(prompt, schema=None, **kwargs):
            schemas.append(schema)
            return engine.generate(prompt, **kwargs)
        engine.generate_json = generate
        with tempfile.TemporaryDirectory() as directory, patch('backend.services.script_generator.create_local_llm', return_value=engine):
            directory = Path(directory)
            generate_video_script(valid_script()['topic'], directory / 'video.json', .5, report_path=directory / 'report.json')
            report = json.loads((directory / 'report.json').read_text())
            self.assertEqual(report['model'], 'test-gguf')
            self.assertEqual(report['dtype'], 'Q4_K_M')
        self.assertEqual(schemas[0]['properties']['scenes']['maxItems'], 3)
        self.assertEqual(schemas[0]['properties']['topic']['const'], valid_script()['topic'])
        self.assertEqual(set(schemas[1]['properties']), {'body'})
        self.assertEqual(set(schemas[2]['properties']), {'narration'})
        engine.close.assert_called_once()

    def test_partial_range_resumes_without_duplicating_bytes(self):
        data = b'abcdefgh'
        calls = []
        def transfer(command, **kwargs):
            start, end = map(int, command[command.index('--range') + 1].split('-'))
            calls.append(start)
            # Simulate a timeout after four valid bytes, then a resumed transfer.
            Path(command[command.index('--output') + 1]).write_bytes(data[start:min(end + 1, start + 4)])
            Path(command[command.index('--dump-header') + 1]).write_text(f'Content-Range: bytes {start}-{end}/{len(data)}\n')
            return Mock(returncode=28 if start == 0 else 0, stdout='206', stderr='')
        with tempfile.TemporaryDirectory() as directory, patch('backend.scripts.setup_gguf.subprocess.run', side_effect=transfer):
            partial = Path(directory) / 'model.partial'
            download_chunks('https://example.invalid/model', partial, len(data))
            self.assertEqual(partial.read_bytes(), data)
            self.assertEqual(calls, [0, 4])

    def test_checksum_failure_preserves_existing_model(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / 'model.gguf'
            model.write_bytes(b'old model')
            def bad_download(url, partial, size):
                partial.write_bytes(b'bad download')
                return []
            with patch('backend.scripts.setup_gguf.download_chunks', side_effect=bad_download):
                with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                    download('https://example.invalid/model', model, '0' * 64, 12)
            self.assertEqual(model.read_bytes(), b'old model')


if __name__ == '__main__':
    unittest.main()
