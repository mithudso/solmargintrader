#!/usr/bin/env python3
"""Archive a bounded public Jupiter app graph; never execute downloaded code.

This records public response bodies outside the checkout. It uses no browser,
cookies, credentials, source-map execution, wallet requests, or transaction APIs.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

PORTAL = "https://jup.ag/1000x?market=SOL&mode=classic"
SCRIPT = re.compile(
    r"(?P<q>[\"'`])(?P<url>(?:https://|/|\.{1,2}/|assets/)[^\"'`\s]{1,3000}?"
    r"\.m?js(?:[?#][^\"'`\s]*|/[^\"'`\s]+)?)(?P=q)"
)
SOURCE_MAP = re.compile(r"[#@]\s*sourceMappingURL\s*=\s*(\S+)")
DYNAMIC_IMPORT = re.compile(r"\bimport\s*\(\s*([^)]{1,220})\)")
SAFE_HEADERS = {"content-type", "content-security-policy", "access-control-allow-origin"}


class Resources(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.urls.add(str(values["src"]))
        if tag == "link" and values.get("href") and values.get("rel") in {
            "modulepreload", "preload", "manifest"
        }:
            href = str(values["href"])
            if re.search(r"\.m?js(?:[?#]|$)", href) or values.get("rel") == "manifest":
                self.urls.add(href)


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl):
            raise ValueError("redirect_outside_public_asset_boundary")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and (parsed.hostname == "jup.ag" or str(parsed.hostname).endswith(".jup.ag")
             or parsed.hostname == "static.cloudflareinsights.com")
        and not parsed.query
    )


def asset_url(reference: str, base: str) -> str | None:
    if reference.startswith("assets/"):
        parsed_base = urllib.parse.urlsplit(base)
        base = f"{parsed_base.scheme}://{parsed_base.netloc}/"
    url = urllib.parse.urljoin(base, reference)
    parts = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    return url if safe_url(url) else None


def retrieve(url: str, output: Path, max_file: int, timeout: float = 25) -> tuple[dict, bytes]:
    record = {"url": url, "retrievedAt": datetime.now(UTC).isoformat()}
    try:
        opener = urllib.request.build_opener(PublicRedirect)
        req = urllib.request.Request(url, headers={"User-Agent": "Public Jupiter asset audit/1.0"})
        try:
            response = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            body = response.read(max_file + 1)
            record.update(status=response.status, responseUrl=response.url, headers={
                key.lower(): value for key, value in response.headers.items()
                if key.lower() in SAFE_HEADERS
            })
        if len(body) > max_file:
            record.update(error="file_byte_limit", bytesRead=len(body))
            return record, b""
        digest = hashlib.sha256(body).hexdigest()
        name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(urllib.parse.urlsplit(url).path).name)[:140]
        path = output / "responses" / f"{hashlib.sha256(url.encode()).hexdigest()[:16]}-{digest[:12]}-{name or 'document'}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        record.update(sha256=digest, bytes=len(body), file=str(path))
        return record, body
    except (OSError, ValueError, urllib.error.URLError) as exc:
        record["error"] = type(exc).__name__
        return record, b""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--observed", type=Path, help="JSON array, or object with assets/urls list")
    parser.add_argument("--max-assets", type=int, default=2000)
    parser.add_argument("--max-bytes", type=int, default=160_000_000)
    parser.add_argument("--max-file-bytes", type=int, default=25_000_000)
    parser.add_argument("--max-seconds", type=int, default=1200)
    parser.add_argument("--requests-per-second", type=float, default=4)
    args = parser.parse_args()
    output = args.output.resolve()
    checkout = Path(__file__).resolve().parents[3]
    if output.is_relative_to(checkout):
        parser.error("--output must be outside the repository; vendor bodies must not enter Git")
    if min(args.max_assets, args.max_bytes, args.max_file_bytes, args.max_seconds,
           args.requests_per_second) <= 0:
        parser.error("limits must be positive")
    output.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.max_seconds
    document, body = retrieve(PORTAL, output, min(args.max_file_bytes, args.max_bytes),
                              min(25, args.max_seconds))
    resources = Resources()
    resources.feed(body.decode("utf-8", errors="replace"))
    references: dict[str, set[str]] = {}
    skipped: list[dict] = []

    def enqueue(reference: str, base: str) -> None:
        url = asset_url(reference, base)
        if url:
            references.setdefault(url, set()).add(base)
        else:
            # Retain only asset locations, never query parameters that might carry session state.
            parts = urllib.parse.urlsplit(urllib.parse.urljoin(base, reference))
            skipped.append({"location": f"{parts.scheme}://{parts.netloc}{parts.path}",
                            "reason": "outside_public_asset_boundary_or_query"})

    for reference in resources.urls:
        enqueue(reference, PORTAL)
    if args.observed:
        observed = json.loads(args.observed.read_text())
        if isinstance(observed, dict):
            observed = observed.get("assets", observed.get("urls", []))
        for reference in observed:
            if isinstance(reference, str):
                enqueue(reference, PORTAL)
    records: dict[str, dict] = {}
    maps: dict[str, dict] = {}
    dynamic: list[dict] = []
    total = int(document.get("bytes", 0))
    stopped = None
    throttle_lock = threading.Lock()
    next_request = [0.0]
    remaining_bytes = [args.max_bytes - total]

    def throttled_get(url: str) -> tuple[dict, bytes]:
        with throttle_lock:
            now = time.monotonic()
            delay = max(0.0, next_request[0] - now)
            next_request[0] = max(now, next_request[0]) + 1 / args.requests_per_second
        if delay:
            time.sleep(delay)
        with throttle_lock:
            allowance = min(args.max_file_bytes, remaining_bytes[0])
            if allowance <= 0 or time.monotonic() >= deadline:
                return {"url": url, "error": "capture_byte_or_time_limit"}, b""
            remaining_bytes[0] -= allowance
        record, payload = retrieve(url, output, allowance, min(25, max(.01, deadline - time.monotonic())))
        with throttle_lock:
            remaining_bytes[0] += max(0, allowance - record.get("bytes", record.get("bytesRead", 0)))
        return record, payload

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        while pending := sorted(set(references) - set(records)):
            pending = pending[:max(0, args.max_assets - len(records))]
            if not pending or total >= args.max_bytes or time.monotonic() >= deadline:
                stopped = "asset_total_byte_or_time_limit"
                break
            results = pool.map(throttled_get, pending)
            map_queue: set[str] = set()
            for record, payload in results:
                url = record["url"]
                records[url] = record
                total += record.get("bytes", 0)
                if record.get("status") != 200 or not payload:
                    continue
                text = payload.decode("utf-8", errors="replace")
                for match in SCRIPT.finditer(text):
                    enqueue(match["url"], url)
                for match in DYNAMIC_IMPORT.finditer(text):
                    expression = match[1].strip()
                    if not re.fullmatch(r"[\"'`][^\"'`${}]+[\"'`]", expression):
                        dynamic.append({"url": url, "offset": match.start(), "expression": expression})
                advertised = SOURCE_MAP.findall(text)
                candidates = advertised or ([url + ".map"] if urllib.parse.urlsplit(url).path.endswith((".js", ".mjs")) else [])
                for reference in candidates:
                    mapped = asset_url(reference, url)
                    if mapped:
                        record.setdefault("sourceMaps", []).append(mapped)
                        if mapped not in maps:
                            map_queue.add(mapped)
                    else:
                        record["mapGap"] = "inline_or_outside_public_asset_boundary"
            for record, payload in pool.map(throttled_get, sorted(map_queue)):
                maps[record["url"]] = record
                total += record.get("bytes", 0)
                if record.get("status") == 200:
                    try:
                        parsed = json.loads(payload)
                        record["validSourceMap"] = parsed.get("version") == 3
                        record["sources"] = len(parsed.get("sources", []))
                        record["sourcesContent"] = sum(x is not None for x in parsed.get("sourcesContent", []))
                    except (ValueError, AttributeError):
                        record["validSourceMap"] = False
            print(f"Retrieved {len(records)} assets and {len(maps)} map attempts; {total} bytes", flush=True)
    for url, record in records.items():
        record["referencedBy"] = sorted(references[url])
    if any(record.get("error") == "capture_byte_or_time_limit"
           for record in [*records.values(), *maps.values()]):
        stopped = "capture_byte_or_time_limit"
    manifest = {
        "version": 1, "portal": PORTAL, "capturedAt": datetime.now(UTC).isoformat(),
        "document": document, "assets": list(records.values()), "maps": list(maps.values()),
        "limits": {"maxAssets": args.max_assets, "maxBytes": args.max_bytes,
                   "maxFileBytes": args.max_file_bytes, "maxSeconds": args.max_seconds,
                   "requestsPerSecond": args.requests_per_second}, "bytes": total,
        "stopReason": stopped, "pending": sorted(set(references) - set(records)),
        "unresolvedDynamicImports": dynamic, "skipped": skipped,
        "coverage": "Finite app build: public HTML scripts/preloads, observed seeds, and literal JS references in retrieved modules/manifests. Map URLs are advertised or conventional .js.map probes. No execution of downloaded code. Runtime-computed paths, unvisited lazy interactions, authenticated resources and deployment changes remain outside this census.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"assets": len(records), "maps": len(maps), "bytes": total,
                      "pending": len(manifest["pending"]), "manifest": str(output / "manifest.json")}))
    return 1 if document.get("status") != 200 or stopped else 0


if __name__ == "__main__":
    raise SystemExit(main())
