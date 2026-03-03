from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PicotsRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    population: str | None = Field(default=None)
    index_prognostic_factor: str | None = Field(default=None)
    comparator_prognostic_factors: list[str] | None = Field(default=None)
    outcome: str | None = Field(default=None)
    timing: str | None = Field(default=None)
    setting: str | None = Field(default=None)
