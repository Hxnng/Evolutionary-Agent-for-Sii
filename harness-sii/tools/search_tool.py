"""
Web search tool — Serper + Jina, with optional search-proxy mode.

Default direct mode talks to Serper / Jina / 0x0 from this process, using
`SERPER_API_KEY` and `JINA_API_KEY` from `.env`.  If `SEARCH_PROXY_URL` is set,
the tool calls a running `search-proxy` service instead; this is useful when
the agent host cannot reach the public internet but another CPU host can.

The two public tool functions keep identical signatures and return shapes
so the LLM tool schema does not change between modes::

    search_text(query, top_k=5, fetch=True, max_chars=3000) -> list[dict]
    search_image(image, top_k=5, fetch=True, max_chars=1500) -> list[dict]

Each result dict::

    {"rank": int, "title": str, "url": str, "snippet": str, "content"?: str}
"""

from __future__ import annotations

import logging
import mimetypes
import os
import re
from html import unescape
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from pathlib import Path
from typing import Optional

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
IMAGE_UPLOADER      = os.getenv("IMAGE_UPLOADER", "0x0")
SEARCH_PROXY_URL    = os.getenv("SEARCH_PROXY_URL", "").rstrip("/")
SEARCH_PROXY_TOKEN  = os.getenv("SEARCH_PROXY_TOKEN", "") or os.getenv("PROXY_API_TOKEN", "")
SEARCH_PROXY_FALLBACK = os.getenv("SEARCH_PROXY_FALLBACK", "1") == "1"

SERPER_SEARCH_URL   = "https://google.serper.dev/search"
SERPER_LENS_URL     = "https://google.serper.dev/lens"
JINA_READER_BASE    = "https://r.jina.ai/"

DEFAULT_TIMEOUT     = 30
JINA_TIMEOUT        = 45


def _search_mode() -> str:
    return "proxy" if SEARCH_PROXY_URL else "direct"


# ---------------------------------------------------------------------------
# Proxy-mode helpers
# ---------------------------------------------------------------------------
def _proxy_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if SEARCH_PROXY_TOKEN:
        headers["Authorization"] = f"Bearer {SEARCH_PROXY_TOKEN}"
    return headers


def _proxy_post(path: str, payload: dict, timeout: float = DEFAULT_TIMEOUT) -> dict:
    if not SEARCH_PROXY_URL:
        raise RuntimeError("SEARCH_PROXY_URL not set")
    resp = requests.post(
        f"{SEARCH_PROXY_URL}{path}",
        json=payload,
        headers=_proxy_headers(),
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("ok") is False:
        raise RuntimeError(data.get("error") or f"proxy returned ok=false: {data}")
    return data


def _proxy_upload_local_image(path: Path) -> str:
    if not SEARCH_PROXY_URL:
        raise RuntimeError("SEARCH_PROXY_URL not set")
    if not path.exists():
        raise FileNotFoundError(path)
    headers = {}
    if SEARCH_PROXY_TOKEN:
        headers["Authorization"] = f"Bearer {SEARCH_PROXY_TOKEN}"
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"
    with path.open("rb") as fh:
        resp = requests.post(
            f"{SEARCH_PROXY_URL}/upload_image",
            files={"file": (path.name, fh, mime)},
            data={"filename": path.name},
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or f"proxy upload failed: {data}")
    return str(data.get("url") or "")


def _proxy_search_text(query: str, top_k: int, fetch: bool, max_chars: int) -> list[dict]:
    data = _proxy_post(
        "/search/text",
        {"query": query, "top_k": top_k, "fetch": fetch, "max_chars": max_chars},
        timeout=max(DEFAULT_TIMEOUT, JINA_TIMEOUT if fetch else DEFAULT_TIMEOUT),
    )
    return list(data.get("results") or [])


def _proxy_search_image(image_url: str, top_k: int, fetch: bool, max_chars: int) -> list[dict]:
    data = _proxy_post(
        "/search/image",
        {"image_url": image_url, "top_k": top_k, "fetch": fetch, "max_chars": max_chars},
        timeout=max(DEFAULT_TIMEOUT, JINA_TIMEOUT if fetch else DEFAULT_TIMEOUT),
    )
    return list(data.get("results") or [])


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


def _direct_upload_local_image(path: Path) -> str:
    if IMAGE_UPLOADER != "0x0":
        raise RuntimeError(
            f"Unsupported IMAGE_UPLOADER={IMAGE_UPLOADER!r}. "
            "Either set IMAGE_UPLOADER=0x0, or host the image yourself "
            "and pass an http(s) URL."
        )
    if not path.exists():
        raise FileNotFoundError(path)
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"
    with open(path, "rb") as fh:
        files = {"file": (path.name, fh, mime)}
        headers = {"User-Agent": "kimi-agent-harness/1.0"}
        resp = requests.post(
            "https://0x0.st", files=files, headers=headers, timeout=DEFAULT_TIMEOUT,
        )
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"Unexpected 0x0.st response: {url!r}")
    logger.info("Uploaded %s -> %s", path, url)
    return url


def _resolve_image_to_url_direct(image: str) -> str:
    if image.startswith("http://") or image.startswith("https://"):
        return image
    p = _resolve_local_image_path(image)
    if p.exists() and p.is_file():
        return _direct_upload_local_image(p)
    raise ValueError(
        f"search_image: {image!r} is neither an http(s) URL nor an existing local file."
    )


def _resolve_image_to_url_proxy(image: str) -> str:
    if image.startswith("http://") or image.startswith("https://"):
        return image
    p = _resolve_local_image_path(image)
    if p.exists() and p.is_file():
        return _proxy_upload_local_image(p)
    raise ValueError(
        f"search_image: {image!r} is neither an http(s) URL nor an existing local file."
    )


def _resolve_local_image_path(image: str) -> Path:
    """Resolve absolute, relative, and common SimpleVQA image references."""
    raw = (image or "").strip()
    p = Path(raw).expanduser()
    if p.exists() and p.is_file():
        return p

    here = Path(__file__).resolve()
    harness_dir = here.parents[1]
    roots: list[Path] = [
        Path.cwd(),
        harness_dir,
        harness_dir / "data" / "simpleVQA" / "simpleVQA_datasets",
    ]
    env_roots = os.getenv("SEARCH_IMAGE_ROOTS") or os.getenv("IMAGE_ROOT") or ""
    for part in env_roots.split(os.pathsep):
        if part.strip():
            roots.insert(0, Path(part.strip()).expanduser())

    candidates: list[Path] = []
    for root in roots:
        candidates.append(root / raw)
        candidates.append(root / Path(raw).name)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    # Last-resort bounded recursive lookup for bare filenames like
    # ``5842....jpg`` produced by some vision APIs.
    name = Path(raw).name
    if name and name == raw and any(name.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
        for root in roots:
            if root.exists() and root.is_dir():
                try:
                    match = next(root.rglob(name), None)
                except Exception:  # noqa: BLE001
                    match = None
                if match and match.is_file():
                    return match
    return p


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
    if SEARCH_PROXY_URL:
        try:
            return _proxy_search_text(query, top_k, fetch, int(max_chars))
        except Exception as exc:  # noqa: BLE001
            if not SEARCH_PROXY_FALLBACK:
                raise
            logger.warning("search proxy failed; falling back to direct mode: %s", exc)

    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set; using DuckDuckGo HTML fallback")
        return _duckduckgo_search(query, top_k, fetch, int(max_chars))

    payload = {"q": query, "num": top_k}
    data = _serper_post(SERPER_SEARCH_URL, payload)
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

    ``image`` may be an http(s) URL or a local file path. In direct mode,
    local files are pushed to a public host (default 0x0.st).
    """
    if not image or not image.strip():
        raise ValueError("search_image requires a non-empty `image` argument.")
    top_k = max(1, min(int(top_k), 10))

    logger.info("search_image(%s) image=%s top_k=%d fetch=%s",
                _search_mode(), image[:120], top_k, fetch)
    if SEARCH_PROXY_URL:
        try:
            image_url = _resolve_image_to_url_proxy(image.strip())
            return _proxy_search_image(image_url, top_k, fetch, int(max_chars))
        except Exception as exc:  # noqa: BLE001
            if not SEARCH_PROXY_FALLBACK:
                raise
            logger.warning("search proxy failed; falling back to direct mode: %s", exc)

    image_url = _resolve_image_to_url_direct(image.strip())
    logger.info("search_image(direct) image_url=%s top_k=%d fetch=%s",
                image_url, top_k, fetch)
    payload = {"url": image_url}
    data = _serper_post(SERPER_LENS_URL, payload)
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
    p_img.add_argument("image", help="URL or local path")
    p_img.add_argument("--top-k", type=int, default=3)
    p_img.add_argument("--no-fetch", action="store_true")

    args = ap.parse_args()

    print(f"[mode] {_search_mode()}")

    if args.cmd == "text":
        out = search_text(args.query, top_k=args.top_k, fetch=not args.no_fetch)
    else:
        out = search_image(args.image, top_k=args.top_k, fetch=not args.no_fetch)

    print(json.dumps(out, ensure_ascii=False, indent=2)[:5000])
