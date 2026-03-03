from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PicotsRecord(BaseModel):
    """Structured PICOTS extraction for a prognostic-factor study.

    This model represents a successful extraction outcome. The
    `index_prognostic_factor` field must contain one unique factor.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    population: str | None = Field(
        default=None,
        description="Target population where the prognostic factor is intended to be used.",
    )
    index_prognostic_factor: str = Field(
        ...,
        min_length=1,
        description="Single unique prognostic factor under evaluation.",
    )
    comparator_prognostic_factors: list[str] | None = Field(
        default=None,
        description="Comparator or adjustment prognostic factors as short factor names.",
    )
    outcome: str | None = Field(
        default=None,
        description="Outcome(s) used to assess prognostic performance.",
    )
    timing: str | None = Field(
        default=None,
        description="Time of prognostic factor measurement and outcome prediction period.",
    )
    setting: str | None = Field(
        default=None,
        description="Clinical care context where the prognostic factor is intended to be used.",
    )


class PicotsExtractionError(BaseModel):
    """Structured error returned when PICOTS extraction cannot meet hard constraints.

    This error is used when a unique `index_prognostic_factor` cannot be extracted.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    message: Literal["No se ha podido extraer la informacion"] = Field(
        default="No se ha podido extraer la informacion",
        description="Fixed user-facing error message in Spanish.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        description="Short explanation (in Spanish) of why extraction failed.",
    )
    failed_field: Literal["index_prognostic_factor"] = Field(
        default="index_prognostic_factor",
        description="Field that caused extraction failure.",
    )


# Agent output can be either a successful extraction or a structured extraction error.
PicotsAgentOutput = PicotsRecord | PicotsExtractionError
