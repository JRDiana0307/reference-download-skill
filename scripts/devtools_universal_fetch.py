#!/usr/bin/env python3
"""Universal PDF fetch from any publisher through Edge DevTools session.
Strategy: from article page, find PDF URL, then fetch() it same-origin.
Supports: ScienceDirect, Springer, AIAA, Taylor & Francis, IOP, Emerald, etc.
"""

from __future__ import annotations

import argparse, base64, csv, json, re, sys, time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
import websocket


def parse_args():
    parser = argparse.ArgumentParser(description="Universal PDF fetch through DevTools")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--debug-port", type=int, default=9222)
    parser.add_argument("--page-wait-seconds", type=int, default=12)
    parser.add_argument("--inter-item-sleep-seconds", type=int, default=10)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def sanitize_name(text, fallback):
    cleaned = re.sub(r'[<>:"/\\|?*]+', " ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:180] or fallback


def make_target_name(number, first_author, year, title):
    author = sanitize_name(first_author, f"ref{number}")
    title_clean = sanitize_name(title, "untitled")
    return f"[{int(number)}]{author}等 - {year} - {title_clean}.pdf"


def write_utf8_no_bom(path, text):
    path.write_text(text, encoding="utf-8")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        path.write_bytes(raw[3:])


def title_similarity(t1, t2):
    def norm(s):
        return set(re.sub(r'[^a-z0-9]+', ' ', s.lower()).split())
    w1, w2 = norm(t1), norm(t2)
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / min(len(w1), len(w2))


class DevToolsClient:
    def __init__(self, debug_port):
        self.base = f"http://127.0.0.1:{debug_port}"

    def http_get(self, url, method="GET"):
        req = Request(url, method=method)
        with urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")

    def open_page(self, url):
        raw = self.http_get(f"{self.base}/json/new?{quote(url, safe=':/?&=%')}", method="PUT")
        return json.loads(raw)

    def close_page(self, page_id):
        try: self.http_get(f"{self.base}/json/close/{page_id}")
        except: pass

    @staticmethod
    def ws_connect(ws_url, timeout=180):
        return websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)

    @staticmethod
    def ws_call(ws, method, params=None, msg_id=1):
        ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == msg_id:
                return msg

    @staticmethod
    def ws_evaluate(ws, expression, await_promise=False, msg_id=1):
        msg = DevToolsClient.ws_call(ws, "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": await_promise}, msg_id=msg_id)
        return msg["result"]["result"].get("value")


def find_pdf_url(ws):
    """Find PDF URL on any publisher's article page."""
    # Pattern 1: citation_pdf_url meta tag (Springer, MDPI, IOP, Emerald, etc.)
    result = DevToolsClient.ws_evaluate(ws, """
    (function() {
        const meta = document.querySelector('meta[name="citation_pdf_url"]');
        if (meta) return meta.getAttribute('content');
        return null;
    })()
    """)
    if result and result.startswith("http"):
        return result

    # Pattern 2: <a> links with /pdf/ or .pdf (AIAA, T&F, etc.)
    links = DevToolsClient.ws_evaluate(ws, """
    (function() {
        const links = document.querySelectorAll('a[href]');
        for (const a of links) {
            const h = a.href;
            if (h.includes('/pdf/') && h.startsWith('http')) return h;
        }
        for (const a of links) {
            if (a.href.endsWith('.pdf') && a.href.startsWith('http')) return a.href;
        }
        return null;
    })()
    """)
    if links and links.startswith("http"):
        return links

    # Pattern 3: ScienceDirect pdfDownload metadata
    html = DevToolsClient.ws_evaluate(ws, "document.documentElement.outerHTML") or ""
    SD_RE = re.compile(r'"pdfDownload":\{"isPdfFullText":(?:true|false),"urlMetadata":\{"queryParams":\{"md5":"([^"]+)","pid":"([^"]+)"\},"pii":"([^"]+)","pdfExtension":"([^"]+)","path":"([^"]+)"\}\}')
    m = SD_RE.search(html)
    if m:
        md5, pid, pii, pdf_ext, path = m.groups()
        return f"https://www.sciencedirect.com/{path}/{pii}{pdf_ext}?md5={md5}&pid={pid}"

    return ""


def fetch_pdf_from_article(ws, pdf_url):
    """From article page context, fetch(pdf_url) to get PDF bytes."""
    fetch_js = (
        "new Promise(resolve => {"
        f"fetch({json.dumps(pdf_url)}, {{credentials: 'include'}})"
        ".then(r => { if (!r.ok) return resolve('HTTP_ERR:' + r.status); return r.arrayBuffer(); })"
        ".then(buf => {"
        "  if (typeof buf === 'string') return resolve(buf);"
        "  const chunk=0x8000; let binary='';"
        "  const bytes = new Uint8Array(buf);"
        "  for (let i=0; i<bytes.length; i+=chunk) {"
        "    binary += String.fromCharCode.apply(null, bytes.subarray(i, i+chunk));"
        "  }"
        "  resolve(btoa(binary));"
        "})"
        ".catch(err => resolve('ERR:' + err.message));"
        "})"
    )
    result = DevToolsClient.ws_evaluate(ws, fetch_js, await_promise=True, msg_id=30)
    if not result or str(result).startswith("ERR") or str(result).startswith("HTTP_ERR"):
        return None
    data = base64.b64decode(result)
    if data.startswith(b"%PDF-"):
        return data
    return None


def process_row(devtools, row, pdf_dir, page_wait_seconds):
    doi = row.get("doi", "").strip()
    number = row.get("number", "0")
    first_author = row.get("first_author", "").strip()
    year = row.get("year", "").strip()
    expected_title = row.get("title", "").strip()

    target_name = make_target_name(number, first_author or doi, year, expected_title)
    target_path = pdf_dir / target_name
    if target_path.exists() and target_path.stat().st_size > 0:
        return {**row, "status": "downloaded", "pdf_path": str(target_path),
                "source_url": "", "note": "existing_file"}

    article_url = row.get("note", "").strip()
    if not article_url or not article_url.startswith("http"):
        article_url = f"https://doi.org/{doi}" if doi else ""
    if not article_url:
        return {**row, "status": "no_url", "pdf_path": "", "source_url": "", "note": ""}

    page = None
    try:
        page = devtools.open_page(article_url)
        ws = devtools.ws_connect(page["webSocketDebuggerUrl"])
        time.sleep(page_wait_seconds)

        # Verify title
        page_title = DevToolsClient.ws_evaluate(ws, "document.title", msg_id=10) or ""
        for suffix in [" - ScienceDirect", " | SpringerLink", " - IOPscience", " - Emerald Insight",
                       " | AIAA Journal", " | Taylor & Francis", " | MDPI", " - ", " | "]:
            if suffix in page_title:
                page_title = page_title.split(suffix)[0].strip()

        sim = title_similarity(expected_title, page_title)
        if sim < 0.35:
            ws.close()
            return {**row, "status": "title_mismatch", "pdf_path": "", "source_url": article_url,
                    "note": f"exp='{expected_title[:50]}' got='{page_title[:50]}' sim={sim:.2f}"}

        # Find PDF URL
        pdf_url = find_pdf_url(ws)
        if not pdf_url:
            ws.close()
            return {**row, "status": "no_pdf_url", "pdf_path": "", "source_url": article_url,
                    "note": f"title={page_title[:80]}"}

        # Special handling for ScienceDirect (need pdfft -> redirect -> fetch approach)
        if "sciencedirect.com" in article_url.lower() or "sd_" in article_url.lower():
            # Close article page, open pdfft, wait for redirect, fetch
            ws.close()
            devtools.close_page(page["id"])
            page = None

            pdf_page = devtools.open_page(pdf_url)
            pws = devtools.ws_connect(pdf_page["webSocketDebuggerUrl"])
            time.sleep(page_wait_seconds)

            real_url = DevToolsClient.ws_evaluate(pws, "window.location.href", msg_id=20) or pdf_url
            if "pdf.sciencedirectassets.com" in real_url:
                pdf_bytes = fetch_pdf_from_article(pws, real_url)
            else:
                pdf_bytes = fetch_pdf_from_article(pws, real_url)
            pws.close()
            devtools.close_page(pdf_page["id"])
        else:
            # Non-ScienceDirect: fetch from article page directly
            pdf_bytes = fetch_pdf_from_article(ws, pdf_url)
            ws.close()

        if not pdf_bytes:
            return {**row, "status": "fetch_failed", "pdf_path": "", "source_url": pdf_url, "note": ""}

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(pdf_bytes)
        return {**row, "status": "downloaded", "pdf_path": str(target_path),
                "source_url": pdf_url, "note": f"size={len(pdf_bytes)}"}

    finally:
        if page:
            try: devtools.close_page(page["id"])
            except: pass


def main():
    args = parse_args()
    input_csv = Path(args.input_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = out_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    with input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if args.limit and args.limit > 0:
        rows = rows[:args.limit]

    devtools = DevToolsClient(args.debug_port)
    results = []
    total = len(rows)
    for i, row in enumerate(rows, start=1):
        doi = row.get("doi", "")
        number = row.get("number", str(i))
        print(f"[{i}/{total}] [{number}] {doi} | {row.get('title','')[:60]}...")
        result = process_row(devtools, row, pdf_dir, args.page_wait_seconds)
        results.append(result)
        print(f"    -> {result['status']}")
        if i < total and args.inter_item_sleep_seconds > 0:
            time.sleep(args.inter_item_sleep_seconds)

    fieldnames = ["number","first_author","title","doi","year","journal","status","pdf_path","source_url","note","formatted"]
    with (out_dir / "results.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    missing = [r for r in results if r.get("status") != "downloaded"]
    with (out_dir / "missing.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in missing:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    n_ok = sum(1 for r in results if r.get("status") == "downloaded")
    print(f"\n{'='*60}")
    print(f"  COMPLETE: {n_ok}/{total} succeeded, {total-n_ok} failed")
    if missing:
        print(f"  Failed:")
        for r in missing:
            print(f"    [{r.get('number','?')}] {r.get('doi','')[:40]} - {r.get('status')} - {r.get('note','')[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
