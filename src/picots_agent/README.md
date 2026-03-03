# PICOTS Agent

## Goal
`picots_agent` extracts the six PICOTS elements from a scientific medical article:

1. Population
2. Index prognostic factor
3. Comparator prognostic factors
4. Outcome
5. Timing
6. Setting

The objective is to produce structured data to support article selection in a systematic review workflow.

## How It Works
The agent is implemented with the OpenAI Agents SDK and uses model `gpt-5-mini`.

Execution flow:

1. Load environment variables with `dotenv`.
2. Read and parse a PDF article with shared helper `src/common/io_helpers.py`.
   - Text extraction: `pypdf`
   - Table extraction: `pdfplumber`
3. Send parsed article content to the agent with PICOTS-specific instructions.
4. Validate the model output with Pydantic schemas (`PicotsRecord` or `PicotsExtractionError`).
5. Print final output as JSON.

## Module Structure
- `agent.py`: agent definition and runtime execution (`main`).
- `model.py`: Pydantic output schema (`PicotsRecord`).
- `prompt.py`: extraction instructions for PICOTS.
- `__init__.py`: public exports.

## Output Schema
Success output: `PicotsRecord`

- `population: str | None`
- `index_prognostic_factor: str` (required and unique)
- `comparator_prognostic_factors: list[str] | None`
- `outcome: str | None`
- `timing: str | None`
- `setting: str | None`

Error output: `PicotsExtractionError`

- `message: "No se ha podido extraer la informacion"`
- `reason: str`
- `failed_field: "index_prognostic_factor"`

If the agent cannot extract one unique `index_prognostic_factor`, it must return the error output.

## Run
From repository root:

```bash
uv run src/picots_agent.py
```

Or call the packaged module directly in Python:

```python
import asyncio
from src.picots_agent.agent import main

asyncio.run(main())
```

To use a custom PDF path:

```python
import asyncio
from src.picots_agent.agent import main

asyncio.run(main("documents/your_article.pdf"))
```
