import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from pydantic import ValidationError

from backend.llm.local_llm import LocalLLM
from backend.llm.prompts import build_video_prompt, normalize_topic, scene_count
from backend.schemas.video_schema import VideoPlan, VideoScript
from backend.scripts.generate_script import main
from backend.services.json_parser import StoryboardParseError, parse_json_object
from backend.services.script_generator import generate_video_script
from backend.utils.scene_data import validate_source


def valid_script(count=3):
    return {
        "title": "How A Library Helps", "topic": "How does a library work?",
        "scenes": [{
            "id": index,
            "headline": f"Library idea {index}",
            "body": f"A library helps people discover useful information in step {index}.",
            "narration": [
                "A library organizes books by subject so visitors can find information. A catalog connects each book to its location on the shelves.",
                "Your membership card lets you borrow a book for a limited period. Returning it on time makes that copy available to the next reader.",
                "Librarians can guide a research project toward useful references. They also help readers evaluate digital resources and compare information from different sources.",
            ][(index - 1) % 3],
        } for index in range(1, count + 1)],
    }


def outline(script):
    return {"title": script["title"], "topic": script["topic"], "scenes": [
        {"id": scene["id"], "headline": scene["headline"], "point": scene["body"]}
        for scene in script["scenes"]
    ]}


def draft_responses(script):
    return [outline(script)] + [
        draft for scene in script["scenes"]
        for draft in ({"body": scene["body"]}, {"narration": scene["narration"]})
    ]


class FakeLLM:
    def __init__(self, responses):
        self.responses = iter(json.dumps(value) if isinstance(value, dict) else value for value in responses)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return next(self.responses)


class SchemaTests(unittest.TestCase):
    def test_generated_narration_teaches_directly_but_authored_scripts_are_kept(self):
        from backend.schemas.video_schema import NarrationDraft
        intro = "In this scene, we explore how a library organizes books and helps people discover useful information for their research."
        with self.assertRaisesRegex(ValidationError, "meta introductions"):
            NarrationDraft.model_validate({"narration": intro})
        data = valid_script()
        data["scenes"][0]["narration"] = intro
        VideoScript.model_validate(data)  # a pasted script keeps the author's own introduction

    def test_accuracy_guarantees_are_rejected_but_negated_limitations_are_allowed(self):
        data = valid_script()
        data["scenes"][0]["narration"] = "This system ensures accurate answers when it retrieves information. Users can depend on every response without checking any sources."
        with self.assertRaisesRegex(ValidationError, "accuracy guarantees"):
            VideoScript.model_validate(data)
        data["scenes"][0]["narration"] = "Retrieval does not guarantee accurate answers. People still need to check source quality and verify important claims before relying on the output."
        VideoScript.model_validate(data)

    def test_outline_rejects_invalid_order_empty_and_duplicate_points(self):
        plan = outline(valid_script())
        self.assertEqual(len(VideoPlan.model_validate(plan).scenes), 3)
        for mutate in [lambda d: d.update(scenes=[]),
                       lambda d: d["scenes"][0].update(id="1"),
                       lambda d: d["scenes"][1].update(id=1),
                       lambda d: d["scenes"][1].update(point=d["scenes"][0]["point"]),
                       lambda d: d["scenes"][0].update(headline="word " * 12)]:
            data = copy.deepcopy(plan)
            mutate(data)
            with self.assertRaises(ValidationError):
                VideoPlan.model_validate(data)

    def test_accepts_valid_and_preserves_milestone2_contract(self):
        video = VideoScript.model_validate(valid_script())
        self.assertEqual(validate_source(video.model_dump())["scenes"][0]["id"], 1)

    def test_rejects_missing_empty_and_unreasonable_content(self):
        mutations = [
            lambda d: d.update(scenes=[]),
            lambda d: d.update(title="  "),
            lambda d: d.update(topic=""),
            lambda d: d["scenes"][0].pop("narration"),
            lambda d: d["scenes"][0].update(narration=""),
            lambda d: d["scenes"][0].update(headline="word " * 20),
            lambda d: d["scenes"][0].update(body="x" * 181),
            lambda d: d["scenes"][0].update(narration="word " * 100 + "."),
            lambda d: d["scenes"][0].update(audio="audio/untrusted.wav"),
            lambda d: d["scenes"][0].update(duration=42),
            lambda d: d.update(fps=24),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                data = valid_script()
                mutate(data)
                with self.assertRaises(ValidationError):
                    VideoScript.model_validate(data)

    def test_rejects_invalid_ids_and_duplicate_scenes(self):
        for identifier in [0, 2, "1", True, 1.0]:
            data = valid_script()
            data["scenes"][0]["id"] = identifier
            with self.subTest(identifier=identifier), self.assertRaises(ValidationError):
                VideoScript.model_validate(data)
        for field in ["headline", "narration"]:
            data = valid_script()
            data["scenes"][1][field] = data["scenes"][0][field]
            with self.assertRaises(ValidationError):
                VideoScript.model_validate(data)


class ParserTests(unittest.TestCase):
    def test_plain_fenced_and_simple_wrappers(self):
        data = valid_script()
        raw = json.dumps(data)
        for response in [raw, f"```json\n{raw}\n```", f"Here is the result:\n{raw}\nDone."]:
            self.assertEqual(parse_json_object(response), data)

    def test_rejects_garbage_truncation_ambiguity_and_duplicate_keys(self):
        for response in ["", "nonsense", "{broken", '{"scenes": [{"id": 1}', '[]', '{} {}', '{"x":1,"x":2}', '{"x": NaN}', '{"x": Infinity}']:
            with self.subTest(response=response), self.assertRaises(StoryboardParseError):
                parse_json_object(response)

    def test_braces_in_strings_are_not_object_boundaries(self):
        self.assertEqual(parse_json_object('Result: {"text": "a } brace and \\" quote"}'), {"text": 'a } brace and " quote'})


class GeneratorTests(unittest.TestCase):
    def test_topic_guidance_does_not_leak_into_unrelated_subjects(self):
        self.assertIn("phrase bank", build_video_prompt("What is Retrieval Augmented Generation?"))
        self.assertNotIn("phrase bank", build_video_prompt("How does photosynthesis work?"))

    def test_near_duplicate_scene_is_retried_without_echoing_bad_text(self):
        good = valid_script()
        near_copy = {"narration": good["scenes"][0]["narration"].replace("A library", "The library")}
        responses = draft_responses(good)
        responses.insert(4, near_copy)
        llm = FakeLLM(responses)
        with tempfile.TemporaryDirectory() as directory:
            result = generate_video_script(good["topic"], Path(directory) / "video.json", 0.5, llm=llm)
            self.assertEqual(result.model_dump(), good)
            self.assertIn("repeats a previous scene", llm.prompts[5])
            self.assertNotIn(near_copy["narration"], llm.prompts[5])

    def test_late_scene_failure_preserves_previous_source(self):
        good = valid_script()
        llm = FakeLLM(draft_responses(good)[:4] + ["invalid", "invalid"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "video.json"
            output.write_text("previous source")
            with self.assertRaisesRegex(ValueError, "scene-2-narration after 2 attempts"):
                generate_video_script(good["topic"], output, 0.5, llm=llm, attempts=2)
            self.assertEqual(output.read_text(), "previous source")

    def test_scene_identity_is_preserved_on_retry(self):
        good = valid_script()
        responses = draft_responses(good)
        responses.insert(1, {"body": good["scenes"][0]["body"], "id": 2})
        llm = FakeLLM(responses)
        with tempfile.TemporaryDirectory() as directory:
            result = generate_video_script(good["topic"], Path(directory) / "video.json", 0.5, llm=llm)
            self.assertEqual(result.model_dump(), good)
            self.assertIn("id: Extra inputs", llm.prompts[2])

    def test_topic_and_duration_validation(self):
        self.assertEqual(normalize_topic("  Exact Topic?  "), "Exact Topic?")
        self.assertEqual(scene_count(2), 8)
        self.assertIn('"Exact Topic?"', build_video_prompt("Exact Topic?"))
        for minutes in [0, -1, float("nan"), float("inf"), 10]:
            with self.assertRaises(ValueError):
                scene_count(minutes)

    def test_cli_rejects_empty_topic_before_loading_model(self):
        for topic in ["", "  "]:
            with patch("backend.scripts.generate_script.generate_video_script") as generator, redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(main([topic]), 1)
                generator.assert_not_called()

    def test_retry_corrects_schema_and_writes_only_valid_json(self):
        good = valid_script()
        responses = draft_responses(good)
        responses.insert(4, {})
        llm = FakeLLM(responses)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "video.json"
            report = Path(directory) / "report.json"
            result = generate_video_script(good["topic"], output, 0.5, llm=llm, report_path=report)
            self.assertEqual(json.loads(output.read_text()), good)
            self.assertEqual(result.topic, good["topic"])
            self.assertIn("narration", llm.prompts[5])
            self.assertEqual(len(json.loads(report.read_text())["attempts"]), 8)
            self.assertEqual(validate_source(json.loads(output.read_text())), good)

    def test_retry_retains_all_previous_field_errors(self):
        good = valid_script()
        responses = draft_responses(good)
        responses[2:2] = [
            {"narration": "Libraries can provide helpful reference information."},
            {"narration": "In this scene, we explore how a library organizes books and helps people discover useful information for their research."},
        ]
        llm = FakeLLM(responses)
        with tempfile.TemporaryDirectory() as directory:
            generate_video_script(good["topic"], Path(directory) / "video.json", 0.5, llm=llm)
            self.assertIn("narration must contain", llm.prompts[4])
            self.assertIn("meta introductions", llm.prompts[4])

    def test_attempt_limit_preserves_previous_output(self):
        llm = FakeLLM(["bad"] * 3)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "video.json"
            output.write_text("previous valid file")
            with self.assertRaisesRegex(ValueError, "after 3 attempts"):
                generate_video_script("Topic", output, llm=llm)
            self.assertEqual(len(llm.prompts), 3)
            self.assertNotEqual(llm.prompts[1], llm.prompts[2])
            self.assertIn("Correction attempt 3", llm.prompts[2])
            self.assertEqual(output.read_text(), "previous valid file")

    def test_topic_rewrite_and_wrong_scene_count_are_rejected(self):
        good = valid_script()
        for topic, minutes in [("Another topic", 0.5), (good["topic"], 2)]:
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                generate_video_script(topic, Path(directory) / "video.json", minutes, llm=FakeLLM([json.dumps(outline(good))]), attempts=1)

    def test_output_directory_failure_precedes_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = FakeLLM([])
            with self.assertRaisesRegex(ValueError, "must be a file"):
                generate_video_script("Topic", directory, llm=engine)
            self.assertEqual(engine.prompts, [])

    def test_local_model_is_lazy_and_validates_limits(self):
        engine = LocalLLM(offline=True)
        self.assertIsNone(engine.model)
        with self.assertRaises(ValueError):
            engine.generate("prompt", max_new_tokens=100000)
        self.assertIsNone(engine.model)


if __name__ == "__main__":
    unittest.main()
