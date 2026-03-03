from __future__ import annotations

import argparse
import asyncio
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import certifi
from agents import Agent, Runner
from dotenv import load_dotenv

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

try:
    from .model import ArticleRecord, SearchAgentResult, SearchConfig, SearchQueries, SourceStatus
    from .prompt import AGENT_INSTRUCTIONS
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    src_root = project_root / "src"
    for candidate in (str(project_root), str(src_root)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
    from search_agent.model import ArticleRecord, SearchAgentResult, SearchConfig, SearchQueries, SourceStatus
    from search_agent.prompt import AGENT_INSTRUCTIONS


load_dotenv()

query_builder_agent = Agent(
    name="Search Query Builder Agent",
    model="gpt-5-mini",
    instructions=AGENT_INSTRUCTIONS,
    output_type=SearchQueries,
)

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def _default_config_path() -> Path:
    return Path(__file__).resolve().with_name("config.toml")


def _load_config(config_path: str | Path | None = None) -> SearchConfig:
    path = Path(config_path) if config_path is not None else _default_config_path()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return SearchConfig(**data)


def _http_get_json(url: str, params: dict[str, str | int] | None = None, headers: dict[str, str] | None = None) -> dict:
    query = urllib.parse.urlencode(params or {})
    full_url = f"{url}?{query}" if query else url
    req = urllib.request.Request(full_url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_get_text(url: str, params: dict[str, str | int] | None = None, headers: dict[str, str] | None = None) -> str:
    query = urllib.parse.urlencode(params or {})
    full_url = f"{url}?{query}" if query else url
    req = urllib.request.Request(full_url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as response:
        return response.read().decode("utf-8")


def _parse_pubmed_abstracts_xml(xml_text: str) -> dict[str, str]:
    abstracts_by_pmid: dict[str, str] = {}
    root = ET.fromstring(xml_text)
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//MedlineCitation/PMID")
        if pmid_el is None or not pmid_el.text:
            continue
        pmid = pmid_el.text.strip()
        abstract_parts = [el.text.strip() for el in article.findall(".//Abstract/AbstractText") if el.text]
        if abstract_parts:
            abstracts_by_pmid[pmid] = "\n".join(abstract_parts)
    return abstracts_by_pmid


def _dedupe_articles(articles: list[ArticleRecord]) -> list[ArticleRecord]:
    seen: set[tuple[str, str | None]] = set()
    deduped: list[ArticleRecord] = []
    for article in articles:
        key = (article.title.strip().lower(), article.publication_date)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(article)
    return deduped


def _normalize_pmcid(raw: str) -> str:
    raw = raw.strip()
    return raw if raw.upper().startswith("PMC") else f"PMC{raw}"


def _search_pubmed(query: str, max_results: int) -> tuple[list[ArticleRecord], SourceStatus]:
    try:
        esearch = _http_get_json(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": max_results,
                "sort": "pub+date",
            },
        )
        ids = esearch.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return [], SourceStatus(source="PubMed", query=query, available=True, results_count=0, detail="No matches")

        ids_csv = ",".join(ids)
        esummary = _http_get_json(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            {"db": "pubmed", "id": ids_csv, "retmode": "json"},
        )
        efetch_xml = _http_get_text(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            {"db": "pubmed", "id": ids_csv, "retmode": "xml"},
        )
        abstracts = _parse_pubmed_abstracts_xml(efetch_xml)

        results = esummary.get("result", {})
        articles: list[ArticleRecord] = []
        for pmid in ids:
            item = results.get(pmid)
            if not item:
                continue
            title = item.get("title") or "Untitled"
            authors = [a.get("name", "").strip() for a in item.get("authors", []) if a.get("name")]
            articleids = item.get("articleids", []) or []

            pmcid = None
            for aid in articleids:
                idtype = (aid.get("idtype") or "").lower()
                if idtype in {"pmc", "pmcid"} and aid.get("value"):
                    pmcid = _normalize_pmcid(aid["value"])
                    break

            full_text_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else None
            has_full_text = bool(full_text_url)

            articles.append(
                ArticleRecord(
                    title=title,
                    authors=authors,
                    journal=item.get("fulljournalname") or item.get("source"),
                    publication_date=item.get("pubdate"),
                    abstract=abstracts.get(pmid),
                    has_full_text=has_full_text,
                    full_text_url=full_text_url,
                )
            )

        return articles, SourceStatus(
            source="PubMed",
            query=query,
            available=True,
            results_count=len(articles),
            detail="Retrieved via E-utilities",
        )
    except Exception as exc:
        return [], SourceStatus(
            source="PubMed",
            query=query,
            available=False,
            results_count=0,
            detail=f"API error: {exc}",
        )


def _search_clinicaltrials(query: str, max_results: int) -> tuple[list[ArticleRecord], SourceStatus]:
    try:
        payload = _http_get_json(
            "https://clinicaltrials.gov/api/v2/studies",
            {
                "query.term": query,
                "pageSize": max_results,
                "format": "json",
            },
        )

        studies = payload.get("studies", []) or []
        articles: list[ArticleRecord] = []
        for study in studies:
            protocol = study.get("protocolSection", {})
            refs = protocol.get("referencesModule", {}).get("references", []) or []
            for ref in refs:
                citation = (ref.get("citation") or "").strip()
                if not citation:
                    continue
                articles.append(
                    ArticleRecord(
                        title=citation[:300],
                        authors=[],
                        journal=None,
                        publication_date=None,
                        abstract=None,
                        has_full_text=bool(ref.get("pmid")),
                        full_text_url=(
                            f"https://pubmed.ncbi.nlm.nih.gov/{ref.get('pmid')}/"
                            if ref.get("pmid")
                            else None
                        ),
                    )
                )

        return articles, SourceStatus(
            source="ClinicalTrials.gov",
            query=query,
            available=True,
            results_count=len(articles),
            detail="Publication references extracted from studies",
        )
    except Exception as exc:
        return [], SourceStatus(
            source="ClinicalTrials.gov",
            query=query,
            available=False,
            results_count=0,
            detail=f"API error: {exc}",
        )


def _search_embase(query: str, max_results: int) -> tuple[list[ArticleRecord], SourceStatus]:
    api_key = os.getenv("EMBASE_API_KEY") or os.getenv("ELS_API_KEY")
    if not api_key:
        return [], SourceStatus(
            source="Embase",
            query=query,
            available=False,
            results_count=0,
            detail="No Embase API key configured (EMBASE_API_KEY/ELS_API_KEY).",
        )

    try:
        headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
        data = _http_get_json(
            "https://api.elsevier.com/content/search/index:EMBASE",
            {
                "query": query,
                "count": max_results,
                "sort": "-date",
            },
            headers=headers,
        )

        entries = data.get("search-results", {}).get("entry", []) or []
        articles: list[ArticleRecord] = []
        for entry in entries:
            title = entry.get("dc:title") or "Untitled"
            creator = entry.get("dc:creator")
            authors = [creator] if creator else []
            links = entry.get("link", []) or []
            full_text_link = None
            for link in links:
                href = link.get("@href")
                ref = (link.get("@ref") or "").lower()
                if href and ref in {"scidir", "full-text"}:
                    full_text_link = href
                    break

            has_full_text = bool(full_text_link)
            articles.append(
                ArticleRecord(
                    title=title,
                    authors=authors,
                    journal=entry.get("prism:publicationName"),
                    publication_date=entry.get("prism:coverDate"),
                    abstract=entry.get("dc:description"),
                    has_full_text=has_full_text,
                    full_text_url=full_text_link,
                )
            )

        return articles, SourceStatus(
            source="Embase",
            query=query,
            available=True,
            results_count=len(articles),
            detail="Retrieved via Elsevier API",
        )
    except Exception as exc:
        return [], SourceStatus(
            source="Embase",
            query=query,
            available=False,
            results_count=0,
            detail=f"API error: {exc}",
        )


def _search_ictrp(query: str, max_results: int) -> tuple[list[ArticleRecord], SourceStatus]:
    # WHO ICTRP public API availability may vary. Try official endpoint first.
    url = "https://trialsearch.who.int/api/TrialSearch"
    try:
        _http_get_json(url, {"q": query, "page": 1, "pageSize": max_results})
        return [], SourceStatus(
            source="WHO ICTRP",
            query=query,
            available=True,
            results_count=0,
            detail="Endpoint reachable but no normalized publication parser configured.",
        )
    except Exception as exc:
        return [], SourceStatus(
            source="WHO ICTRP",
            query=query,
            available=False,
            results_count=0,
            detail=f"API unavailable or incompatible endpoint: {exc}",
        )


async def _build_queries(
    prognostic_factor: str,
    target_population: str,
    start_date: str,
    end_date: str,
) -> SearchQueries:
    prompt_input = (
        "Build technical search expressions for prognostic studies. "
        f"User factor: {prognostic_factor}. "
        f"Target population: {target_population}. "
        f"Start date: {start_date}. End date: {end_date}."
    )
    result = await Runner.run(query_builder_agent, input=prompt_input)
    output = result.final_output
    if isinstance(output, SearchQueries):
        return output
    if hasattr(output, "model_dump"):
        return SearchQueries(**output.model_dump())
    if isinstance(output, dict):
        return SearchQueries(**output)
    raise ValueError("Unexpected query builder output format")


async def main(config_path: str | Path | None = None) -> None:
    cfg = _load_config(config_path)

    queries = await _build_queries(
        prognostic_factor=cfg.prognostic_factor,
        target_population=cfg.target_population,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
    )

    pubmed_articles, pubmed_status = await asyncio.to_thread(_search_pubmed, queries.pubmed_query, cfg.max_results)
    embase_articles, embase_status = await asyncio.to_thread(_search_embase, queries.embase_query, cfg.max_results)
    ct_articles, ct_status = await asyncio.to_thread(
        _search_clinicaltrials, queries.clinicaltrials_query, cfg.max_results
    )
    ictrp_articles, ictrp_status = await asyncio.to_thread(_search_ictrp, queries.ictrp_query, cfg.max_results)

    all_articles = _dedupe_articles(pubmed_articles + embase_articles + ct_articles + ictrp_articles)

    final_result = SearchAgentResult(
        articles=all_articles,
        source_status=[pubmed_status, embase_status, ct_status, ictrp_status],
        search_queries=queries,
    )
    print(final_result.model_dump_json(indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search medical literature across multiple databases using TOML config.")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to TOML config file. Defaults to src/search_agent/config.toml.",
    )
    args = parser.parse_args()
    asyncio.run(main(config_path=args.config))
