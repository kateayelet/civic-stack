#!/usr/bin/env python3
"""Fill 94920 corpus headings with official enacted text.

Publishers (never invents law):
  - CivicPlus Municode API — Town of Tiburon, Marin County
  - belvedere.municipal.codes (via r.jina.ai when Cloudflare blocks)
  - California Legislative Counsel (leginfo.legislature.ca.gov)
  - Office of the Law Revision Counsel (uscode.house.gov) / govinfo
  - eCFR
  - National Archives
  - Cornell LII (U.S. Reports) for case holdings
  - District publishers (codepublishing, ecode360, agency sites) via Jina fallback

Usage:
  python3 scripts/ingest_corpus.py
  python3 scripts/ingest_corpus.py --only municode,belvedere,leginfo
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = Path("/tmp/civic-ingest-cache")
CACHE.mkdir(parents=True, exist_ok=True)

UA = (
    "94920-corpus-ingest/1.0 (+https://github.com/kateayelet/civic-stack; "
    "homeowner enacted-text corpus; official publishers)"
)
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

MUNICODE_ORIGIN = {
    "User-Agent": BROWSER_UA,
    "Accept": "application/json",
    "Origin": "https://library.municode.com",
    "Referer": "https://library.municode.com/",
}

TIBURON = {"client": 9796, "product": 16657, "job": 486977, "slug": "tiburon"}
MARIN = {"client": 6748, "product": 16476, "job": 493511, "slug": "marin_county", "product_name": "municipal_code"}

CODE_NAMES = {
    "BPC": "Business and Professions Code",
    "CCP": "Code of Civil Procedure",
    "CIV": "Civil Code",
    "COM": "Commercial Code",
    "CONS": "California Constitution",
    "CORP": "Corporations Code",
    "EDC": "Education Code",
    "ELEC": "Elections Code",
    "EVID": "Evidence Code",
    "FAC": "Food and Agricultural Code",
    "FAM": "Family Code",
    "FGC": "Fish and Game Code",
    "FIN": "Financial Code",
    "GOV": "Government Code",
    "HNC": "Harbors and Navigation Code",
    "HSC": "Health and Safety Code",
    "INS": "Insurance Code",
    "LAB": "Labor Code",
    "MVC": "Military and Veterans Code",
    "PCC": "Public Contract Code",
    "PEN": "Penal Code",
    "PRC": "Public Resources Code",
    "PROB": "Probate Code",
    "PUC": "Public Utilities Code",
    "RTC": "Revenue and Taxation Code",
    "SHC": "Streets and Highways Code",
    "UIC": "Unemployment Insurance Code",
    "VEH": "Vehicle Code",
    "WAT": "Water Code",
    "WIC": "Welfare and Institutions Code",
}

# Article ids used on leginfo CONS displayText
CONST_ARTICLES = {
    "i": "I",
    "ii": "II",
    "iii": "III",
    "iv": "IV",
    "v": "V",
    "vi": "VI",
    "vii": "VII",
    "ix": "IX",
    "x": "X",
    "xa": "XA",
    "xb": "XB",
    "xi": "XI",
    "xii": "XII",
    "xiiib": "XIIIB",
    "xiii": "XIII",
    "xiiia": "XIIIA",
    "xiiic": "XIIIC",
    "xiiid": "XIIID",
    "xiv": "XIV",
    "xv": "XV",
    "xvi": "XVI",
    "xviii": "XVIII",
    "xx": "XX",
    "xxi": "XXI",
    "xxxiv": "XXXIV",
    "xxxv": "XXXV",
}

PLACEHOLDER_RE = re.compile(r"^\$\d+$")


class HTMLText(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP:
            self.skip += 1
        if tag in {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "section"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        t = "".join(self.parts)
        t = html.unescape(t)
        t = t.replace("\xa0", " ").replace("\u2002", " ").replace("\u2003", " ")
        t = re.sub(r"[ \t]+\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()


def html_to_text(raw: str) -> str:
    p = HTMLText()
    try:
        p.feed(raw)
        p.close()
    except Exception:
        raw = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
        raw = re.sub(r"(?is)<style.*?>.*?</style>", " ", raw)
        raw = re.sub(r"<[^>]+>", " ", raw)
        return re.sub(r"\s+", " ", html.unescape(raw)).strip()
    return p.text()


def cache_path(url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()
    return CACHE / h


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 45,
    retries: int = 3,
    sleep: float = 0.15,
    as_json: bool = False,
) -> Any:
    path = cache_path(url + ("#json" if as_json else ""))
    meta = path.with_suffix(".hdr")
    if path.exists() and path.stat().st_size > 0:
        raw = path.read_bytes()
        if as_json:
            return json.loads(raw.decode("utf-8"))
        return raw.decode("utf-8", "replace")

    hdr = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9,*/*;q=0.8"}
    if headers:
        hdr.update(headers)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            path.write_bytes(raw)
            meta.write_text(f"{resp.status}\n{url}\n", encoding="utf-8")
            time.sleep(sleep)
            if as_json:
                return json.loads(raw.decode("utf-8"))
            return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last_err = e
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            if e.code in {403, 404, 406, 410}:
                break
            time.sleep(1.2 * (attempt + 1))
        except Exception as e:
            last_err = e
            time.sleep(1.2 * (attempt + 1))
    if last_err:
        raise last_err
    raise RuntimeError(f"GET failed: {url}")


def http_get_bytes(url: str, timeout: int = 90, sleep: float = 0.2) -> bytes:
    path = cache_path(url + "#bin")
    if path.exists() and path.stat().st_size > 200:
        return path.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").lower()
    if len(raw) < 200 or ("html" in ctype and not raw.startswith(b"%PDF")):
        raise RuntimeError(f"not a PDF: {url} ({ctype}, {len(raw)} bytes)")
    path.write_bytes(raw)
    time.sleep(sleep)
    return raw


def pdf_text(url: str, max_chars: int = 60000) -> str:
    raw = http_get_bytes(url)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(raw)
        tmp.flush()
        out = subprocess.check_output(
            ["pdftotext", "-layout", "-nopgbrk", tmp.name, "-"],
            timeout=60,
        )
    text = clean_law_text(out.decode("utf-8", "replace"))
    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n", 1)[0]
    return text


def jina(url: str) -> str:
    """Fetch official page text through Jina Reader when the publisher blocks bots."""
    if url.startswith("https://"):
        wrapped = "https://r.jina.ai/" + url
    else:
        wrapped = "https://r.jina.ai/http://" + url.split("://", 1)[-1]
    text = http_get(
        wrapped,
        headers={
            "User-Agent": UA,
            "Accept": "text/markdown",
        },
        sleep=0.85,
        timeout=70,
    )
    if "Markdown Content:" in text:
        text = text.split("Markdown Content:", 1)[1]
    text = re.sub(r"^Title:.*\n", "", text)
    text = re.sub(r"^URL Source:.*\n", "", text)
    text = re.sub(r"^Warning:.*\n", "", text)
    return text.strip()


def capture_id(raw: str, target_id: str) -> str:
    """Return inner HTML of the first element whose id matches."""
    m = re.search(rf'id="{re.escape(target_id)}"', raw)
    if not m:
        return ""
    # find the start tag that contains this id
    start_tag = raw.rfind("<", 0, m.start())
    if start_tag < 0:
        return ""
    tag_m = re.match(r"<([a-zA-Z0-9]+)", raw[start_tag:])
    if not tag_m:
        return ""
    tag = tag_m.group(1)
    # walk from end of start tag
    gt = raw.find(">", start_tag)
    if gt < 0:
        return ""
    i = gt + 1
    depth = 1
    lower = raw.lower()
    open_re = re.compile(rf"<{tag.lower()}(\s|>|/)")
    close_re = re.compile(rf"</{tag.lower()}>")
    while i < len(raw) and depth:
        nxt_open = lower.find(f"<{tag.lower()}", i)
        nxt_close = lower.find(f"</{tag.lower()}>", i)
        if nxt_close < 0:
            break
        if nxt_open >= 0 and nxt_open < nxt_close:
            # could be same tag nested
            depth += 1
            i = nxt_open + len(tag) + 1
        else:
            depth -= 1
            if depth == 0:
                return raw[gt + 1 : nxt_close]
            i = nxt_close + len(tag) + 3
    return raw[gt + 1 :]


def clean_law_text(text: str, drop: list[str] | None = None) -> str:
    junk = drop or [
        "Skip to main content",
        "Please enable cookies",
        "Loading…",
        "Loading...",
        "Get Notified",
        "This section is included in your selections.",
        "This chapter is included in your selections.",
        "This Title is included in your selections.",
    ]
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            lines.append("")
            continue
        s = re.sub(r"^#+\s+", "", s)
        s = re.sub(r"^[\*\-]\s+", "", s)
        if any(s.startswith(j) or s == j for j in junk):
            continue
        if s.startswith("[") and "](" in s and s.endswith(")"):
            # markdown nav link; keep section titles that look like law headings
            label = re.sub(r"^\[(.*?)\]\(.*\)$", r"\1", s)
            if re.match(r"^(\d|Ch\.|Title|Article|Sec\.|Section|CHAPTER|TITLE)", label, re.I):
                lines.append(label)
            continue
        lines.append(s)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


# ---------- Municode ----------


def municode_toc(cfg: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    q = urllib.parse.urlencode(
        {"jobId": cfg["job"], "productId": cfg["product"], "nodeId": node_id}
    )
    url = f"https://api.municode.com/codesToc/children?{q}"
    data = http_get(url, headers=MUNICODE_ORIGIN, as_json=True, sleep=0.12)
    return data or []


def walk_toc(cfg: dict[str, Any], root: str) -> list[dict[str, Any]]:
    cache = CACHE / f"toc-{cfg['product']}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    out: list[dict[str, Any]] = []

    def rec(nid: str, depth: int) -> None:
        kids = municode_toc(cfg, nid)
        for k in kids:
            item = {
                "id": k.get("Id") or "",
                "heading": k.get("Heading") or "",
                "parent": k.get("ParentId") or nid,
                "depth": k.get("NodeDepth") or depth,
                "has_children": bool(k.get("HasChildren")),
            }
            out.append(item)
            if item["has_children"]:
                rec(item["id"], depth + 1)

    rec(root, 0)
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


def municode_content(cfg: dict[str, Any], node_id: str, leaf: bool = False) -> tuple[str, str]:
    q = urllib.parse.urlencode(
        {"jobId": cfg["job"], "productId": cfg["product"], "nodeId": node_id}
    )
    url = f"https://api.municode.com/CodesContent?{q}"
    data = http_get(url, headers=MUNICODE_ORIGIN, as_json=True, sleep=0.12)
    docs = (data or {}).get("Docs") or []
    if leaf:
        exact = [d for d in docs if d.get("Id") == node_id]
        docs = exact or docs[:1]
    chunks: list[str] = []
    title = ""
    for doc in docs:
        title = title or (doc.get("Title") or "")
        th = doc.get("TitleHtml") or ""
        content = doc.get("Content") or ""
        piece = html_to_text(th + "\n" + content)
        if not piece.strip():
            piece = (doc.get("Title") or "").strip()
        if piece:
            chunks.append(piece)
    text = clean_law_text("\n\n".join(chunks))
    return title, text


def heading_key(heading: str) -> str:
    h = heading.upper()
    h = h.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", h).strip()


def match_municode(suffix: str, toc: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Map a corpus id suffix (e.g. 16-52.020, I, 22I) onto a Municode TOC node."""
    if not suffix:
        return None
    s = suffix.strip()
    su = s.upper()
    if re.fullmatch(r"[IVX]+", su):
        for n in toc:
            hk = heading_key(n["heading"])
            if re.match(rf"TITLE {su}\b", hk):
                return n
    if su in {"BE", "BEGINNING", "TIMUCO"}:
        for n in toc:
            hk = heading_key(n["heading"])
            if n["id"] == "TIMUCO" or hk.startswith("TIBURON MUNICIPAL CODE"):
                return n
    numbered = []
    for n in toc:
        h = n["heading"].strip()
        hu = heading_key(h)
        starts = (
            hu.startswith(su + " ")
            or hu.startswith(su + " -")
            or hu.startswith(su + ".")
            or hu == su
            or re.match(rf"^(CHAPTER|CH\.?|TITLE|ARTICLE|SEC\.?|SECTION)\s+{re.escape(su)}\b", hu)
        )
        if not starts:
            continue
        exact = hu.startswith(su + " -") or hu.startswith(su + " ") or hu == su
        score = 0
        if exact:
            score -= 5
        if n.get("has_children") is False and ("." in s or "-" in s):
            score -= 2
        if n.get("has_children") and "." not in s:
            score -= 1
        numbered.append((score, len(h), n))
    if numbered:
        numbered.sort(key=lambda x: (x[0], x[1]))
        return numbered[0][2]
    return None


def deep_municode_url(slug: str, node_id: str, product_name: str = "code_of_ordinances") -> str:
    return (
        f"https://library.municode.com/ca/{slug}/codes/{product_name}?nodeId={urllib.parse.quote(node_id)}"
    )


# ---------- Belvedere (municipal.codes) ----------


def belvedere_url(code: str) -> str:
    if not code or code in {"code"}:
        return "https://belvedere.municipal.codes/Code"
    return f"https://belvedere.municipal.codes/Code/{code}"


def extract_belvedere_body(md: str, code: str) -> str:
    """Keep the official heading + body; drop municipal.codes chrome and Loading…."""
    md = clean_law_text(md)
    if "just a moment" in md.lower() and "ord." not in md.lower():
        return ""
    start = None
    needles: list[str] = []
    if code:
        needles.extend(
            [
                rf"(?:^|\n)#{{1,6}}\s*{re.escape(code)}\b",
                rf"(?:^|\n)(?:Title|Chapter|Ch\.)\s+{re.escape(code)}\b",
                rf"(?:^|\n){re.escape(code)}\s",
            ]
        )
    needles.extend(
        [
            r"(?:^|\n)#{1,6}\s*\d",
            r"This Title is enacted",
            r"This title is included",
            r"This chapter is included",
            r"This Title shall",
            r"\nSections:",
            r"\nChapters:",
        ]
    )
    for pat in needles:
        m = re.search(pat, md, re.I)
        if m:
            start = m.start()
            break
    if start is not None:
        md = md[start:].lstrip("# ").strip()
    for stop in ("\n## Contents", "\nWhat’s Nearby", "\nWhat's Nearby", "\nYour Selections", "\nToggle site"):
        i = md.find(stop)
        if i > 80:
            md = md[:i]
    md = re.sub(r"(?i)^loading…\s*", "", md).strip()
    return md


def fetch_belvedere(code: str) -> tuple[str, str]:
    url = belvedere_url(code)
    # HTTPS is Cloudflare-blocked; HTTP via Jina renders the ordinance body.
    md = ""
    for candidate in (url.replace("https://", "http://"), url):
        try:
            md = jina(candidate)
        except Exception:
            md = ""
        body = extract_belvedere_body(md, code)
        if body and len(body) >= 40:
            # municipal.codes serves Title 19's chapter list for repealed/missing numbers.
            if "." in (code or "") and "19.04 General Provisions" in body:
                if not re.search(rf"(?:Chapter|Ch\.)\s+{re.escape(code)}\b|{re.escape(code)}\s", body[:500]):
                    continue
            return url, body
    return url, ""


# ---------- California LegInfo ----------


def leginfo_section(law: str, section: str) -> tuple[str, str]:
    section = section.rstrip(".")
    url = (
        "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?"
        + urllib.parse.urlencode({"lawCode": law, "sectionNum": section})
    )
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.2)
    inner = capture_id(raw, "codeLawSectionNoHead") or capture_id(raw, "single_law_section")
    if not inner:
        inner = capture_id(raw, "codes_displaysecblock")
    text = html_to_text(inner or "")
    text = clean_law_text(text)
    # Leginfo pages include chrome; keep from the section number onward if present
    m = re.search(rf"\b{re.escape(section)}\b", text)
    if m and m.start() > 80:
        # don't crop if the number appears only in nav; require nearby legal text
        window = text[m.start() : m.start() + 40]
        if re.search(r"[\.:\(]", window) or window.strip().startswith(section):
            text = text[m.start() :]
    return url, text


def leginfo_article(article: str) -> tuple[str, str]:
    url = (
        "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?"
        + urllib.parse.urlencode({"lawCode": "CONS", "article": article})
    )
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.2)
    # The article body sits after the ARTICLE heading
    text = html_to_text(raw)
    m = re.search(rf"ARTICLE\s+{re.escape(article)}\b", text, re.I)
    if m:
        text = text[m.start() :]
    # Trim footer chrome
    for stop in ("Bill Information", "California Law", "Publications", "Other Resources"):
        i = text.rfind(stop)
        if i > 400:
            text = text[:i]
    return url, clean_law_text(text)


def extract_const_section(article_text: str, sec: str) -> str:
    """Pull one SEC. N from an already-fetched article."""
    # SEC. 1 / SECTION 1. / Sec. 1.
    pat = re.compile(
        rf"(?:^|\n)\s*(SECTION|SEC\.)\s+{re.escape(sec)}\b[\s\S]*?(?=(?:\n\s*(?:SECTION|SEC\.)\s+\d+)|\Z)",
        re.I,
    )
    m = pat.search(article_text)
    return m.group(0).strip() if m else ""


def leginfo_code_heading(law: str) -> tuple[str, str]:
    url = (
        "https://leginfo.legislature.ca.gov/faces/codesTOCSelected.xhtml?"
        + urllib.parse.urlencode({"tocCode": law})
    )
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.2)
    text = html_to_text(raw)
    name = CODE_NAMES.get(law, law)
    # Official page title plus code name
    m = re.search(rf"{re.escape(name)}[\s\S]{{0,400}}", text, re.I)
    body = m.group(0) if m else name
    heading = f"CALIFORNIA CODES\n{name.upper()} ({law})"
    # Try section 1 as a short official opening if it exists
    try:
        _, sec1 = leginfo_section(law, "1")
        if sec1 and len(sec1) > 40 and "we're sorry" not in sec1.lower():
            return url, heading + "\n\n" + sec1
    except Exception:
        pass
    return url, heading + "\n\n" + clean_law_text(body)[:2500]


# ---------- US Code / eCFR / founding / cases ----------


def uscode_section(title: str, section: str) -> tuple[str, str]:
    url = (
        "https://uscode.house.gov/view.xhtml?"
        + urllib.parse.urlencode(
            {
                "req": f"granuleid:USC-prelim-title{title}-section{section}",
                "num": "0",
                "edition": "prelim",
            }
        )
    )
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.2)
    inner = capture_id(raw, "content") or capture_id(raw, "uscitem")
    text = html_to_text(inner or raw)
    m = re.search(rf"§+\s*{re.escape(section)}\b|Section {re.escape(section)}\b", text)
    if m:
        text = text[m.start() :]
    for stop in ("-SOURCE-", "Current through", "Office of the Law Revision Counsel"):
        i = text.find(stop)
        if i > 200:
            text = text[:i]
    return url, clean_law_text(text)


def uscode_title(title: str) -> tuple[str, str]:
    url = f"https://uscode.house.gov/browse/prelim@title{title}&edition=prelim"
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.2)
    text = html_to_text(raw)
    m = re.search(rf"Title {re.escape(title)}\b[\s\S]{{0,1800}}", text, re.I)
    body = m.group(0) if m else text[:1800]
    return url, clean_law_text(body)


def ecfr_section(title: str, section: str) -> tuple[str, str]:
    url = f"https://www.ecfr.gov/current/title-{title}/section-{section}"
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.2)
    text = html_to_text(raw)
    m = re.search(rf"§\s*{re.escape(section)}\b", text)
    if m:
        text = text[m.start() :]
    for stop in ("Need assistance?", "Enhanced Content", "eCFR Content"):
        i = text.find(stop)
        if i > 200:
            # keep going; eCFR chrome is messy
            pass
    return url, clean_law_text(text)[:20000]


def ecfr_title(title: str) -> tuple[str, str]:
    url = f"https://www.ecfr.gov/current/title-{title}"
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.2)
    text = html_to_text(raw)
    m = re.search(rf"Title {re.escape(title)}\b[\s\S]{{0,2000}}", text, re.I)
    return url, clean_law_text(m.group(0) if m else text[:2000])


def archives_main(url: str, start_markers: list[str]) -> tuple[str, str]:
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.2)
    text = html_to_text(raw)
    idx = -1
    for mk in start_markers:
        i = text.find(mk)
        if i >= 0:
            idx = i
            break
    if idx >= 0:
        text = text[idx:]
    for stop in ("More Milestone Documents", "Footnotes", "Share this page", "Page URL"):
        i = text.find(stop)
        if i > 400:
            text = text[:i]
            break
    return url, clean_law_text(text)


def cornell_case(volume: str, page: str) -> tuple[str, str]:
    url = f"https://www.law.cornell.edu/supremecourt/text/{volume}/{page}"
    try:
        raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.25)
        text = html_to_text(raw)
        m = re.search(rf"{re.escape(volume)}\s+U\.S\.\s+{re.escape(page)}", text)
        if m:
            text = text[m.start() :]
        else:
            m = re.search(r"\bSyllabus\b|\bOpinion\b", text)
            if m:
                text = text[m.start() :]
        cleaned = clean_law_text(text)
        if cleaned and len(cleaned) > 80 and "not found" not in cleaned.lower()[:80]:
            return url, cleaned
    except Exception:
        pass
    # CourtListener reproduces the U.S. Reports; search then read the opinion page.
    q = urllib.parse.quote(f'"{volume} U.S. {page}"')
    search = (
        f"https://www.courtlistener.com/api/rest/v4/search/?q={q}&type=o&court=scotus"
    )
    try:
        data = http_get(search, headers={"User-Agent": BROWSER_UA, "Accept": "application/json"}, as_json=True, sleep=0.2)
        results = (data or {}).get("results") or []
        hit = None
        for rec in results:
            cites = rec.get("citation") or []
            if cite_in_list(f"{volume} U.S. {page}", cites if isinstance(cites, list) else [str(cites)]):
                hit = rec
                break
        if hit and hit.get("absolute_url"):
            cl_url = "https://www.courtlistener.com" + hit["absolute_url"]
            text = clean_law_text(jina(cl_url))
            return cl_url, text
    except Exception:
        pass
    return url, ""


def parse_us_cite(citation: str) -> tuple[str, str] | None:
    m = re.search(r"(\d+)\s+U\.S\.\s+(\d+)", citation)
    if m:
        return m.group(1), m.group(2)
    return None


def parse_cal_cite(citation: str) -> tuple[str, str] | None:
    m = re.search(r"(\d+)\s+Cal\.(?:4th|3d|2d|App\.\s*4th)?\s+(\d+)", citation)
    if m:
        return m.group(1), m.group(2)
    return None


def loc_us_reports_pdf(volume: str, page: str) -> str:
    return (
        f"https://tile.loc.gov/storage-services/service/ll/usrep/usrep{volume}/"
        f"usrep{volume}{page}/usrep{volume}{page}.pdf"
    )


def cite_in_list(want: str, citations: list[str]) -> bool:
    norm = re.sub(r"\s+", " ", want).strip()
    for c in citations:
        got = re.sub(r"\s+", " ", c).strip()
        if got == norm:
            return True
        if re.sub(r"\.\s*", ".", got) == re.sub(r"\.\s*", ".", norm):
            return True
    return False


def courtlistener_exact(cite: str, name_hint: str = "") -> dict[str, Any] | None:
    """Return a CL search hit only when the reporter cite matches exactly."""
    q = urllib.parse.quote(f'"{cite}"')
    search = f"https://www.courtlistener.com/api/rest/v4/search/?q={q}&type=o"
    data = http_get(
        search,
        headers={"User-Agent": BROWSER_UA, "Accept": "application/json"},
        as_json=True,
        sleep=0.25,
    )
    hint = name_hint.lower()
    for rec in (data or {}).get("results") or []:
        if not cite_in_list(cite, rec.get("citation") or []):
            continue
        cname = (rec.get("caseName") or "").lower()
        if hint and hint not in cname:
            continue
        return rec
    return None


def scocal_opinion(url: str) -> str:
    raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.25)
    text = html_to_text(raw)
    m = re.search(r"\d+\s+Cal\.", text)
    if m and m.start() < 4000:
        text = text[m.start() :]
    for stop in ("Stanford Law School", "Related cases", "Comments are closed"):
        i = text.find(stop)
        if i > 400:
            text = text[:i]
            break
    return clean_law_text(text)


# Official PDFs keyed by graph id. Never a search-result fallback.
CASE_OFFICIAL_PDFS = {
    "case:koontz": [
        (
            "https://tile.loc.gov/storage-services/service/ll/usrep/usrep570/usrep570595/usrep570595.pdf",
            "Library of Congress, 570 U.S. 595",
        ),
        (
            "https://storage.courtlistener.com/pdf/2013/06/25/koontz_v._st._johns_river_water_management_dist..pdf",
            "U.S. Reports 570 U.S. 595 (CourtListener storage of official PDF)",
        ),
    ],
    "case:kelo": [
        (
            "https://tile.loc.gov/storage-services/service/ll/usrep/usrep545/usrep545469/usrep545469.pdf",
            "Library of Congress, 545 U.S. 469",
        ),
    ],
    "case:olech": [
        (
            "https://tile.loc.gov/storage-services/service/ll/usrep/usrep528/usrep528562/usrep528562.pdf",
            "Library of Congress, 528 U.S. 562",
        ),
    ],
    "case:cedar-point": [
        (
            "https://www.supremecourt.gov/opinions/20pdf/20-107_ihdj.pdf",
            "U.S. Supreme Court slip opinion, Cedar Point Nursery v. Hassid, 594 U.S. 139",
        ),
    ],
    "case:knick": [
        (
            "https://www.supremecourt.gov/opinions/18pdf/17-647_m648.pdf",
            "U.S. Supreme Court slip opinion, Knick v. Township of Scott, 588 U.S. 180",
        ),
    ],
    "case:pakdel": [
        (
            "https://www.supremecourt.gov/opinions/20pdf/20-1212_3204.pdf",
            "U.S. Supreme Court slip opinion, Pakdel v. City and County of San Francisco, 594 U.S. 474",
        ),
    ],
    "case:tyler": [
        (
            "https://www.supremecourt.gov/opinions/22pdf/22-166_8n59.pdf",
            "U.S. Supreme Court slip opinion, Tyler v. Hennepin County, 598 U.S. 631",
        ),
    ],
    "case:horne": [
        (
            "https://storage.courtlistener.com/pdf/2015/06/22/horne_v._department_of_agriculture.pdf",
            "U.S. Supreme Court slip opinion, Horne v. Department of Agriculture (CourtListener storage of official PDF)",
        ),
    ],
}

CASE_SCOCAL = {
    "case:nollan-cousin-ehrlich": "https://scocal.stanford.edu/opinion/ehrlich-v-city-culver-city-31606/",
    "case:gion": "https://scocal.stanford.edu/opinion/gion-v-city-santa-cruz-30092/",
}

# Recodified / clustered cites: fetch the official successor section when the
# legacy section page has no body on LegInfo.
SUCCESSORS = {
    "ca:code:gov:6250": ("GOV", "7920.000"),
    "ca:code:civ:1350": ("CIV", "4000"),
    "ca:code:civ:1954.20": ("CIV", "1954.50"),
    "ca:code:gov:65852.22": ("GOV", "66333"),
}

DISTRICT_URLS = {
    "dist:tamuhsd": "https://www.tamdistrict.org/",
    "dist:mccd": "https://www.marin.edu/",
    "dist:calfire": "https://osfm.fire.ca.gov/what-we-do/community-wildfire-preparedness-and-mitigation/fire-hazard-severity-zones",
    "dist:usace": "https://www.spn.usace.army.mil/",
    "dist:fema": "https://www.fema.gov/flood-insurance/work-with-nfip/national-flood-insurance-program",
    "dist:ggbht": "https://www.goldengate.org/",
    "dist:tam": "https://www.tam.ca.gov/",
    "dist:bt-rec": "https://www.beltiblibrary.org/",
    "dist:mmwd": "https://www.marinwater.org/",
    "dist:mmwd:title13": "https://ecode360.com/44094959",
    "dist:mmwd:13.02.020": "https://ecode360.com/44094959",
    "dist:sd5:code": "https://www.codepublishing.com/CA/MarinCSD5/html/MarinCSD5NT.html",
    "dist:csa29": "https://publicworks.marincounty.gov/paradise-cay-csa29/",
    "dist:rwqcb2": "https://www.waterboards.ca.gov/sanfranciscobay/",
}


def fetch_url_text(url: str) -> str:
    try:
        raw = http_get(url, headers={"User-Agent": BROWSER_UA}, sleep=0.3)
        text = clean_law_text(html_to_text(raw))
        if len(text) >= 80 and "you have been blocked" not in text.lower() and "just a moment" not in text.lower():
            return text
    except Exception:
        pass
    for candidate in (url.replace("https://", "http://"), url):
        try:
            text = clean_law_text(jina(candidate))
            if len(text) >= 80 and "just a moment" not in text.lower():
                return text
        except Exception:
            continue
    return ""


def node_bucket(nid: str) -> str:
    if nid.startswith("ca:tiburon:code") or nid.startswith("ca:marin:code"):
        return "municode"
    if nid.startswith("ca:belvedere:code"):
        return "belvedere"
    if nid == "ca:const-1849":
        return "founding"
    if nid.startswith("us:usc:"):
        return "uscode"
    if nid.startswith("us:cfr:"):
        return "ecfr"
    if nid.startswith("us:declaration") or nid in {
        "us:const",
        "us:articles",
        "us:northwest-ordinance",
        "us:const-conan",
        "us:land-act-1851",
    }:
        return "founding"
    if nid.startswith("case:"):
        return "cases"
    if nid.startswith("ca:ccr:"):
        return "ccr"
    if nid.startswith("ca:code:") or nid.startswith("ca:const"):
        return "leginfo"
    if nid.startswith("dist:"):
        return "district"
    return "other"


def relevant(nid: str, only: set[str] | None) -> bool:
    if not only:
        return True
    b = node_bucket(nid)
    if b in only:
        return True
    if "city" in only and b in {"municode", "belvedere"}:
        return True
    if "county" in only and b == "municode":
        return True
    if "state" in only and b in {"leginfo", "ccr"}:
        return True
    if "federal" in only and b in {"uscode", "ecfr", "founding"}:
        return True
    return False


def is_placeholder(node: dict[str, Any]) -> bool:
    t = (node.get("text") or "").strip()
    return not t or bool(PLACEHOLDER_RE.match(t)) or t in {"The People\nThe People"}


def should_fill(node: dict[str, Any], overwrite: bool = False) -> bool:
    if node.get("type") in {"Issue", "Actor", "Jurisdiction", "ParcelClass"}:
        return False
    kind = node.get("text_kind") or ""
    if kind == "catalog":
        return True
    if kind == "enacted" and is_placeholder(node):
        return True
    if overwrite and kind in {"enacted", "holding", "catalog"}:
        src = node.get("text_source") or ""
        if src.startswith("Municode") or kind == "catalog" or is_placeholder(node):
            return True
    return False


def parse_const_id(nid: str) -> tuple[str, str | None] | None:
    """Return (article, section|None) for ca:const:* ids."""
    rest = nid.split(":", 2)[-1]  # after ca:const
    if rest in {"const", "code:cons"}:
        return None
    if rest.startswith("art-"):
        art = rest[4:]
        return CONST_ARTICLES.get(art, art.upper()), None
    if rest in CONST_ARTICLES and "-" not in rest:
        return CONST_ARTICLES[rest], None
    # i-3, xi-11, xiii-1, xiii-a (article XIII A is a whole article)
    if rest in {"xiii-a", "xiii-c", "xiii-d"}:
        return {"xiii-a": "XIII A", "xiii-c": "XIII C", "xiii-d": "XIII D"}[rest], None
    m = re.fullmatch(r"([ivx]+)-(\d+[a-z]?)", rest)
    if m:
        art = CONST_ARTICLES.get(m.group(1), m.group(1).upper())
        return art, m.group(2)
    if rest == "xxxiv":
        return "XXXIV", None
    if rest == "xxxv":
        return "XXXV", None
    if rest == "iv":
        return "IV", None
    return None


def fill_node(
    node: dict[str, Any],
    toc_t: list[dict[str, Any]],
    toc_m: list[dict[str, Any]],
    only: set[str] | None,
) -> dict[str, Any] | None:
    """Return a result dict {text,url,source,kind,coverage} or None."""
    nid = node["id"]
    layer = node.get("layer") or ""

    def allow(*names: str) -> bool:
        return not only or any(n in only for n in names)

    # Municode Tiburon
    if nid.startswith("ca:tiburon:code") and allow("municode", "city"):
        suffix = nid[len("ca:tiburon:code") :].lstrip(":")
        if not suffix:
            title, text = municode_content(TIBURON, "ADCO")
            banner = (
                "CODE OF ORDINANCES\nTIBURON, CALIFORNIA\n"
                "Codified through Ordinance No. 614 N.S., passed November 5, 2025. (Supp. No. 39)"
            )
            url = deep_municode_url("tiburon", "ADCO")
            return result(banner + "\n\n" + text, url, "Municode / Town of Tiburon Code of Ordinances", "enacted", "excerpt")
        hit = match_municode(suffix, toc_t)
        if not hit:
            return None
        leaf = not hit.get("has_children")
        title, text = municode_content(TIBURON, hit["id"], leaf=leaf)
        if not text:
            return None
        url = deep_municode_url("tiburon", hit["id"])
        cov = "full" if leaf or len(text) < 80000 else "excerpt"
        if len(text) > 120000:
            text = text[:120000].rsplit("\n", 1)[0]
            cov = "excerpt"
        return result(text, url, f"Municode / Tiburon ({hit['heading']})", "enacted", cov)

    if nid.startswith("ca:marin:code") and allow("municode", "county"):
        suffix = nid[len("ca:marin:code") :].lstrip(":")
        if not suffix:
            # banner + title 1 if present
            hit = next((n for n in toc_m if n["id"] and "TIT" in n["id"][:6]), toc_m[0] if toc_m else None)
            if not hit:
                return None
            title, text = municode_content(MARIN, hit["id"])
            banner = (
                "MARIN COUNTY CALIFORNIA MUNICIPAL CODE\n"
                "Codified through Ordinance No. 26-002, passed February 24, 2026."
            )
            url = deep_municode_url("marin_county", hit["id"], "municipal_code")
            return result(banner + "\n\n" + text[:8000], url, "Municode / Marin County Code", "enacted", "excerpt")
        hit = match_municode(suffix, toc_m)
        if not hit:
            return None
        leaf = not hit.get("has_children")
        title, text = municode_content(MARIN, hit["id"], leaf=leaf)
        if not text:
            return None
        url = deep_municode_url("marin_county", hit["id"], "municipal_code")
        cov = "full" if leaf or len(text) < 80000 else "excerpt"
        if len(text) > 120000:
            text = text[:120000].rsplit("\n", 1)[0]
            cov = "excerpt"
        return result(text, url, f"Municode / Marin County ({hit['heading']})", "enacted", cov)

    if nid.startswith("ca:belvedere:code") and allow("belvedere", "city"):
        suffix = nid[len("ca:belvedere:code") :].lstrip(":")
        url, text = fetch_belvedere(suffix or "")
        if not text or len(text) < 40:
            return None
        cov = "full" if suffix.count(".") >= 2 or re.match(r"^\d+\.\d+\.\d+", suffix or "") else "excerpt"
        if suffix.count(".") == 2:
            cov = "full"
        elif re.match(r"^\d+\.\d+\.\d+", suffix or ""):
            cov = "full"
        elif re.match(r"^\d+$", suffix or ""):
            cov = "excerpt"
        return result(text, url, "City of Belvedere Municipal Code (municipal.codes)", "enacted", cov)

    # California constitution
    if (nid == "ca:const" or nid.startswith("ca:const:")) and allow("leginfo", "state"):
        if nid in {"ca:const", "ca:code:cons"}:
            url, text = leginfo_article("I")
            # store preamble-ish article I heading plus note it's the constitution
            heading = "CONSTITUTION OF THE STATE OF CALIFORNIA"
            return result(heading + "\n\n" + text[:4000], url, "California Legislative Counsel, Cal. Const.", "enacted", "excerpt")
        parsed = parse_const_id(nid)
        if not parsed:
            return None
        art, sec = parsed
        url, article_text = leginfo_article(art)
        if not article_text:
            return None
        if sec:
            piece = extract_const_section(article_text, sec)
            if not piece:
                return None
            return result(piece, url, f"California Legislative Counsel, Cal. Const. art. {art} § {sec}", "enacted", "full")
        return result(article_text, url, f"California Legislative Counsel, Cal. Const. art. {art}", "enacted", "full")

    if nid.startswith("ca:code:") and allow("leginfo", "state"):
        parts = nid.split(":")  # ca, code, GOV, 65000?
        if len(parts) < 3:
            return None
        law = parts[2].upper()
        if law == "CONS":
            url, text = leginfo_article("I")
            return result("CALIFORNIA CONSTITUTION\n\n" + text[:3000], url, "California Legislative Counsel", "enacted", "excerpt")
        if len(parts) == 3:
            url, text = leginfo_code_heading(law)
            return result(text, url, f"California Legislative Counsel, {CODE_NAMES.get(law, law)}", "enacted", "excerpt")
        section = parts[3]
        url, text = leginfo_section(law, section)
        src_label = f"{law} § {section}"
        if (not text or len(text) < 30) and nid in SUCCESSORS:
            slaw, ssec = SUCCESSORS[nid]
            url, text = leginfo_section(slaw, ssec)
            src_label = f"{slaw} § {ssec} (successor to {law} § {section})"
        if not text or len(text) < 30:
            return None
        cov = "full" if len(text) < 20000 else "excerpt"
        if len(text) > 40000:
            text = text[:40000]
            cov = "excerpt"
        return result(text, url, f"California Legislative Counsel, {src_label}", "enacted", cov)

    if nid.startswith("us:usc:") and allow("uscode", "federal"):
        parts = nid.split(":")
        # us:usc:42 or us:usc:42:4001
        if len(parts) == 3:
            url, text = uscode_title(parts[2])
            return result(text, url, f"Office of the Law Revision Counsel, {parts[2]} U.S.C.", "enacted", "excerpt")
        url, text = uscode_section(parts[2], parts[3])
        if not text or len(text) < 30:
            return None
        cov = "full" if len(text) < 25000 else "excerpt"
        return result(text, url, f"OLRC, {parts[2]} U.S.C. § {parts[3]}", "enacted", cov)

    if nid.startswith("us:cfr:") and allow("ecfr", "federal"):
        parts = nid.split(":")
        # us:cfr:44 or us:cfr:44:60.3
        if len(parts) == 3:
            url, text = ecfr_title(parts[2])
            return result(text, url, f"eCFR Title {parts[2]}", "enacted", "excerpt")
        url, text = ecfr_section(parts[2], parts[3])
        if not text or len(text) < 30:
            return None
        return result(text, url, f"eCFR {parts[2]} C.F.R. {parts[3]}", "enacted", "full")

    if nid.startswith("us:declaration") and allow("founding"):
        url, text = archives_main(
            "https://www.archives.gov/founding-docs/declaration-transcript",
            ["In Congress, July 4, 1776", "The unanimous Declaration"],
        )
        if nid.endswith("preamble-rights"):
            # rights paragraphs — exact official sentences
            m = re.search(
                r"We hold these truths[\s\S]+?their Safety and Happiness\.",
                text,
            )
            if m:
                text = m.group(0)
                return result(text, url, "National Archives, Declaration of Independence", "enacted", "excerpt")
        if nid.endswith("facts-takings-adjacent"):
            # listed abuses; take the facts section start
            m = re.search(r"He has[\s\S]{200,2500}", text)
            if m:
                return result(m.group(0)[:2500], url, "National Archives, Declaration of Independence", "enacted", "excerpt")
        return result(text, url, "National Archives, Stone Engraving transcript", "enacted", "full")

    if nid == "us:const" and allow("founding", "federal"):
        url, text = archives_main(
            "https://www.archives.gov/founding-docs/constitution-transcript",
            ["We the People of the United States"],
        )
        return result(text, url, "National Archives, Constitution of the United States", "enacted", "full")

    if nid == "us:articles" and allow("founding"):
        url, text = archives_main(
            "https://www.archives.gov/milestone-documents/articles-of-confederation",
            ["To all to whom these Presents", "Articles of Confederation"],
        )
        return result(text, url, "National Archives, Articles of Confederation", "enacted", "full")

    if nid == "us:northwest-ordinance" and allow("founding"):
        url, text = archives_main(
            "https://www.archives.gov/milestone-documents/northwest-ordinance",
            ["An Ordinance for the government", "Northwest Ordinance"],
        )
        return result(text, url, "National Archives, Northwest Ordinance", "enacted", "full")

    if nid == "us:land-act-1851" and allow("federal"):
        # 9 Stat. 631 — use govinfo statutes at large if possible
        url = "https://www.govinfo.gov/content/pkg/STATUTE-9/html/STATUTE-9-Pg631.htm"
        try:
            raw = http_get(url, headers={"User-Agent": BROWSER_UA})
            text = html_to_text(raw)
            return result(clean_law_text(text), url, "U.S. Statutes at Large, 9 Stat. 631 (govinfo)", "enacted", "full")
        except Exception:
            return None

    if nid == "us:const-conan" and allow("federal"):
        url, text = archives_main(
            "https://www.archives.gov/founding-docs/constitution-transcript",
            ["We the People of the United States"],
        )
        return result(text[:3000], "https://constitution.congress.gov/", "Constitution Annotated / National Archives transcript", "enacted", "excerpt")

    if nid.startswith("case:") and allow("cases"):
        cite = node.get("citation") or ""
        name_hint = (node.get("label") or "").split(",")[0]
        for url, source in CASE_OFFICIAL_PDFS.get(nid, []):
            try:
                text = pdf_text(url)
            except Exception:
                text = ""
            if text and len(text) > 80:
                cov = "full" if len(text) < 30000 else "excerpt"
                return result(text, url, source, "holding", cov)
        scocal = CASE_SCOCAL.get(nid)
        if scocal:
            try:
                text = scocal_opinion(scocal)
            except Exception:
                text = ""
            if text and len(text) > 80:
                cov = "full" if len(text) < 30000 else "excerpt"
                if len(text) > 60000:
                    text = text[:60000]
                    cov = "excerpt"
                return result(text, scocal, f"Stanford SCOCAL reproduction, {cite}", "holding", cov)
        us = parse_us_cite(cite)
        if us:
            loc = loc_us_reports_pdf(us[0], us[1])
            try:
                text = pdf_text(loc)
            except Exception:
                text = ""
            if text and len(text) > 80:
                cov = "full" if len(text) < 30000 else "excerpt"
                return result(text, loc, f"Library of Congress, {us[0]} U.S. {us[1]}", "holding", cov)
            url, text = cornell_case(us[0], us[1])
            if text and len(text) > 80:
                cov = "full" if len(text) < 30000 else "excerpt"
                if len(text) > 60000:
                    text = text[:60000]
                    cov = "excerpt"
                source = (
                    f"U.S. Reports {us[0]} U.S. {us[1]} via {url}"
                    if "courtlistener" in url
                    else f"Cornell LII, {us[0]} U.S. {us[1]}"
                )
                return result(text, url, source, "holding", cov)
        # Exact-cite CourtListener hit → official download_url only (no results[0]).
        try:
            rec = courtlistener_exact(cite.split("(")[0].strip(), name_hint=name_hint.split(" v.")[0])
        except Exception:
            rec = None
        if rec:
            for op in rec.get("opinions") or []:
                dl = op.get("download_url") or ""
                if dl.endswith(".pdf") and "opinions.aspx" not in dl:
                    try:
                        text = pdf_text(dl)
                    except Exception:
                        text = ""
                    if text and len(text) > 80:
                        cov = "full" if len(text) < 30000 else "excerpt"
                        return result(text, dl, f"Official opinion PDF ({cite})", "holding", cov)
        # Last resort: the node's own publisher URL, if it already points at a case page.
        own = node.get("url") or ""
        if own and ("justia.com" in own or "scocal.stanford.edu" in own):
            text = fetch_url_text(own) if own else ""
            if len(text) > 200 and "just a moment" not in text.lower():
                if len(text) > 60000:
                    text = text[:60000]
                return result(text, own, own, "holding", "excerpt")
        return None

    if nid.startswith("ca:ccr:") and allow("ccr", "state"):
        parts = nid.split(":")
        title = parts[2]
        official = "https://govt.westlaw.com/calregs/"
        lii = f"https://www.law.cornell.edu/regulations/california/title-{title}"
        if len(parts) >= 4:
            lii = f"https://www.law.cornell.edu/regulations/california/{title}-CCR-{parts[3]}"
        try:
            raw = http_get(lii, headers={"User-Agent": BROWSER_UA}, sleep=0.25)
            text = clean_law_text(html_to_text(raw))
            if len(text) < 80:
                text = clean_law_text(jina(lii))
            if len(text) > 80:
                return result(
                    text[:20000],
                    official,
                    f"California CCR Title {title} (LII reproduction; official host is Westlaw Cal. Code Regs.)",
                    "enacted",
                    "excerpt",
                )
        except Exception:
            try:
                text = clean_law_text(jina(lii))
                if len(text) > 80:
                    return result(text[:20000], official, f"California CCR Title {title} (LII; official host Westlaw)", "enacted", "excerpt")
            except Exception:
                return None
        return None

    if nid == "private:davis-stirling" and allow("leginfo", "state"):
        url, text = leginfo_section("CIV", "4000")
        return result(text, url, "California Legislative Counsel, Civ. § 4000 (Davis-Stirling)", "enacted", "excerpt")

    if nid.startswith("dist:") and allow("district"):
        url = node.get("url") or DISTRICT_URLS.get(nid) or ""
        if not url:
            return None
        text = fetch_url_text(url)
        if len(text) < 80:
            return None
        return result(text[:20000], url, url, "enacted", "excerpt")

    if nid == "ca:const-1849" and allow("founding", "state", "leginfo"):
        url = "https://www.sos.ca.gov/archives/collections/constitutions"
        text = fetch_url_text(url)
        if len(text) < 80:
            return None
        return result(text[:15000], url, "California Secretary of State Archives, 1849 Constitution collections", "enacted", "excerpt")

    return None


def result(text: str, url: str, source: str, kind: str, coverage: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if len(text) < 40:
        return None
    # refuse chrome-only pages
    low = text.lower()
    if "you have been blocked" in low or "just a moment" in low or "enable javascript" in low:
        return None
    if "performing security verification" in low or "complete the security check" in low:
        return None
    return {
        "text": text,
        "url": url,
        "text_source": source,
        "text_kind": kind,
        "coverage": coverage,
    }


def apply_fill(node: dict[str, Any], fill: dict[str, Any]) -> None:
    node["text"] = fill["text"]
    node["text_kind"] = fill["text_kind"]
    node["coverage"] = fill["coverage"]
    node["text_source"] = fill["text_source"]
    if fill.get("url"):
        node["url"] = fill["url"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma list: municode,belvedere,leginfo,uscode,ecfr,founding,cases,ccr,district")
    ap.add_argument("--overwrite", action="store_true", help="refill nodes previously ingested from Municode")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()} or None

    graph = load_json(DATA / "graph.json")
    corpora = {
        name: load_json(DATA / f"corpus_{name}.json")
        for name in ("tiburon", "belvedere", "paradise_cay", "strawberry")
    }

    print("Walking Municode TOC (Tiburon, Marin)…", flush=True)
    toc_t = walk_toc(TIBURON, str(TIBURON["product"])) if (not only or "municode" in only or "city" in only) else []
    toc_m = walk_toc(MARIN, str(MARIN["product"])) if (not only or "municode" in only or "county" in only) else []
    print(f"  Tiburon TOC nodes: {len(toc_t)}  Marin TOC nodes: {len(toc_m)}", flush=True)

    filled = 0
    failed: list[dict[str, str]] = []
    skipped = 0
    by_id = {n["id"]: n for n in graph["nodes"]}

    targets = [
        n
        for n in graph["nodes"]
        if should_fill(n, overwrite=args.overwrite) and relevant(n["id"], only)
    ]
    print(f"Targets: {len(targets)}", flush=True)

    for i, node in enumerate(targets, 1):
        nid = node["id"]
        try:
            fill = fill_node(node, toc_t, toc_m, only)
        except Exception as e:
            fill = None
            failed.append({"id": nid, "reason": f"error: {type(e).__name__}: {e}", "url": node.get("url") or ""})
            print(f"  [{i}/{len(targets)}] ERROR {nid}: {e}", flush=True)
            continue
        if not fill:
            skipped += 1
            failed.append(
                {
                    "id": nid,
                    "reason": "no official text fetched",
                    "url": node.get("url") or "",
                    "layer": node.get("layer") or "",
                    "type": node.get("type") or "",
                    "citation": node.get("citation") or "",
                }
            )
            print(f"  [{i}/{len(targets)}] gap {nid}", flush=True)
            continue
        apply_fill(node, fill)
        filled += 1
        print(f"  [{i}/{len(targets)}] filled {nid} ({fill['coverage']}, {len(fill['text'])} chars)", flush=True)

    # sync corpora
    for name, rows in corpora.items():
        for row in rows:
            src = by_id.get(row["id"])
            if src and src.get("text_kind") in {"enacted", "holding"} and src.get("text"):
                row["text"] = src["text"]
                row["text_kind"] = src["text_kind"]
                row["coverage"] = src["coverage"]
                row["text_source"] = src["text_source"]
                row["url"] = src.get("url") or row.get("url") or ""

    graph["meta"]["compiled_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    graph["meta"]["ingest_note"] = (
        "Enacted text ingested from official publishers. Catalog remains only where "
        "the publisher could not be fetched or the node is not an enacted instrument."
    )

    dump_json(DATA / "graph.json", graph)
    for name, rows in corpora.items():
        dump_json(DATA / f"corpus_{name}.json", rows)

    report = {
        "filled": filled,
        "gaps": len(failed),
        "skipped_unchanged": skipped,
        "failed": failed,
    }
    (DATA / "ingest-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nFilled {filled}. Remaining gaps {len(failed)}. Report: data/ingest-report.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
