from __future__ import annotations

import argparse
import asyncio
import json
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import certifi

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

try:
    from .model import ArticleRecord, SearchAgentResult, SearchConfig, SearchQueries
except ImportError:
    project_root = Path(__file__).resolve().parents[2]
    src_root = project_root / "src"
    for candidate in (str(project_root), str(src_root)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
    from search_agent.model import ArticleRecord, SearchAgentResult, SearchConfig, SearchQueries


_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def _default_config_path() -> Path:
    return Path(__file__).resolve().with_name("config.toml")


def _load_config(config_path: str | Path | None = None) -> SearchConfig:
    path = Path(config_path) if config_path is not None else _default_config_path()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return SearchConfig(**data)


def _escape_pubmed_phrase(value: str) -> str:
    return value.strip().replace('"', '\\"')


def _build_strict_pubmed_query(
    prognostic_factor: str,
    target_population: str,
    start_date: str,
    end_date: str,
) -> SearchQueries:
    factor = _escape_pubmed_phrase(prognostic_factor)
    population = _escape_pubmed_phrase(target_population)
    pubmed_query = (
        f"(\"{factor}\"[Title/Abstract]) "
        f"AND (\"{population}\"[Title/Abstract]) "
        f"AND (\"{start_date}\"[Date - Publication] : \"{end_date}\"[Date - Publication])"
    )
    return SearchQueries(pubmed_query=pubmed_query)


def _http_get_json(url: str, params: dict[str, str | int] | None = None) -> dict:
    query = urllib.parse.urlencode(params or {})
    full_url = f"{url}?{query}" if query else url
    req = urllib.request.Request(full_url, headers={})
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_get_text(url: str, params: dict[str, str | int] | None = None) -> str:
    query = urllib.parse.urlencode(params or {})
    full_url = f"{url}?{query}" if query else url
    req = urllib.request.Request(full_url, headers={})
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


def _search_pubmed(query: str, max_results: int) -> list[ArticleRecord]:
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
        return []

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
    return articles


async def main(config_path: str | Path | None = None) -> None:
    cfg = _load_config(config_path)
    queries = _build_strict_pubmed_query(
        prognostic_factor=cfg.prognostic_factor,
        target_population=cfg.target_population,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
    )
    articles = await asyncio.to_thread(_search_pubmed, queries.pubmed_query, cfg.max_results)
    final_result = SearchAgentResult(
        articles=_dedupe_articles(articles),
        search_queries=queries,
    )
    print(final_result.model_dump_json(indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search PubMed medical literature using TOML config.")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to TOML config file. Defaults to src/search_agent/config.toml.",
    )
    args = parser.parse_args()
    asyncio.run(main(config_path=args.config))
