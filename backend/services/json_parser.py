"""Recover wrappers, never invent or repair missing JSON content."""
import json
import re


class StoryboardParseError(ValueError):
    pass


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise StoryboardParseError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise StoryboardParseError(f"Non-standard JSON constant: {value}")


def parse_json_object(raw: str) -> dict:
    if not isinstance(raw, str) or not raw.strip():
        raise StoryboardParseError("The model returned an empty response.")
    if len(raw) > 64000:
        raise StoryboardParseError("Model response exceeds the 64 KB limit.")
    text = raw.strip().lstrip("\ufeff")
    fenced = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    decoder = json.JSONDecoder(object_pairs_hook=_pairs, parse_constant=_constant)
    try:
        result = decoder.decode(text)
    except json.JSONDecodeError:
        # Only the first opening brace is considered. Do not salvage inner
        # objects from a truncated outer object or choose between two answers.
        start = text.find("{")
        if start < 0 or "[" in text[:start]:
            raise StoryboardParseError("No complete JSON object found; return one object, not a list or prose.") from None
        try:
            result, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError as exc:
            raise StoryboardParseError(f"Invalid or truncated JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
        suffix = text[end:].strip()
        if any(char in suffix for char in "{}[]") or text[:start].strip().startswith(('{', '[')):
            raise StoryboardParseError("Ambiguous response: expected one complete JSON object.")
    if not isinstance(result, dict):
        raise StoryboardParseError("Storyboard must be a JSON object.")
    return result
