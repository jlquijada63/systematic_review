# Search Agent

## Goal
`search_agent` performs multi-source medical literature search for prognostic studies and returns normalized article metadata.

Target sources:
- PubMed (E-utilities)
- Embase (Elsevier API, if credentials are available)
- ClinicalTrials.gov (API v2)
- WHO ICTRP (best-effort API endpoint)

## How It Works
1. Loads runtime configuration from a TOML file.
2. Uses `gpt-5-mini` (OpenAI Agents SDK) to generate database-specific technical search expressions.
3. Executes source searches via APIs when available.
4. Normalizes records into a common Pydantic schema.
5. Returns JSON output with article records, source status, and generated queries.

## Configuration (TOML)
Default config path:
- `src/search_agent/config.toml`

Required/optional fields:

```toml
prognostic_factor = "age"
target_population = "older adults with hip fracture"
start_date = "2018-01-01"
end_date = "2024-12-31"
max_results = 20
```

Field definitions:
- `prognostic_factor` (required): prognostic factor selected by the user.
- `target_population` (required): population where the factor is expected to act.
- `start_date` (required): search start date (`YYYY-MM-DD`).
- `end_date` (required): search end date (`YYYY-MM-DD`).
- `max_results` (optional): max records requested per source. Default: `20`.

## Run
From repository root:

```bash
uv run src/search_agent/agent.py
```

With explicit config path:

```bash
uv run src/search_agent/agent.py --config src/search_agent/config.toml
```

## Output
The agent prints JSON (`SearchAgentResult`) with:
- `articles`: list of normalized records with fields:
  - `title`
  - `authors`
  - `journal`
  - `publication_date`
  - `abstract`
  - `has_full_text`
  - `full_text_url`
- `source_status`: status per source (`available`, `results_count`, `detail`, `query`)
- `search_queries`: the generated technical expressions for each database.

## Notes
- Embase is queried only if `EMBASE_API_KEY` or `ELS_API_KEY` is configured.
- If a source is unavailable, the workflow continues and reports that status in `source_status`.
- WHO ICTRP endpoint availability may vary and is handled as best-effort.
