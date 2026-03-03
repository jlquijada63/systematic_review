from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from agents import Agent, Runner
from dotenv import load_dotenv

try:
    from ..common.io_helpers import extract_pdf_text_and_tables_markdown
    from .model import CharmsPfRecord
    from .prompt import CHARMS_PF_INSTRUCTIONS
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    src_root = project_root / "src"
    for candidate in (str(project_root), str(src_root)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)

    try:
        from src.common.io_helpers import extract_pdf_text_and_tables_markdown
        from src.charms_agent.model import CharmsPfRecord
        from src.charms_agent.prompt import CHARMS_PF_INSTRUCTIONS
    except ImportError:
        from common.io_helpers import extract_pdf_text_and_tables_markdown
        from charms_agent.model import CharmsPfRecord
        from charms_agent.prompt import CHARMS_PF_INSTRUCTIONS


load_dotenv()

charms_pf_agent = Agent(
    name="Charm_pf Agent",
    model="gpt-5-mini",
    instructions=CHARMS_PF_INSTRUCTIONS,
    output_type=CharmsPfRecord,
)


def _default_pdf_path() -> Path:
    return Path(__file__).resolve().parents[2] / "documents" / "hip_fracture_prognosis.pdf"


async def main(pdf_path: str | Path | None = None) -> None:
    selected_pdf_path = Path(pdf_path) if pdf_path is not None else _default_pdf_path()
    article_converted = extract_pdf_text_and_tables_markdown(pdf_path=str(selected_pdf_path))

    result = await Runner.run(
        charms_pf_agent,
        input=f"analiza el siguiente articulo: {article_converted}",
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
