# Search Agent

## Goal
`search_agent` performs PubMed-only medical literature search for prognostic studies and returns normalized article metadata.

Target source:
- PubMed (E-utilities)

## How It Works
1. Loads runtime configuration from a TOML file.
2. Builds a deterministic strict PubMed query using only:
   - `prognostic_factor` (exact phrase in `Title/Abstract`)
   - `target_population` (exact phrase in `Title/Abstract`)
   - date range (`start_date` to `end_date`)
3. Executes PubMed search via E-utilities.
4. Normalizes records into a common Pydantic schema.
5. Returns JSON output with article records and generated query.

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
- `search_queries.pubmed_query`: strict deterministic PubMed expression.

## Notes
- Runtime retrieval is PubMed-only.
- No synonym/MeSH expansion is applied.
- Strict query template:
  - `("prognostic_factor"[Title/Abstract]) AND ("target_population"[Title/Abstract]) AND ("start_date"[Date - Publication] : "end_date"[Date - Publication])`
