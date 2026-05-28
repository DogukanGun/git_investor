import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime

import httpx

from .config import settings

log = logging.getLogger("gitinvest.funding")

SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data"

_CIK_RE = re.compile(r"CIK\s+(\d+)", re.IGNORECASE)
_LEGAL_SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|corp|corporation|co|ltd|limited|plc|gmbh|labs?|technologies|technology|software|holdings)\b",
    re.IGNORECASE,
)
_NONWORD_RE = re.compile(r"[^a-z0-9\s]")


@dataclass
class FundingInfo:
    total: int  # largest disclosed offering amount, USD
    last_at: datetime | None
    url: str | None
    source: str = "sec_edgar"


def _normalize(name: str) -> set[str]:
    name = name.lower()
    name = _NONWORD_RE.sub(" ", name)
    name = _LEGAL_SUFFIX_RE.sub(" ", name)
    return {tok for tok in name.split() if len(tok) > 1}


def _name_matches(query: str, edgar_name: str) -> bool:
    """Conservative match: every meaningful query token appears in the EDGAR name."""
    q = _normalize(query)
    e = _normalize(edgar_name)
    if not q or not e:
        return False
    return q.issubset(e)


def _parse_filing_ref(hit: dict) -> tuple[str, str, str] | None:
    """Return (cik, accession_nodash, doc_name) from a search hit, or None."""
    _id = hit.get("_id", "")
    if ":" not in _id:
        return None
    accession, doc_name = _id.split(":", 1)
    source = hit.get("_source", {})
    names = source.get("display_names") or []
    cik = None
    for n in names:
        m = _CIK_RE.search(n)
        if m:
            cik = str(int(m.group(1)))  # strip leading zeros
            break
    if cik is None:
        return None
    return cik, accession.replace("-", ""), doc_name


def _matched_name(hit: dict) -> str:
    names = hit.get("_source", {}).get("display_names") or [""]
    return names[0]


def _parse_amount(xml: str) -> int | None:
    m = re.search(r"<totalAmountSold>(.*?)</totalAmountSold>", xml)
    if not m or not m.group(1).strip().isdigit():
        # Fall back to the total offering amount if nothing sold is recorded.
        m = re.search(r"<totalOfferingAmount>(.*?)</totalOfferingAmount>", xml)
    if m and m.group(1).strip().isdigit():
        return int(m.group(1).strip())
    return None


class FundingClient:
    """Looks up private-raise funding from free SEC EDGAR Form D filings.

    Coverage is partial: US issuers only, matched by company name. A miss
    returns None (the company simply has no known funding signal).
    """

    def __init__(self, user_agent: str | None = None, max_filings: int = 3):
        ua = user_agent or settings.sec_user_agent
        # SEC requires a User-Agent with a contact email or it returns 403.
        self._client = httpx.AsyncClient(headers={"User-Agent": ua}, timeout=30.0)
        self._max_filings = max_filings
        self._warned_403 = False

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "FundingClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def lookup(self, company_name: str | None) -> FundingInfo | None:
        if not company_name or not company_name.strip():
            return None
        try:
            resp = await self._client.get(
                SEARCH_URL, params={"q": f'"{company_name}"', "forms": "D"}
            )
        except httpx.HTTPError as exc:
            log.warning("EDGAR search failed for %r: %s", company_name, exc)
            return None
        if resp.status_code != 200:
            return None

        hits = resp.json().get("hits", {}).get("hits", [])
        matched = [h for h in hits if _name_matches(company_name, _matched_name(h))]
        if not matched:
            return None
        # Most recent first.
        matched.sort(key=lambda h: h.get("_source", {}).get("file_date", ""), reverse=True)

        best_total = 0
        last_at: datetime | None = None
        best_url: str | None = None
        for hit in matched[: self._max_filings]:
            ref = _parse_filing_ref(hit)
            if ref is None:
                continue
            cik, acc, doc = ref
            doc_url = f"{ARCHIVE_BASE}/{cik}/{acc}/{doc}"
            amount = await self._fetch_amount(doc_url)
            file_date = _parse_date(hit.get("_source", {}).get("file_date"))
            if last_at is None and file_date is not None:
                last_at = file_date
                best_url = f"{ARCHIVE_BASE}/{cik}/{acc}/"
            if amount is not None and amount > best_total:
                best_total = amount
                if best_url is None:
                    best_url = f"{ARCHIVE_BASE}/{cik}/{acc}/"
            await asyncio.sleep(0.12)  # stay well under SEC's 10 req/s

        if best_total <= 0 and last_at is None:
            return None
        return FundingInfo(total=best_total, last_at=last_at, url=best_url)

    async def _fetch_amount(self, doc_url: str) -> int | None:
        try:
            resp = await self._client.get(doc_url)
        except httpx.HTTPError:
            return None
        if resp.status_code == 403 and not self._warned_403:
            self._warned_403 = True
            log.warning(
                "SEC returned 403 — set SEC_USER_AGENT to a string containing a contact email"
            )
        if resp.status_code != 200:
            return None
        return _parse_amount(resp.text)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except ValueError:
        return None
