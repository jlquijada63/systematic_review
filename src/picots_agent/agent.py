from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from agents import Agent, Runner
from dotenv import load_dotenv

try:
    from ..common.io_helpers import extract_pdf_text_and_tables_markdown
    from .model import PicotsAgentOutput, PicotsExtractionError, PicotsRecord
    from .prompt import PICOTS_INSTRUCTIONS
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    src_root = project_root / "src"
    for candidate in (str(project_root), str(src_root)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)

    try:
        from src.common.io_helpers import extract_pdf_text_and_tables_markdown
        from src.picots_agent.model import PicotsAgentOutput, PicotsExtractionError, PicotsRecord
        from src.picots_agent.prompt import PICOTS_INSTRUCTIONS
    except ImportError:
        from common.io_helpers import extract_pdf_text_and_tables_markdown
        from picots_agent.model import PicotsAgentOutput, PicotsExtractionError, PicotsRecord
        from picots_agent.prompt import PICOTS_INSTRUCTIONS


load_dotenv()

picots_agent = Agent(
    name="PICOTS Agent",
    model="gpt-5-mini",
    instructions=PICOTS_INSTRUCTIONS,
    output_type=PicotsAgentOutput,
)


def _default_pdf_path() -> Path:
    return Path(__file__).resolve().parents[2] / "documents" / "hip_fracture_prognosis.pdf"


def _normalize_factor_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _to_error(reason: str) -> PicotsExtractionError:
    return PicotsExtractionError(reason=reason)


async def main(
    pdf_path: str | Path | None = None,
    index_prognostic_factor: str | None = None,
) -> None:
    selected_pdf_path = Path(pdf_path) if pdf_path is not None else _default_pdf_path()
    if not index_prognostic_factor or not index_prognostic_factor.strip():
        print(
            _to_error(
                "No se ha proporcionado un factor pronostico indice por parte del usuario."
            ).model_dump_json(indent=2)
        )
        return

    article_converted = extract_pdf_text_and_tables_markdown(pdf_path=str(selected_pdf_path))

    result = await Runner.run(
        picots_agent,
        input=(
            "Analyze the following article and extract PICOTS. "
            f"The user-selected index prognostic factor is: '{index_prognostic_factor}'. "
            f"Article content: {article_converted}"
        ),
    )

    final_output = result.final_output
    if isinstance(final_output, PicotsRecord):
        user_factor = index_prognostic_factor.strip()
        studied_factors = final_output.studied_prognostic_factors or []
        if not studied_factors:
            final_output = _to_error(
                "El articulo no reporta de forma clara los factores pronosticos estudiados y no se puede validar el factor indicado."
            )
        else:
            normalized_user = _normalize_factor_name(user_factor)
            normalized_studied = {_normalize_factor_name(item): item for item in studied_factors if item}
            if normalized_user not in normalized_studied:
                final_output = _to_error(
                    "El factor pronostico introducido por el usuario no figura entre los factores pronosticos estudiados en el articulo."
                )
            else:
                validated_index = normalized_studied[normalized_user]
                comparators = [
                    factor
                    for factor in studied_factors
                    if _normalize_factor_name(factor) != normalized_user
                ]
                final_output.index_prognostic_factor = validated_index
                final_output.comparator_prognostic_factors = comparators or None

    if hasattr(final_output, "model_dump_json"):
        print(final_output.model_dump_json(indent=2))
    elif isinstance(final_output, dict):
        print(json.dumps(final_output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"output": str(final_output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run PICOTS extraction agent.")
    parser.add_argument(
        "--pdf-path",
        type=str,
        default=None,
        help="Path to source PDF. Defaults to project hip fracture sample.",
    )
    parser.add_argument(
        "--index-prognostic-factor",
        type=str,
        default=None,
        help="User-selected index prognostic factor to validate against studied factors.",
    )
    args = parser.parse_args()
    asyncio.run(main(pdf_path=args.pdf_path, index_prognostic_factor=args.index_prognostic_factor))
