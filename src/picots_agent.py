from __future__ import annotations

import asyncio
import json
from pathlib import Path

from agents import Agent, Runner
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

try:
    from .helpers import extract_pdf_text_and_tables_markdown
except ImportError:
    from helpers import extract_pdf_text_and_tables_markdown


PICOTS_INSTRUCTIONS = """
You are an expert in medical systematic reviews.
Extract PICOTS from the provided scientific article to support study selection.

Return only these six items:
1) Population
2) Index prognostic factor
3) Comparator prognostic factor(s)
4) Outcome
5) Timing
6) Setting

Rules:
- Be concise.
- Use only information supported by the article text.
- If an item is not reported, return null for that field.

How to extract each item:
- Population:
  Define the target population where the prognostic factor(s) are used.
  Include condition, key inclusion features, and disease stage/context when available.
- Index prognostic factor:
  Identify the main prognostic factor(s) whose prognostic value is being evaluated.
- Comparator prognostic factor(s):
  Identify other factors used for comparison or adjustment.
  If the study reports only unadjusted effect of the index factor with no comparator factors,
  return null.
- Outcome:
  Define outcome(s) for which prognostic ability is assessed.
  Include outcome families/endpoints when clearly reported (e.g., disease-specific, CV, all-cause mortality).
- Timing:
  Extract both:
  (i) when prognostic factors are measured/used (time point of prognostication), and
  (ii) prediction/follow-up time period for outcomes.
- Setting:
  Define intended care context and role of the prognostic factor(s) (e.g., primary care, secondary care,
  risk stratification, treatment management support).

Extraction quality rules:
- Prefer explicit statements from methods/objectives/eligibility criteria.
- Do not invent comparator factors; use null if absent.
- Keep comparator_prognostic_factors as a list of short factor names.
- Do not add fields outside the output schema.
"""


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


load_dotenv()

picots_agent = Agent(
    name="PICOTS Agent",
    model="gpt-5-mini",
    instructions=PICOTS_INSTRUCTIONS,
    output_type=PicotsRecord,
)


def _default_pdf_path() -> Path:
    return Path(__file__).resolve().parents[1] / "documents" / "hip_fracture_prognosis.pdf"


async def main(pdf_path: str | Path | None = None) -> None:
    selected_pdf_path = Path(pdf_path) if pdf_path is not None else _default_pdf_path()
    article_converted = extract_pdf_text_and_tables_markdown(pdf_path=str(selected_pdf_path))

    result = await Runner.run(
        picots_agent,
        input=f"Analyze the following article and extract PICOTS: {article_converted}",
    )

    final_output = result.final_output
    if hasattr(final_output, "model_dump_json"):
        print(final_output.model_dump_json(indent=2))
    elif isinstance(final_output, dict):
        print(json.dumps(final_output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"output": str(final_output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
