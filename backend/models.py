"""Versioned canonical model. Times are source seconds, beats are quarter notes."""

import math
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return str(uuid4())


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Meter(Model):
    numerator: int = Field(4, ge=1, le=12)
    denominator: Literal[2, 4, 8, 16] = 4

    @property
    def quarters(self) -> float:
        return self.numerator * 4 / self.denominator


class Chord(Model):
    id: str = Field(default_factory=uid, max_length=64)
    beat: float = Field(0, ge=0)
    symbol: str = Field("N.C.", max_length=48)
    confidence: float = Field(0, ge=0, le=1)
    manual: bool = False


class Note(Model):
    id: str = Field(default_factory=uid, max_length=64)
    beat: float = Field(0, ge=0)
    duration: float = Field(1, gt=0, le=48)
    midi: int = Field(60, ge=0, le=127)
    confidence: float = Field(0, ge=0, le=1)
    manual: bool = False


class Measure(Model):
    id: str = Field(default_factory=uid, max_length=64)
    start: float = Field(0, ge=0)
    end: float = Field(2, gt=0)
    meter: Meter = Field(default_factory=Meter)
    chords: list[Chord] = Field(default_factory=list, max_length=48)
    notes: list[Note] = Field(default_factory=list, max_length=192)
    section: str = Field("", max_length=60)
    cue: str = Field("", max_length=160)
    repeat_start: bool = False
    repeat_end: bool = False

    @model_validator(mode="after")
    def validate_events(self):
        if self.end <= self.start:
            raise ValueError("Measure end must follow its start")
        q = self.meter.quarters
        if any(c.beat >= q for c in self.chords):
            raise ValueError("Chord must start within the measure")
        if len({c.beat for c in self.chords}) != len(self.chords):
            raise ValueError("Only one chord change may start at each beat")
        prior_end = 0.0
        for n in sorted(self.notes, key=lambda n: n.beat):
            if n.beat < prior_end - 1e-6 or n.beat + n.duration > q + 1e-6:
                raise ValueError("Melody notes must fit the measure without overlapping")
            prior_end = n.beat + n.duration
        return self


class TempoPoint(Model):
    time: float = Field(0, ge=0)
    bpm: float = Field(120, ge=30, le=300)


class Source(Model):
    filename: str = Field("", max_length=255)
    reference_url: str = Field("", max_length=2048)
    duration: float = Field(0, ge=0)
    sample_rate: int = 22050


class Project(Model):
    schema_version: Literal[1] = 1
    id: str = Field(default_factory=uid, pattern=r"^[a-f0-9-]{36}$")
    revision: int = Field(0, ge=0)
    title: str = Field("Untitled chart", min_length=1, max_length=160)
    composer: str = Field("", max_length=160)
    source: Source = Field(default_factory=Source)
    bpm: float = Field(120, ge=30, le=300)
    tempo_confidence: float = Field(0, ge=0, le=1)
    tempo_map: list[TempoPoint] = Field(default_factory=list, max_length=2000)
    key: str = Field("C", max_length=12)
    key_mode: Literal["major", "minor"] = "major"
    key_confidence: float = Field(0, ge=0, le=1)
    key_manual: bool = False
    feel: Literal["straight", "swing", "unspecified"] = "unspecified"
    meter: Meter = Field(default_factory=Meter)
    meter_confidence: float = Field(0, ge=0, le=1)
    beats: list[float] = Field(default_factory=list, max_length=20000)
    measures: list[Measure] = Field(default_factory=list, max_length=2000)
    waveform: list[float] = Field(default_factory=list, max_length=2000)
    warnings: list[str] = Field(default_factory=list, max_length=30)
    form_suggestions: list[str] = Field(default_factory=list, max_length=30)
    updated_at: str = ""

    @model_validator(mode="after")
    def validate_timeline(self):
        if any(a.end > b.start + 1e-5 for a, b in zip(self.measures, self.measures[1:])):
            raise ValueError("Measure times must be ordered and must not overlap")
        if len({m.id for m in self.measures}) != len(self.measures):
            raise ValueError("Measure IDs must be unique")
        if any(not math.isfinite(x) or x < 0 for x in self.beats):
            raise ValueError("Beat times must be finite and nonnegative")
        if any(b <= a for a, b in zip(self.beats, self.beats[1:])):
            raise ValueError("Beat times must increase")
        if any(not math.isfinite(x) or not 0 <= x <= 1 for x in self.waveform):
            raise ValueError("Waveform peaks must be between zero and one")
        return self


class AnalysisOptions(Model):
    start: float = Field(0, ge=0)
    end: float | None = Field(None, gt=0)
    bpm: float | None = Field(None, ge=30, le=300)
    meter: Meter = Field(default_factory=Meter)
    key: str | None = Field(None, pattern=r"^[A-G][b#]?$")
    key_mode: Literal["major", "minor"] = "major"
    melody: bool = False
    sensitivity: float = Field(0.75, ge=0.5, le=0.99)

    @model_validator(mode="after")
    def valid_region(self):
        if self.end is not None and self.end <= self.start:
            raise ValueError("Region end must follow start")
        return self
