from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

import cloudscraper
import requests
import trafilatura
from bs4 import BeautifulSoup

from core.exceptions import EmptyContentError, InvalidLinkError, ScrapeError

DEFAULT_TIMEOUT = 15

# Many sites 403 plain `requests` calls and sit behind a Cloudflare-style challenge.
# cloudscraper solves that challenge (same thing a real browser's JS does) so we can
# still fetch a page the user themselves can already see in their own browser.
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_scraper = None


def _get_scraper() -> cloudscraper.CloudScraper:
    global _scraper
    if _scraper is None:
        _scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True}
        )
        _scraper.headers.update(HEADERS)
    return _scraper


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise InvalidLinkError(f"'{url}' is not a valid HTTP/HTTPS URL.")


def fetch_html(url: str) -> str:
    scraper = _get_scraper()
    try:
        response = scraper.get(url, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
    except cloudscraper.exceptions.CloudflareException as exc:
        raise ScrapeError(
            f"{url} is protected by anti-bot measures that couldn't be solved "
            f"automatically ({exc}). Use the 'Paste Content' tab to add it manually instead."
        ) from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (401, 403, 429):
            raise ScrapeError(
                f"{url} returned HTTP {status} — this site is likely blocking automated "
                f"requests. Use the 'Paste Content' tab to add it manually instead."
            ) from exc
        raise ScrapeError(f"Failed to fetch {url}: {exc}") from exc
    except requests.RequestException as exc:
        raise ScrapeError(f"Failed to fetch {url}: {exc}") from exc
    return response.text


def extract_title(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return fallback


def extract_readable_content(html: str, url: str) -> str:
    extracted = trafilatura.extract(
        html, url=url, include_comments=False, include_tables=True, favor_recall=True
    )
    if extracted and extracted.strip():
        return extracted.strip()

    # Fallback: strip obvious boilerplate tags and return remaining text.
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def ingest_website(url: str) -> dict:
    validate_url(url)
    html = fetch_html(url)
    title = extract_title(html, fallback=url)
    content = extract_readable_content(html, url)

    if not content or len(content) < 50:
        raise EmptyContentError(f"No readable content could be extracted from {url}.")

    markdown = (
        f"# {title}\n\n"
        f"Source: {url}\n\n"
        f"Retrieved: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"## Content\n\n{content}\n"
    )

    return {
        "title": title,
        "source_url": url,
        "source_type": "website",
        "content": markdown,
    }
