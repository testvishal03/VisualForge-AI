"""Validate content only: the model cannot supply paths, durations or frames."""
import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


def words(text: str) -> list[str]:
    return re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", text)


class StrictContent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class Scene(StrictContent):
    id: Annotated[int, Field(ge=1, le=120)]
    headline: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    body: Annotated[str, StringConstraints(min_length=1, max_length=180)]
    narration: Annotated[str, StringConstraints(min_length=1, max_length=600)]

    @field_validator("headline")
    @classmethod
    def short_headline(cls, value: str) -> str:
        if len(words(value)) > 10:
            raise ValueError("headline must have at most 10 words; aim for fewer than 8")
        return value

    @field_validator("headline", "body", "narration")
    @classmethod
    def plain_text(cls, value: str) -> str:
        if "```" in value or "\n" in value or re.search(r"[\x00-\x1f]", value):
            raise ValueError("scene fields must be plain single-paragraph text, without Markdown or control characters")
        for claim in re.finditer(r"\b(?:ensur(?:e|es|ing)|guarantee(?:s|ing)?|always)\b[^.!?]{0,160}\b(?:accurate|accuracy|correct|reliable)\b", value, re.IGNORECASE):
            prefix = value[max(0, claim.start() - 40):claim.start()]
            if not re.search(r"\b(?:not|never|cannot|can't|doesn't|no)\b", prefix, re.IGNORECASE):
                raise ValueError("Avoid unqualified accuracy guarantees; describe benefits conditionally and acknowledge source quality")
        return value

    @field_validator("narration")
    @classmethod
    def spoken_paragraph(cls, value: str) -> str:
        if not 1 <= len(words(value)) <= 60:
            raise ValueError("narration must contain 15–60 words; aim for 20–45")
        if not re.search(r"[.!?:;…][\"'\u201d\u2019]?$", value):
            raise ValueError("narration must end as a complete sentence")
        return value

    @model_validator(mode="after")
    def distinct_body(self):
        if self.body.casefold() == self.narration.casefold():
            raise ValueError("body must summarize the scene, not duplicate narration verbatim")
        return self


class VideoScript(StrictContent):
    title: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    topic: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    scenes: Annotated[list[Scene], Field(min_length=1, max_length=120)]

    @model_validator(mode="after")
    def ordered_distinct_scenes(self):
        if [scene.id for scene in self.scenes] != list(range(1, len(self.scenes) + 1)):
            raise ValueError("scene IDs must be sequential integers starting at 1")
        for field in ("headline", "narration"):
            values = [getattr(scene, field).casefold() for scene in self.scenes]
            if len(set(values)) != len(values):
                raise ValueError(f"duplicate scene {field}; each scene must add a distinct idea")
        return self


class ScenePlan(StrictContent):
    id: Annotated[int, Field(ge=1, le=120)]
    headline: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    point: Annotated[str, StringConstraints(min_length=10, max_length=300)]

    @field_validator("headline")
    @classmethod
    def readable_headline(cls, value: str) -> str:
        return Scene.short_headline(value)

    @field_validator("headline", "point")
    @classmethod
    def plain_plan_text(cls, value: str) -> str:
        return Scene.plain_text(value)


class VideoPlan(StrictContent):
    title: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    topic: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    scenes: Annotated[list[ScenePlan], Field(min_length=3, max_length=12)]

    @model_validator(mode="after")
    def distinct_ordered_points(self):
        if [s.id for s in self.scenes] != list(range(1, len(self.scenes) + 1)):
            raise ValueError("outline IDs must be sequential integers starting at 1")
        for field in ("headline", "point"):
            if len({getattr(s, field).casefold() for s in self.scenes}) != len(self.scenes):
                raise ValueError(f"duplicate outline {field}")
        return self


class BodyDraft(StrictContent):
    body: Annotated[str, StringConstraints(min_length=1, max_length=180)]

    @field_validator("body")
    @classmethod
    def readable_body(cls, value: str) -> str:
        return Scene.plain_text(value)


class NarrationDraft(StrictContent):
    narration: Annotated[str, StringConstraints(min_length=1, max_length=600)]

    @field_validator("narration")
    @classmethod
    def spoken_text(cls, value: str) -> str:
        if len(words(value)) < 15:
            raise ValueError('narration must contain 15-60 words when drafting a lesson')
        # Model-written narration teaches the subject directly. Authored scripts may introduce
        # their own video ("In this video, we'll...") and are preserved as written.
        if re.search(r"\b(?:in this (?:scene|video)|we(?: will|'ll)? explore)\b", value, re.IGNORECASE):
            raise ValueError("Narrate the subject directly; omit meta introductions about the scene or video")
        return Scene.spoken_paragraph(Scene.plain_text(value))
