"""Wikipedia (MediaWiki Action API) research provider.

Only the fixed Wikipedia host is ever contacted (no user-supplied URLs => no SSRF surface). Wikipedia's
API is free for automated, rate-respecting use with a descriptive User-Agent; content is CC BY-SA, and we
store only short excerpts plus the source URL for attribution.
"""

from __future__ import annotations

import re
import time
import urllib.parse

import httpx

from app.application.ports import ProviderHealth, Source

_API = "https://en.wikipedia.org/w/api.php"
_TAGS = re.compile(r"<[^>]+>")
MISSING_CONTACT = (
    "Set NARRAVO_RESEARCH_CONTACT to an email or URL: Wikimedia's API policy requires a contact in the "
    "User-Agent. Until then scripts are written without source checks and claims stay unverified."
)


class ResearchUnavailableError(RuntimeError):
    pass


class WikipediaResearchProvider:
    name = "wikipedia"

    def __init__(self, contact: str | None, min_interval: float = 0.5) -> None:
        self.contact = (contact or "").strip()
        self.headers = {"User-Agent": f"NaRRAVO/0.1 (self-hosted fact-check module; contact: {self.contact}) httpx"}
        self.min_interval = min_interval
        self._last = 0.0

    def _get(self, params: dict) -> dict:
        if not self.contact:
            raise ResearchUnavailableError(MISSING_CONTACT)
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        resp = httpx.get(_API, params={**params, "format": "json", "formatversion": 2}, headers=self.headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> ProviderHealth:
        if not self.contact:
            return ProviderHealth(self.name, "research", False, MISSING_CONTACT)
        try:
            self._get({"action": "query", "meta": "siteinfo"})
        except httpx.HTTPError as exc:
            return ProviderHealth(self.name, "research", False, f"Wikipedia unreachable ({type(exc).__name__})")
        return ProviderHealth(self.name, "research", True, "Wikipedia API (CC BY-SA excerpts with attribution)")

    def search_sources(self, query: str, limit: int = 3) -> list[Source]:
        data = self._get({"action": "query", "list": "search", "srsearch": query[:250], "srlimit": limit})
        out = []
        for hit in data.get("query", {}).get("search", []):
            title = hit["title"]
            out.append(Source(title, self._url(title), _TAGS.sub("", hit.get("snippet", ""))))
        return out

    def retrieve_source(self, title: str) -> Source | None:
        data = self._get({"action": "query", "prop": "extracts", "explaintext": 1, "exchars": 4000, "titles": title[:250],
                          "redirects": 1})  # fmt: skip
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            return None
        page = pages[0]
        return Source(page["title"], self._url(page["title"]), page.get("extract", ""))

    @staticmethod
    def _url(title: str) -> str:
        return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
