from __future__ import annotations

from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader


def _normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_empty_row(row: list[Any]) -> bool:
    return all(_normalize_cell(cell) == "" for cell in row)


def _table_to_markdown(table: list[list[Any]]) -> str:
    cleaned_rows = []
    for row in table:
        normalized_row = [_normalize_cell(cell) for cell in row]
        if not _is_empty_row(normalized_row):
            cleaned_rows.append(normalized_row)

    if not cleaned_rows:
        return ""

    max_cols = max(len(row) for row in cleaned_rows)
    padded_rows = [row + [""] * (max_cols - len(row)) for row in cleaned_rows]

    header = padded_rows[0]
    body = padded_rows[1:]

    markdown_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * max_cols) + " |",
    ]
    for row in body:
        markdown_lines.append("| " + " | ".join(row) + " |")

    return "\n".join(markdown_lines)


def extract_pdf_text_and_tables_markdown(pdf_path: str) -> dict[str, Any]:
    """Extract text with pypdf and tables with pdfplumber from a PDF.

    Args:
        pdf_path: Path to a PDF document.

    Returns:
        A dictionary with:
        - text: full text across all pages
        - tables_markdown: list of markdown-formatted tables
        - metadata: source path, page count, and table count

    Raises:
        FileNotFoundError: If the PDF path does not exist.
        ValueError: If the file extension is not .pdf.
        RuntimeError: If the PDF cannot be parsed.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file (.pdf), got: {pdf_path}")

    try:
        reader = PdfReader(str(path))
        page_texts = [(page.extract_text() or "") for page in reader.pages]

        tables_markdown: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    if not table:
                        continue
                    markdown_table = _table_to_markdown(table)
                    if markdown_table:
                        tables_markdown.append(markdown_table)
    except Exception as exc:
        raise RuntimeError(f"Failed to parse PDF '{pdf_path}': {exc}") from exc

    text = "\n\n".join(page_texts)
    return {
        "text": text,
        "tables_markdown": tables_markdown,
        "metadata": {
            "source_pdf": str(path),
            "num_pages": len(page_texts),
            "num_tables": len(tables_markdown),
        },
    }
