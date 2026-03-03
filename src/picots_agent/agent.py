from __future__ import annotations

import asyncio
import json
from pathlib import Path

from agents import Agent, Runner
from dotenv import load_dotenv

try:
    from ..common.io_helpers import extract_pdf_text_and_tables_markdown
    from .model import PicotsRecord
    from .prompt import PICOTS_INSTRUCTIONS
except ImportError:
    from src.common.io_helpers import extract_pdf_text_and_tables_markdown
    from src.picots_agent.model import PicotsRecord
    from src.picots_agent.prompt import PICOTS_INSTRUCTIONS


load_dotenv()

picots_agent = Agent(
    name="PICOTS Agent",
    model="gpt-5-mini",
    instructions=PICOTS_INSTRUCTIONS,
    output_type=PicotsRecord,
)


def _default_pdf_path() -> Path:
    return Path(__file__).resolve().parents[2] / "documents" / "hip_fracture_prognosis.pdf"


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
