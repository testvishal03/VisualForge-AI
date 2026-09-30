import json
from pathlib import Path


def validate_source(data: object) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ValueError("Scene JSON requires a non-empty title.")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Scene JSON requires at least one scene.")
    ids = set()
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {index} must be an object.")
        scene_id = scene.get("id")
        if type(scene_id) is not int or abs(scene_id) > 9007199254740991 or scene_id in ids:
            raise ValueError(f"Scene {index} requires a unique safe integer id.")
        ids.add(scene_id)
        for field in ("headline", "narration"):
            if not isinstance(scene.get(field), str) or not scene[field].strip():
                raise ValueError(f"Scene {scene_id}: {field} must be a non-empty string.")
        if not isinstance(scene.get("body"), str):
            raise ValueError(f"Scene {scene_id}: body must be a string.")
    return data


def load_source(path: Path) -> dict:
    try:
        return validate_source(json.loads(path.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot load scene data {path}: {exc}") from exc
