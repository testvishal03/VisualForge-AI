"""Conservative editorial checks, not an automated fact checker."""
import re
from difflib import SequenceMatcher

from backend.schemas.video_schema import Scene, VideoScript, words


def scene_issues(scene: Scene, previous: list[Scene], topic: str = '') -> list[dict]:
    issues = []
    def add(code, message, severity="warning"):
        issues.append({"scene": scene.id, "code": code, "severity": severity, "message": message})
    summary = bool(re.search(r"takeaway|summary|conclusion|recap|review|overview", scene.headline, re.I))
    if not summary:
        sentences = {s.strip().casefold() for s in re.split(r"(?<=[.!?])\s+", scene.narration) if len(words(s)) >= 10}
        for old in previous:
            old_sentences = {s.strip().casefold() for s in re.split(r"(?<=[.!?])\s+", old.narration)}
            if sentences & old_sentences or SequenceMatcher(None, scene.narration.lower(), old.narration.lower()).ratio() > .82:
                add("repeated_explanation", "Explain a new point instead of repeating an earlier explanation.", "error")
                break
    quoted_example = any(len(words(m[0])) >= 2 for m in re.finditer(r'''(?<!\w)["'“‘][^"'“”‘’\n]{3,100}["'”’](?!\w)''', scene.narration))
    if re.search(r"example|case study", scene.headline, re.I) and not quoted_example and not re.search(
        r"\b(?:like|such as|imagine|for example|person|student|teacher|customer|designer|writer|user|assistant|model|bot|developer|engineer|system)\b", scene.narration, re.I
    ):
        add("weak_example", "Give a concrete person, object, or task to illustrate this example.", "error")
    if len(words(scene.narration)) > 45:
        add("long_narration", "Narration exceeds the preferred 45-word target.")
    if re.search(r'\b(?:as long as you like|unlimited time|forever)\b', scene.narration, re.I) and re.search(r'\b(?:must|deadline|on time|due date)\b', scene.narration, re.I):
        add('conflicting_conditions', 'Review the unlimited-time statement alongside its deadline or obligation; these conditions may contradict each other.')
    if re.search(r"\b(?:revolutioniz\w*|amazing|game.chang\w*|incredible)\b", scene.body + " " + scene.narration, re.I):
        add("promotional_language", "Review promotional wording for a neutral educational tone.")
    if re.search(r"mechanism|how .*works", scene.headline, re.I) and not re.search(
        r"\b(?:first|then|by|learn\w*|train\w*|process\w*|step\w*)\b", scene.narration, re.I
    ):
        add("shallow_mechanism", "Review whether the narration explains how the process works.")

    if re.search(r"mechanism|how.*works|process", scene.headline, re.I) and not re.search(
        r"\b(?:because|so that|which means|therefore|as a result|this causes|this means|leading to)\b", scene.narration, re.I
    ):
        add("shallow_mechanism_no_causation", "Mechanism scenes should explain cause and effect. Add why or how this leads to the next step.")

    if re.search(r"\b(language model|llm|neural|ai model|transformer)\b", topic + " " + scene.headline + " " + scene.narration, re.I):
        for m in re.finditer(r"\b(understands?|knows?|thinks?|believes?|feels?|wants?|decides?)\b", scene.narration, re.I):
            preceding = scene.narration[:m.start()]
            last_words = re.findall(r'\b\w+\b', preceding)[-5:]
            if not any(re.match(r"^(not|never|doesn't|cannot)$", w, re.I) for w in last_words):
                add("anthropomorphic_ai", "Avoid claiming the model understands or knows things — describe what the computation does instead.")
                break

    return issues


def review_video(video: VideoScript) -> dict:
    previous = []
    issues = []
    for scene in video.scenes:
        issues.extend(scene_issues(scene, previous, video.topic))
        previous.append(scene)
    return {"status": "needs_review" if issues else "checks_passed", "issues": issues,
            "fact_check": "not_performed", "notice": "Heuristics cannot establish factual accuracy. Review before publishing."}
