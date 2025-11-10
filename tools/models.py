from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


LessonLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2", "UNSET"]
VocabLevel = LessonLevel
PartOfSpeech = Literal["noun", "verb", "adj", "adv", "prep", "det", "pron", "conj", "expr"]
Gender = Optional[Literal["masculine", "feminine"]]


class EnglishAnchorStep(BaseModel):
    phase: Literal["english_anchor"]
    line: str


class SystemLogicStep(BaseModel):
    phase: Literal["system_logic"]
    line: str


class MeaningDepthStep(BaseModel):
    phase: Literal["meaning_depth"]
    origin: str
    story: str


class SpanishEntryStep(BaseModel):
    phase: Literal["spanish_entry"]
    line: str


class ExamplesStep(BaseModel):
    phase: Literal["examples"]
    items: List[str]

    @field_validator("items")
    @classmethod
    def ensure_items(cls, value: List[str]) -> List[str]:
        return [item for item in value if item and item.strip()]


LessonStep = Union[
    EnglishAnchorStep,
    SystemLogicStep,
    MeaningDepthStep,
    SpanishEntryStep,
    ExamplesStep,
]


class Lesson(BaseModel):
    id: str = Field(pattern=r"^mmspanish__grammar_\d{3}_[a-z0-9\-]+$")
    title: str
    nickname: str
    level: LessonLevel
    unit: int
    lesson_number: int
    tags: List[str]
    steps: List[LessonStep]
    notes: Optional[str] = None
    source_files: List[str]

    @field_validator("nickname")
    @classmethod
    def nickname_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("nickname must not be empty")
        return value

    @field_validator("tags", "source_files")
    @classmethod
    def unique_lists(cls, value: List[str]) -> List[str]:
        seen = []
        for item in value:
            if item not in seen:
                seen.append(item)
        return seen

    @field_validator("steps")
    @classmethod
    def ensure_steps(cls, value: List[LessonStep]) -> List[LessonStep]:
        if not value:
            raise ValueError("steps must not be empty")
        return value


class VocabExample(BaseModel):
    es: str
    en: str

    @model_validator(mode="after")
    def ensure_text(self) -> "VocabExample":
        if not self.es.strip() or not self.en.strip():
            raise ValueError("example text must not be empty")
        return self


class Vocabulary(BaseModel):
    id: str = Field(pattern=r"^mmspanish__vocab_[0-9a-f]{16}$")
    spanish: str
    pos: PartOfSpeech
    gender: Gender = None
    english_gloss: str
    definition: str
    origin: Optional[str] = None
    story: Optional[str] = None
    examples: List[VocabExample]
    level: VocabLevel
    tags: List[str]
    source_files: List[str]
    notes: Optional[str] = None

    @field_validator("spanish", "english_gloss", "definition")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be empty")
        return value

    @field_validator("tags", "source_files")
    @classmethod
    def unique_lists(cls, value: List[str]) -> List[str]:
        seen = []
        for item in value:
            if item not in seen:
                seen.append(item)
        return seen

    @field_validator("examples")
    @classmethod
    def at_least_one_example(cls, value: List[VocabExample]) -> List[VocabExample]:
        if not value:
            raise ValueError("examples must not be empty")
        return value

    @model_validator(mode="after")
    def gender_for_pos(self) -> "Vocabulary":
        if self.pos != "noun":
            object.__setattr__(self, "gender", None)
        return self
