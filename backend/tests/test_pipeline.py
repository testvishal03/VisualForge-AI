import copy
import json
from pathlib import Path
import tempfile
import unittest
import wave

from backend.scripts.generate_audio import generate, PROJECT_ROOT
from backend.utils.audio_duration import audio_duration
from backend.utils.scene_data import load_source, validate_source


def fake_speech(text, path, voice):
    with wave.open(str(path), "wb") as audio:
        audio.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x01\x00" * 24000)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.source = load_source(PROJECT_ROOT / "data/video.json")

    def test_schema(self):
        self.assertGreater(len(self.source["scenes"]), 0)
        for value in [None, "", "   "]:
            invalid = copy.deepcopy(self.source)
            invalid["scenes"][0]["narration"] = value
            with self.assertRaisesRegex(ValueError, "narration"):
                validate_source(invalid)
        invalid = copy.deepcopy(self.source)
        invalid["scenes"][1]["id"] = invalid["scenes"][0]["id"]
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_source(invalid)
        with self.assertRaisesRegex(ValueError, "at least one"):
            validate_source({"title": "Empty", "scenes": []})

    def test_generation_and_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "generated.json"
            args = (PROJECT_ROOT / "data/video.json", output, root / "public")
            first = generate(*args, synthesizer=fake_speech)
            second = generate(*args, synthesizer=fake_speech)
            self.assertEqual(first, second)
            self.assertEqual(json.loads(output.read_text()), first)
            for scene in first["scenes"]:
                self.assertEqual(scene["duration"], 1)
                self.assertEqual(audio_duration(root / "public" / scene["audio"]), 1)

    def test_failure_does_not_publish_partial_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "generated.json"
            output.write_text("previous metadata")
            def fail(text, path, voice):
                raise RuntimeError("TTS failure")
            with self.assertRaisesRegex(RuntimeError, "TTS failure"):
                generate(PROJECT_ROOT / "data/video.json", output, root / "public", synthesizer=fail)
            self.assertEqual(output.read_text(), "previous metadata")

    def test_missing_audio_invalid_folder_and_malformed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "WAV duration"):
                generate(PROJECT_ROOT / "data/video.json", root / "out.json", root / "public", synthesizer=lambda *args: None)
            invalid = root / "bad.json"
            invalid.write_text("{bad json")
            with self.assertRaisesRegex(ValueError, "Cannot load scene data"):
                load_source(invalid)
            file = root / "not-a-folder"
            file.write_text("file")
            with self.assertRaises(OSError):
                generate(PROJECT_ROOT / "data/video.json", root / "out.json", file, synthesizer=fake_speech)
            with self.assertRaisesRegex(ValueError, "WAV duration"):
                audio_duration(invalid)

    def test_real_generated_artifacts(self):
        generated = json.loads((PROJECT_ROOT / "data/video.generated.json").read_text())
        self.assertEqual(len(generated["scenes"]), len(self.source["scenes"]))
        # The narration WAVs are a local, git-ignored cache; a fresh checkout has to generate them first.
        if not all((PROJECT_ROOT / "renderer/public" / scene["audio"]).is_file() for scene in generated["scenes"]):
            self.skipTest("demo narration not generated here; run backend/scripts/generate_audio.py")
        for source, scene in zip(self.source["scenes"], generated["scenes"]):
            self.assertEqual(scene["narration"], source["narration"])
            duration = audio_duration(PROJECT_ROOT / "renderer/public" / scene["audio"])
            self.assertGreater(duration, 0)
            self.assertEqual(duration, scene["duration"])


if __name__ == "__main__":
    unittest.main()
