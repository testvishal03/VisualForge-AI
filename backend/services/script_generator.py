import hashlib
import json
from pathlib import Path
import tempfile
import time
from difflib import SequenceMatcher
from typing import Callable, Protocol

from pydantic import ValidationError

from backend.llm.local_llm import MODEL_NAME, MODEL_REVISION, SEED
from backend.llm.gguf_llm import create_local_llm
from backend.llm.prompts import SYSTEM_PROMPT, build_retry_prompt, build_video_prompt, build_scene_prompt, normalize_topic, scene_count
from backend.schemas.video_schema import BodyDraft, NarrationDraft, Scene, VideoPlan, VideoScript, words
from backend.services.json_parser import parse_json_object
from backend.services.quality import scene_issues


class TextGenerator(Protocol):
    def generate(self, prompt: str, max_new_tokens: int = 1800, temperature: float = 0.0) -> str: ...


def write_json_atomic(output: Path, data: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not output.is_file():
        raise ValueError(f"Output must be a file: {output}")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, suffix=".tmp", delete=False) as stream:
            temp_path = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        # Windows readers and antivirus scanners can briefly hold the destination.
        # Keep the original intact and retry only sharing/access errors, bounded to 1s.
        import time
        for attempt in range(6):
            try:
                temp_path.replace(output)
                break
            except PermissionError as exc:
                if attempt == 5 or getattr(exc, 'winerror', None) not in (5, 32, 33):
                    raise
                time.sleep(.2)
    except OSError as exc:
        raise ValueError(f"Cannot save generated script to {output}: {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def generate_video_script(topic: str, output_path: str | Path, target_minutes: float = 2.0, *,
                          llm: TextGenerator | None = None, attempts: int = 3,
                          max_new_tokens: int = 1800, temperature: float = 0.0,
                          offline: bool = False, threads: int = 2, report_path: Path | None = None,
                          diagnostics_dir: Path | None = None,
                          checkpoint_dir: Path | None = None,
                          audience: str = 'beginner to intermediate',
                          on_progress: Callable[[str], None] | None = None) -> VideoScript:
    topic = normalize_topic(topic)
    if not isinstance(audience,str) or not audience.strip() or len(audience)>160 or any(ord(c)<32 for c in audience):
        raise ValueError('Audience must be a single line of 1–160 characters')
    count = scene_count(target_minutes)
    if not 1 <= attempts <= 3:
        raise ValueError("Generation attempts must be between 1 and 3 per stage.")
    if not 128 <= max_new_tokens <= 3000 or not 0 <= temperature <= 1:
        raise ValueError("Use 128-3000 new tokens and temperature between 0 and 1.")
    output = Path(output_path)
    if report_path is not None and report_path.resolve() == output.resolve():
        raise ValueError("Script and report paths must be different.")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not output.is_file():
        raise ValueError(f"Output must be a file: {output}")
    with tempfile.TemporaryFile(dir=output.parent):
        pass
    engine = llm if llm is not None else create_local_llm(offline=offline, threads=threads, on_progress=on_progress)
    try:
        started = time.perf_counter()
        history = []

        def ask(stage: str, original: str, validator, token_limit: int, budget=None):
            cache_key = hashlib.sha256(json.dumps([original, SYSTEM_PROMPT, getattr(engine, 'cache_identity', MODEL_REVISION), temperature, max_new_tokens, token_limit, SEED], sort_keys=True).encode()).hexdigest()
            cache = checkpoint_dir / f"{stage}-{cache_key}.json" if checkpoint_dir else None
            if cache and cache.is_file():
                try:
                    cached = json.loads(cache.read_text(encoding="utf-8"))
                    result = validator(cached)
                    status='reused_with_duration_warning' if budget and len(words(result.narration))>budget[1] else 'reused'
                    history.append({"stage": stage, "status": status, "seconds": 0, "tokens": 0})
                    if on_progress:
                        on_progress(f"{stage}: reusing validated draft.")
                    return result
                except (ValueError, OSError):
                    pass  # A corrupt or newly invalid draft is regenerated, never trusted.
            prompt = original
            failures = []
            best = None
            def accept_budget_candidate():
                result, parsed, count = best
                history.append({'stage':stage,'status':'accepted_with_duration_warning','seconds':0,'tokens':0,'words':count,'preferred_max':budget[1]})
                if on_progress: on_progress(f'{stage}: keeping a valid {count}-word draft after bounded duration retries; review its measured runtime.')
                if cache: write_json_atomic(cache,parsed)
                return result
            for attempt in range(1, attempts + 1):
                if on_progress:
                    on_progress(f"{stage}: attempt {attempt}/{attempts}...")
                if hasattr(engine, 'generate_json'):
                    schema = (VideoPlan if stage == 'outline' else BodyDraft if stage.endswith('-body') else NarrationDraft).model_json_schema()
                    if stage == 'outline':
                        schema['properties']['scenes'].update(minItems=scene_count(target_minutes), maxItems=scene_count(target_minutes))
                        schema['properties']['topic']['const'] = topic
                    raw = engine.generate_json(prompt, max_new_tokens=min(max_new_tokens, token_limit), temperature=temperature, schema=schema)
                else:
                    raw = engine.generate(prompt, max_new_tokens=min(max_new_tokens, token_limit), temperature=temperature)
                if diagnostics_dir is not None:
                    diagnostics_dir.mkdir(parents=True, exist_ok=True)
                    (diagnostics_dir / f"{stage}-attempt-{attempt}.txt").write_text(raw, encoding="utf-8")
                entry = {"stage": stage, "attempt": attempt,
                         "seconds": round(getattr(engine, "last_generation_seconds", 0), 3),
                         "tokens": getattr(engine, "last_token_count", 0)}
                try:
                    parsed = parse_json_object(raw)
                    result = validator(parsed)
                except ValueError as exc:
                    failure = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors(include_input=False, include_url=False)) if isinstance(exc, ValidationError) else str(exc)
                    history.append({**entry, "status": "invalid", "error": failure[:1800]})
                    if on_progress:
                        on_progress(f"Validation failed: {failure[:400]}")
                    if attempt == attempts:
                        if best is not None: return accept_budget_candidate()
                        raise ValueError(f"No valid {stage} after {attempts} attempts. Existing output was preserved. Last error: {failure}") from exc
                    if failure not in failures:
                        failures.append(failure)
                    prompt = build_retry_prompt(original, raw, "\n".join(failures), attempt + 1)
                else:
                    if budget and len(words(result.narration))>budget[1]:
                        count=len(words(result.narration))
                        if best is None or count<best[2]: best=(result,parsed,count)
                        failure=f'This draft has {count} words. Use at most {budget[1]} words to fit the requested duration. Use one or two short sentences. Remove repetition and general encouragement.'
                        history.append({**entry,'status':'outside_word_budget','words':count})
                        if attempt>=min(attempts,2): return accept_budget_candidate()
                        if on_progress: on_progress(f'Duration rewrite: {failure}')
                        prompt=build_retry_prompt(original,raw,failure,attempt+1)
                        continue
                    history.append({**entry, "status": "valid"})
                    if cache:
                        write_json_atomic(cache, parsed)
                    return result
            raise AssertionError("unreachable")

        def validate_plan(data):
            plan = VideoPlan.model_validate(data)
            if plan.topic != topic:
                raise ValueError("topic must exactly match the supplied topic, without rewriting it")
            minimum, maximum = count, count
            if not minimum <= len(plan.scenes) <= maximum:
                raise ValueError(f"Expected {minimum}-{maximum} scenes, received {len(plan.scenes)}")
            return plan

        plan = ask("outline", build_video_prompt(topic, target_minutes, audience), validate_plan, 1000)
        from backend.services.duration import word_budget
        budget=word_budget(target_minutes,len(plan.scenes))
        if on_progress:
            on_progress(f"Outline validated: {plan.title} ({len(plan.scenes)} scenes).")
        accepted = []
        for brief in plan.scenes:
            body = ask(f"scene-{brief.id}-body", build_scene_prompt(
                topic, brief.model_dump(), "body", audience=audience,
            ), BodyDraft.model_validate, 180).body

            def validate_scene(data):
                narration = NarrationDraft.model_validate(data).narration
                scene = Scene(id=brief.id, headline=brief.headline, body=body, narration=narration)
                if any(SequenceMatcher(None, scene.narration.casefold(), old.narration.casefold()).ratio() > 0.82 for old in accepted):
                    raise ValueError("Narration repeats a previous scene; explain the current point instead")
                errors = [issue["message"] for issue in scene_issues(scene, accepted) if issue["severity"] == "error"]
                if errors:
                    raise ValueError(" ".join(errors))
                return scene

            scene = ask(f"scene-{brief.id}-narration", build_scene_prompt(
                topic, brief.model_dump(), "narration", body, budget, audience,
                teaching_plan=[s.model_dump() for s in plan.scenes],
                previous_narration=accepted[-1].narration if accepted else "",
            ), validate_scene, 300, budget=budget)
            accepted.append(scene)
            if on_progress:
                on_progress(f"Scene {scene.id} validated: {len(words(scene.narration))} narrated words.")
        video = VideoScript(title=plan.title, topic=plan.topic, scenes=accepted)
        write_json_atomic(output, video.model_dump())
        if report_path is not None:
            write_json_atomic(report_path, {
                "model": MODEL_NAME, "revision": MODEL_REVISION, "device": "cpu", "dtype": "float32",
                **getattr(engine, 'metadata', {}),
                "seed": SEED, "temperature": temperature, "do_sample": temperature > 0,
                "max_new_tokens": max_new_tokens, "outline_token_limit": min(max_new_tokens, 1000),
                "body_token_limit": min(max_new_tokens, 180), "narration_token_limit": min(max_new_tokens, 300),
                "threads": threads, "target_minutes": target_minutes,
                "strategy": "validated outline, then individually validated captions and narration; one model instance",
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "model_load_seconds": round(getattr(engine, "load_seconds", 0), 3),
                "generation_seconds": round(sum(a["seconds"] for a in history), 3),
                "generated_tokens": sum(a["tokens"] for a in history),
                "teaching_plan": plan.model_dump(),
                "attempts": history, "title": video.title, "topic": video.topic, "scenes": len(video.scenes),
                "narration_words": sum(len(words(scene.narration)) for scene in video.scenes),
                "script_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            })
        return video
    finally:
        if llm is None and hasattr(engine, 'close'):
            engine.close()
