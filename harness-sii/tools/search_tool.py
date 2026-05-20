"""
Web search tool — Serper + Jina, with optional search-proxy mode.

Default direct mode talks to Serper / Jina from this process, using
`SERPER_API_KEY` and `JINA_API_KEY` from `.env`.  If `SEARCH_PROXY_URL` is set,
the tool calls a running `search-proxy` service instead; this is useful when
the agent host cannot reach the public internet but another CPU host can.

`search_image` only accepts public http(s) image URLs. Local files are not
uploaded on the fly, which avoids concurrent 0x0/proxy upload failures during
parallel evaluation. Use model vision or `search_text` for local images.

The two public tool functions keep identical signatures and return shapes
so the LLM tool schema does not change between modes::

    search_text(query, top_k=5, fetch=True, max_chars=3000) -> list[dict]
    search_image(image, top_k=5, fetch=True, max_chars=1500) -> list[dict]

Each result dict::

    {"rank": int, "title": str, "url": str, "snippet": str, "content"?: str}
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from html import unescape
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from pathlib import Path

import requests

def _load_env_file(path: Path, override: bool = True) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value


here = Path(__file__).resolve()
_load_env_file(here.parents[2] / ".env", override=False)
_load_env_file(here.parents[1] / ".env", override=True)

logger = logging.getLogger("harness.tools.search")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# Direct Serper/Jina mode.
SERPER_API_KEY      = os.getenv("SERPER_API_KEY", "")
JINA_API_KEY        = os.getenv("JINA_API_KEY", "")
SEARCH_PROXY_URL    = os.getenv("SEARCH_PROXY_URL", "").rstrip("/")
SEARCH_PROXY_TOKEN  = os.getenv("SEARCH_PROXY_TOKEN", "") or os.getenv("PROXY_API_TOKEN", "")
SEARCH_PROXY_FALLBACK = os.getenv("SEARCH_PROXY_FALLBACK", "1") == "1"
PROXY_HTTP_TIMEOUT  = float(os.getenv("SEARCH_PROXY_TIMEOUT", "120"))
SEARCH_PROXY_VERIFY_SSL = os.getenv("SEARCH_PROXY_VERIFY_SSL", "true").lower() not in (
    "0", "false", "no"
)
try:
    SEARCH_PROXY_EXTRA_HEADERS: dict = json.loads(
        os.getenv("SEARCH_PROXY_EXTRA_HEADERS", "") or "{}"
    )
    if not isinstance(SEARCH_PROXY_EXTRA_HEADERS, dict):
        SEARCH_PROXY_EXTRA_HEADERS = {}
except Exception:  # noqa: BLE001
    SEARCH_PROXY_EXTRA_HEADERS = {}

SERPER_SEARCH_URL   = "https://google.serper.dev/search"
SERPER_LENS_URL     = "https://google.serper.dev/lens"
JINA_READER_BASE    = "https://r.jina.ai/"

DEFAULT_TIMEOUT     = 30
JINA_TIMEOUT        = 45
# Off by default: many hosts block Range probes; Serper Lens is the real check.
IMAGE_URL_PROBE_RETRIES = max(0, int(os.getenv("IMAGE_URL_PROBE_RETRIES", "0")))
IMAGE_URL_PROBE_DELAY = float(os.getenv("IMAGE_URL_PROBE_DELAY", "0.8"))
IMAGE_URL_PROBE_STRICT = os.getenv("IMAGE_URL_PROBE_STRICT", "0") == "1"


def _search_mode() -> str:
    return "proxy" if SEARCH_PROXY_URL else "direct"


def _proxy_enabled() -> bool:
    return bool(SEARCH_PROXY_URL)


# ---------------------------------------------------------------------------
# Proxy-mode helpers
# ---------------------------------------------------------------------------
def _proxy_headers(json_body: bool = True) -> dict[str, str]:
    headers: dict[str, str] = {}
    if json_body:
        headers["Content-Type"] = "application/json"
    if SEARCH_PROXY_TOKEN:
        headers["Authorization"] = f"Bearer {SEARCH_PROXY_TOKEN}"
    if SEARCH_PROXY_EXTRA_HEADERS:
        headers.update({str(k): str(v) for k, v in SEARCH_PROXY_EXTRA_HEADERS.items()})
    return headers


def _proxy_post(path: str, payload: dict, timeout: float | None = None) -> dict:
    if not SEARCH_PROXY_URL:
        raise RuntimeError("SEARCH_PROXY_URL not set")
    resp = requests.post(
        f"{SEARCH_PROXY_URL}{path}",
        json=payload,
        headers=_proxy_headers(json_body=True),
        timeout=timeout or PROXY_HTTP_TIMEOUT,
        verify=SEARCH_PROXY_VERIFY_SSL,
    )
    resp.raise_for_status()
    return resp.json()


def _proxy_search(path: str, payload: dict) -> list[dict]:
    """POST /search/text or /search/image; normalize to the legacy result shape."""
    timeout = max(DEFAULT_TIMEOUT, JINA_TIMEOUT if payload.get("fetch") else DEFAULT_TIMEOUT)
    try:
        data = _proxy_post(path, payload, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        logger.warning("search-proxy %s transport failed: %s", path, exc)
        return [{"rank": 1, "title": "", "url": "", "snippet": f"[proxy-error] {type(exc).__name__}: {exc}"}]

    if not data.get("ok", False):
        err = data.get("error", "unknown proxy error")
        logger.warning("search-proxy %s failed: %s", path, err)
        return [{"rank": 1, "title": "", "url": "", "snippet": f"[proxy-error] {err}"}]

    out: list[dict] = []
    for hit in data.get("results", []) or []:
        entry = {
            "rank": hit.get("rank", len(out) + 1),
            "title": hit.get("title", ""),
            "url": hit.get("url", ""),
            "snippet": hit.get("snippet", ""),
        }
        if hit.get("content") is not None:
            entry["content"] = hit["content"]
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Direct-mode helpers
# ---------------------------------------------------------------------------
def _require_serper_key() -> str:
    if not SERPER_API_KEY:
        raise RuntimeError(
            "SERPER_API_KEY not set. Fill SERPER_API_KEY in harness-sii/.env."
        )
    return SERPER_API_KEY


def _serper_post(url: str, payload: dict) -> dict:
    headers = {
        "X-API-KEY":    _require_serper_key(),
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s or "")
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _duckduckgo_search(query: str, top_k: int, fetch: bool, max_chars: int) -> list[dict]:
    """No-key fallback search for local smoke tests.

    Serper remains the preferred benchmark path.  This fallback avoids a hard
    crash when keys are not configured, and gives the agent real evidence
    instead of forcing it to hallucinate.
    """
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; sii-harness/0.1)"}
    try:
        resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return [
            {
                "rank": 1,
                "title": "search unavailable",
                "url": "",
                "snippet": (
                    "Search is unavailable: configure SERPER_API_KEY. "
                    f"DuckDuckGo fallback failed: {type(exc).__name__}: {exc}"
                ),
            }
        ]

    html = resp.text or ""
    blocks = re.findall(r'(?is)<div[^>]+class="[^"]*result[^"]*"[^>]*>(.*?)</div>\s*</div>', html)
    if not blocks:
        blocks = re.findall(r'(?is)<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)

    results: list[dict] = []
    for block in blocks:
        if isinstance(block, tuple):
            href, title_html = block
            snippet_html = ""
        else:
            a = re.search(r'(?is)<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block)
            if not a:
                continue
            href, title_html = a.group(1), a.group(2)
            snip = re.search(r'(?is)<a[^>]+class="result__snippet"[^>]*>(.*?)</a>|<div[^>]+class="result__snippet"[^>]*>(.*?)</div>', block)
            snippet_html = (snip.group(1) or snip.group(2)) if snip else ""

        parsed = urlparse(unescape(href))
        qs = parse_qs(parsed.query)
        target = unquote(qs.get("uddg", [unescape(href)])[0])
        if not target.startswith(("http://", "https://")):
            continue
        entry = {
            "rank": len(results) + 1,
            "title": _strip_html(title_html),
            "url": target,
            "snippet": _strip_html(snippet_html),
            "source": "duckduckgo_html_fallback",
        }
        if fetch:
            entry["content"] = _jina_fetch(target, max_chars)
        results.append(entry)
        if len(results) >= top_k:
            break

    if not results:
        return [
            {
                "rank": 1,
                "title": "no fallback search results",
                "url": "",
                "snippet": "No results parsed from DuckDuckGo fallback. Configure SERPER_API_KEY for reliable search.",
            }
        ]
    return results


def _jina_fetch(url: str, max_chars: int) -> str:
    if not url:
        return ""
    reader_url = JINA_READER_BASE + url
    headers = {"Accept": "text/plain"}
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"
    try:
        resp = requests.get(reader_url, headers=headers, timeout=JINA_TIMEOUT)
        resp.raise_for_status()
        text = resp.text or ""
        if max_chars and len(text) > max_chars:
            text = text[:max_chars] + f"\n\n...[truncated at {max_chars} chars]"
        return text
    except Exception as exc:  # noqa: BLE001
        logger.warning("Jina fetch failed for %s: %s", url, exc)
        return f"[jina-error] {type(exc).__name__}: {exc}"


def _require_image_url(image_url: str) -> str:
    """Validate that ``image_url`` is a public http(s) URL."""
    if not image_url or not str(image_url).strip():
        raise ValueError("search_image requires a non-empty image URL.")
    s = str(image_url).strip()
    if not (s.startswith("http://") or s.startswith("https://")):
        raise ValueError(
            f"search_image: {s!r} is not an http(s) URL. "
            "Local image upload has been disabled to avoid concurrent upload failures — "
            "pass a publicly reachable URL, or use vision / search_text instead."
        )
    return s


def _probe_image_url(image_url: str) -> bool:
    """Best-effort check that Serper Lens can reach the image URL."""
    headers = {"User-Agent": "kimi-agent-harness/1.0", "Range": "bytes=0-1023"}
    for attempt in range(IMAGE_URL_PROBE_RETRIES + 1):
        try:
            resp = requests.get(
                image_url,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True,
                stream=True,
            )
            if resp.status_code < 400:
                return True
            logger.warning(
                "image URL probe failed (%s) attempt=%d url=%s",
                resp.status_code,
                attempt + 1,
                image_url[:120],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "image URL probe error attempt=%d url=%s: %s",
                attempt + 1,
                image_url[:120],
                exc,
            )
        if attempt < IMAGE_URL_PROBE_RETRIES:
            time.sleep(IMAGE_URL_PROBE_DELAY)
    return False


def _image_search_unavailable(
    reason: str,
    image: str = "",
    *,
    kind: str = "generic",
) -> list[dict]:
    hints = {
        "local_path": (
            "Reverse image search needs a public http(s) image URL. "
            f"{reason} Use the model's visual understanding, atomic_fact/source_digest, "
            "or search_text instead of uploading local files."
        ),
        "probe": (
            f"Image URL probe failed: {reason} "
            "You may retry later, use another public URL, or fall back to vision/search_text."
        ),
        "lens": (
            f"Serper Lens could not process the image URL: {reason} "
            "Use vision/search_text, or verify the URL is publicly reachable."
        ),
        "generic": (
            f"Reverse image search could not run: {reason} "
            "Use the model's visual understanding, atomic_fact/source_digest, "
            "or search_text with the identified entity and requested attribute."
        ),
    }
    return [
        {
            "rank": 1,
            "title": "image search unavailable",
            "url": "",
            "snippet": hints.get(kind, hints["generic"]),
            "ok": False,
            "error": reason,
            "image": image,
        }
    ]


def _resolve_public_image_url(image: str) -> str:
    """Return a public http(s) URL, or raise if only a local path was supplied."""
    raw = (image or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return _require_image_url(raw)
    raise ValueError(
        f"search_image: {raw!r} is not an http(s) URL. "
        "Concurrent local uploads to public hosts are disabled; use the model's "
        "vision input, atomic_fact/source_digest, or search_text instead."
    )


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------
def search_text(
    query: str,
    top_k: int = 3,
    fetch: bool = True,
    max_chars: int = 3000,
) -> list[dict]:
    """Text search on Google (via Serper) optionally enriched with full-text via Jina.

    Returns ``list[dict]`` with keys ``{rank, title, url, snippet, content?}``.
    """
    if not query or not query.strip():
        return []
    top_k = max(1, min(int(top_k), 10))

    logger.info("search_text(%s) q=%r top_k=%d fetch=%s",
                _search_mode(), query, top_k, fetch)
    if _proxy_enabled():
        try:
            results = _proxy_search(
                "/search/text",
                {
                    "query": query,
                    "top_k": top_k,
                    "fetch": bool(fetch),
                    "max_chars": int(max_chars),
                },
            )
            if results and not str(results[0].get("snippet", "")).startswith("[proxy-error]"):
                return results
            if not SEARCH_PROXY_FALLBACK:
                return results
            logger.warning("search proxy returned error; falling back to direct mode")
        except Exception as exc:  # noqa: BLE001
            if not SEARCH_PROXY_FALLBACK:
                raise
            logger.warning("search proxy failed; falling back to direct mode: %s", exc)

    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set; using DuckDuckGo HTML fallback")
        return _duckduckgo_search(query, top_k, fetch, int(max_chars))

    payload = {"q": query, "num": top_k}
    try:
        data = _serper_post(SERPER_SEARCH_URL, payload)
    except Exception as exc:  # noqa: BLE001
        reason = f"{type(exc).__name__}: {exc}"
        logger.warning("search_text Serper request failed; using fallback: %s", reason)
        fallback = _duckduckgo_search(query, top_k, fetch, int(max_chars))
        if fallback:
            fallback[0]["snippet"] = (
                f"[serper-error] {reason}; fallback result: "
                + str(fallback[0].get("snippet", ""))
            )
        return fallback or [
            {
                "rank": 1,
                "title": "search unavailable",
                "url": "",
                "snippet": f"[serper-error] {reason}; no fallback results.",
            }
        ]
    organic = data.get("organic", []) or []

    results: list[dict] = []
    for rank, item in enumerate(organic[:top_k], start=1):
        url = item.get("link") or ""
        entry = {
            "rank":    rank,
            "title":   item.get("title", ""),
            "url":     url,
            "snippet": item.get("snippet", ""),
        }
        if fetch and url:
            entry["content"] = _jina_fetch(url, max_chars)
        results.append(entry)
    return results


def search_image(
    image: str,
    top_k: int = 1,
    fetch: bool = True,
    max_chars: int = 1500,
) -> list[dict]:
    """Reverse image search via Google Lens (Serper /lens).

    ``image`` must be a publicly reachable http(s) URL. Local paths are not
    uploaded on the fly (avoids concurrent 0x0/proxy upload failures).
    """
    if not image or not image.strip():
        raise ValueError("search_image requires a non-empty `image` argument.")
    top_k = max(1, min(int(top_k), 10))
    raw_image = image.strip()

    try:
        image_url = _resolve_public_image_url(raw_image)
    except ValueError as exc:
        reason = str(exc)
        logger.warning("search_image unavailable: %s", reason)
        return _image_search_unavailable(reason, image=raw_image, kind="local_path")

    if IMAGE_URL_PROBE_RETRIES > 0:
        if not _probe_image_url(image_url):
            reason = (
                f"image URL not reachable after {IMAGE_URL_PROBE_RETRIES + 1} "
                f"probes: {image_url}"
            )
            logger.warning("search_image probe failed: %s", reason)
            if IMAGE_URL_PROBE_STRICT:
                return _image_search_unavailable(reason, image=image_url, kind="probe")
        else:
            logger.info("search_image probe ok: %s", image_url[:120])

    logger.info(
        "search_image(%s) image_url=%s top_k=%d fetch=%s",
        _search_mode(),
        image_url[:120],
        top_k,
        fetch,
    )

    if _proxy_enabled():
        results = _proxy_search(
            "/search/image",
            {
                "image_url": image_url,
                "top_k": top_k,
                "fetch": bool(fetch),
                "max_chars": int(max_chars),
            },
        )
        if results and not str(results[0].get("snippet", "")).startswith("[proxy-error]"):
            return results
        if not SEARCH_PROXY_FALLBACK:
            return results
        logger.warning("search_image proxy failed; falling back to direct mode")

    payload = {"url": image_url}
    try:
        data = _serper_post(SERPER_LENS_URL, payload)
    except Exception as exc:  # noqa: BLE001
        reason = f"{type(exc).__name__}: {exc}"
        logger.warning("search_image lens request failed: %s", reason)
        return _image_search_unavailable(reason, image=image_url, kind="lens")
    items = data.get("organic") or data.get("visual_matches") or []

    results: list[dict] = []
    for rank, item in enumerate(items[:top_k], start=1):
        url = item.get("link") or item.get("url") or ""
        entry = {
            "rank":    rank,
            "title":   item.get("title", ""),
            "url":     url,
            "snippet": item.get("snippet", "") or item.get("source", ""),
        }
        if fetch and url:
            entry["content"] = _jina_fetch(url, max_chars)
        results.append(entry)
    return results


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_text = sub.add_parser("text")
    p_text.add_argument("query")
    p_text.add_argument("--top-k", type=int, default=3)
    p_text.add_argument("--no-fetch", action="store_true")

    p_img = sub.add_parser("image")
    p_img.add_argument("image", help="Public http(s) image URL")
    p_img.add_argument("--top-k", type=int, default=3)
    p_img.add_argument("--no-fetch", action="store_true")

    args = ap.parse_args()

    print(f"[mode] {_search_mode()}")

    if args.cmd == "text":
        out = search_text(args.query, top_k=args.top_k, fetch=not args.no_fetch)
    else:
        out = search_image(args.image, top_k=args.top_k, fetch=not args.no_fetch)

    print(json.dumps(out, ensure_ascii=False, indent=2)[:5000])
