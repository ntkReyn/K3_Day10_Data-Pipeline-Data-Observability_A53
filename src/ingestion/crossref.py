from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref ``/works`` response into stable local records."""

    def text(value: object) -> str:
        plain = re.sub(r"<[^>]+>", " ", str(value or ""))
        return normalize_whitespace(unescape(plain))

    def date_value(item: dict, *keys: str) -> str:
        for key in keys:
            candidate = item.get(key) or {}
            parts = candidate.get("date-parts", [[]]) if isinstance(candidate, dict) else [[]]
            values = parts[0] if parts else []
            if values:
                year = int(values[0])
                month = int(values[1]) if len(values) > 1 else 1
                day = int(values[2]) if len(values) > 2 else 1
                return f"{year:04d}-{month:02d}-{day:02d}"
        return ""

    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = text(item.get("DOI")).lower()
        title_values = item.get("title") or []
        title = text(title_values[0] if title_values else "")
        summary = text(item.get("abstract") or item.get("description"))
        if not paper_id or not title or not summary or paper_id in seen_ids:
            continue

        authors = []
        for author in item.get("author") or []:
            if not isinstance(author, dict):
                continue
            name = text(" ".join(part for part in [author.get("given"), author.get("family")] if part))
            if not name:
                name = text(author.get("name"))
            if name:
                authors.append(name)
        categories = [text(value) for value in item.get("subject") or [] if text(value)]
        links = item.get("link") or []
        pdf_url = ""
        for link in links:
            if isinstance(link, dict) and "pdf" in str(link.get("content-type", "")).lower():
                pdf_url = text(link.get("URL"))
                break
        resource = item.get("resource") or {}
        abs_url = text(item.get("URL") or resource.get("primary", {}).get("URL"))
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=date_value(item, "published-print", "published-online", "issued", "created"),
                updated=date_value(item, "indexed", "created", "deposited"),
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=text(item.get("publisher") or item.get("container-title", [""])[0]),
            )
        )
        seen_ids.add(paper_id)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch a Crossref snapshot, retaining both source and parsed artifacts."""
    endpoint = "https://api.crossref.org/works"
    params = {"query": settings.source_query, "filter": settings.source_filter, "rows": settings.max_results}
    headers = {"User-Agent": "day10-data-observability-lab/0.1 (educational project)"}
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=30)
            if response.status_code in {429, 503}:
                delay = 2**attempt
                time.sleep(delay)
                continue
            response.raise_for_status()
            payload = response.json()
            write_json(settings.paths.raw_api_response, payload)
            records = parse_crossref_payload(payload)
            write_json(settings.paths.raw_records_json, [record.__dict__ for record in records])
            return records
        except requests.RequestException as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2**attempt)
    raise RuntimeError(f"Unable to fetch Crossref after retries: {last_error}")


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the parsed raw-record snapshot written by :func:`fetch_source_records`."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of raw records in {path}.")
    fields = set(PaperRecord.__dataclass_fields__)
    records = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        values = {field: item.get(field, [] if field in {"authors", "categories"} else "") for field in fields}
        records.append(PaperRecord(**values))
    return records
