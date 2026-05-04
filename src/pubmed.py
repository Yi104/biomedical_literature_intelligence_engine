from __future__ import annotations

from dataclasses import dataclass
from typing import List
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class PubMedRecord:
    pmid: str
    title: str
    abstract: str
    journal: str
    year: str


def _http_get(url: str, timeout: int = 30) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        return response.read()


def search_pubmed(
    query: str,
    retmax: int = 20,
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
) -> List[str]:
    term_parts = [f"({query})"]
    if year_from is not None and year_to is not None:
        term_parts.append(
            f'("{year_from}"[Date - Publication] : "{year_to}"[Date - Publication])'
        )
    if journal and journal.strip():
        term_parts.append(f'("{journal.strip()}"[Journal])')
    term = " AND ".join(term_parts)

    params = {
        "db": "pubmed",
        "term": term,
        "retmax": str(retmax),
        "retmode": "xml",
        "sort": "relevance",
    }
    url = f"{EUTILS_BASE}/esearch.fcgi?{urlencode(params)}"
    content = _http_get(url)
    root = ET.fromstring(content)
    return [node.text.strip() for node in root.findall(".//IdList/Id") if node.text]


def fetch_pubmed_details(pmids: List[str]) -> List[PubMedRecord]:
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    url = f"{EUTILS_BASE}/efetch.fcgi?{urlencode(params)}"
    content = _http_get(url)
    root = ET.fromstring(content)

    records: List[PubMedRecord] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//MedlineCitation/PMID", default="").strip()
        title = article.findtext(".//Article/ArticleTitle", default="").strip()
        journal = article.findtext(".//Article/Journal/Title", default="").strip()
        year = article.findtext(".//PubDate/Year", default="").strip()
        if not year:
            medline_date = article.findtext(".//PubDate/MedlineDate", default="").strip()
            year = medline_date[:4] if medline_date else ""

        abstract_nodes = article.findall(".//Article/Abstract/AbstractText")
        abstract_parts = []
        for node in abstract_nodes:
            label = (node.attrib.get("Label") or "").strip()
            text = "".join(node.itertext()).strip()
            if not text:
                continue
            abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = " ".join(abstract_parts).strip()

        records.append(
            PubMedRecord(
                pmid=pmid,
                title=title,
                abstract=abstract,
                journal=journal,
                year=year,
            )
        )
    return records
