
from __future__ import annotations

import asyncio
from pathlib import Path

from agents import Agent, Runner
from dotenv import load_dotenv

try:
    from .helpers import extract_pdf_text_and_tables_markdown
    from .models import CharmsPfRecord
    from .prompts import CHARMS_PF_INSTRUCTIONS
except ImportError:
    from helpers import extract_pdf_text_and_tables_markdown
    from models import CharmsPfRecord
    from prompts import CHARMS_PF_INSTRUCTIONS

load_dotenv()

charms_pf_agent = Agent(
    name="Charm_pf Agent",
    model="gpt-5-mini",
    instructions=CHARMS_PF_INSTRUCTIONS,
    output_type=CharmsPfRecord,
)

def _default_pdf_path() -> Path:
    return Path(__file__).resolve().parents[1] / "documents" / "hip_fracture_prognosis.pdf"


async def main(pdf_path: str | Path | None = None) -> None:
    selected_pdf_path = Path(pdf_path) if pdf_path is not None else _default_pdf_path()
    article_converted = extract_pdf_text_and_tables_markdown(pdf_path=str(selected_pdf_path))

    result = await Runner.run(
        charms_pf_agent,
        input=f"analiza el siguiente articulo: {article_converted}",
    )
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
