# -*- coding: utf-8 -*-
"""
Smart, lightweight site crawler (no Selenium) — saves RAW HTML.
- robots.txt respect
- sitemap.xml bootstrap
- MIME/size preflight via HEAD
- domain restriction + exclude regex
- traps avoided (utm/fbclid/session params)

Usage:
    python crawler.py https://example.com

Requirements:
    pip install httpx==0.27.0 selectolax==0.3.21 tldextract==5.1.2
"""
import sys
import os
import re
import csv
import asyncio
import urllib.parse
import hashlib
import xml.etree.ElementTree as ET
from collections import deque
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser
import tldextract

from .config import (
    MAX_PAGES, CONCURRENCY, TIMEOUT, MAX_BYTES,
    ALLOWED_HTML, RESPECT_ROBOTS, EXCLUDE_REGEX
)

# ---- helpers ----

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def safe_join(root: str, *parts: str) -> str:
    p = os.path.abspath(os.path.join(root, *parts))
    if not p.startswith(os.path.abspath(root)):
        raise ValueError("Unsafe path traversal detected")
    return p

def norm_url(base, href: str):
    if not href:
        return None
    href = href.split("#", 1)[0].strip()
    if not href:
        return None
    url = urllib.parse.urljoin(base, href)
    # Normalize and drop common trap params
    urlp = urllib.parse.urlsplit(url)
    q = urllib.parse.parse_qsl(urlp.query, keep_blank_values=False)
    drop = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content",
            "gclid","fbclid","sessionid","sid","phpsessid","msclkid"}
    q = [(k, v) for (k, v) in q if k.lower() not in drop]
    url = urllib.parse.urlunsplit((urlp.scheme, urlp.netloc,
                                   urllib.parse.unquote(urlp.path),
                                   urllib.parse.urlencode(q), ""))
    return url

def same_reg_domain(u0, u1) -> bool:
    e0, e1 = tldextract.extract(u0), tldextract.extract(u1)
    return (e0.domain, e0.suffix) == (e1.domain, e1.suffix)

def looks_like_client_rendered(html: str) -> bool:
    if len(html or "") < 1500:
        return True
    lower = (html or "").lower()
    hints = ["__next_data__", "window.__nuxt__", "data-server-rendered", "id=\"app\"", "vite"]
    score = sum(1 for h in hints if h in lower)
    return score >= 2

# ---- crawler ----

class Crawler:
    def __init__(self, start_url: str, out_dir: str = "./pages"):
        self.start_url = start_url.rstrip("/")
        self.root = f"{urllib.parse.urlsplit(self.start_url).scheme}://{urllib.parse.urlsplit(self.start_url).netloc}"
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

        self.index_path = safe_join(".", "index.csv")
        self.seen = set()
        self.results = []  # list of dict rows

        self.exclude_re = re.compile(EXCLUDE_REGEX) if EXCLUDE_REGEX else None

        self.rp = RobotFileParser()
        self.rp.set_url(urllib.parse.urljoin(self.root, "/robots.txt"))
        self._robots_loaded = False

    # ----- politeness / robots -----
    def robots_can_fetch(self, url: str) -> bool:
        if not RESPECT_ROBOTS:
            return True
        if not self._robots_loaded:
            try:
                self.rp.read()
            except Exception:
                pass
            self._robots_loaded = True
        try:
            return self.rp.can_fetch("*", url)
        except Exception:
            return True

    # ----- HTTP helpers -----
    async def head_ok(self, client: httpx.AsyncClient, url: str):
        # Returns (allowed:boolean, ctype:str, clen:int or None, final_url:str)
        try:
            r = await client.head(url, timeout=TIMEOUT, follow_redirects=True)
            ctype = r.headers.get("content-type","").split(";")[0].lower()
            clen = r.headers.get("content-length")
            clen = int(clen) if clen and clen.isdigit() else None
            if clen and clen > MAX_BYTES:
                return False, ctype, clen, str(r.url)
            return True, ctype, clen, str(r.url)
        except Exception:
            # Some servers don't support HEAD; allow and fallback to GET
            return True, "", None, url

    async def get_html(self, client: httpx.AsyncClient, url: str):
        try:
            r = await client.get(url, timeout=TIMEOUT, follow_redirects=True,
                                 headers={"User-Agent":"SmartHTMLCrawler/0.1"})
            ctype = r.headers.get("content-type","").split(";")[0].lower()
            if ctype not in ALLOWED_HTML:
                return None, None, None
            if r.headers.get("content-length"):
                try:
                    if int(r.headers["content-length"]) > MAX_BYTES:
                        return None, None, None
                except Exception:
                    pass
            return r.text, str(r.url), len(r.content or b"")
        except Exception:
            return None, None, None

    # ----- save -----
    def save_html(self, url: str, html: str) -> str:
        name = f"{sha1(url)}.html"
        path = safe_join(self.out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    # ----- sitemap bootstrap -----
    async def fetch_text(self, client, url):
        try:
            r = await client.get(url, timeout=TIMEOUT, follow_redirects=True,
                                 headers={"User-Agent": "SmartHTMLCrawler/0.1"})
            return r.text, str(r.url), r.headers.get("content-type","").split(";")[0].lower()
        except Exception:
            return None, None, None

    async def load_sitemaps(self, client):
        robots_url = urllib.parse.urljoin(self.root, "/robots.txt")
        txt, _, _ = await self.fetch_text(client, robots_url)
        candidates = set()
        if txt:
            for line in txt.splitlines():
                if line.lower().startswith("sitemap:"):
                    candidates.add(line.split(":",1)[1].strip())
        candidates.update({urllib.parse.urljoin(self.root, "/sitemap.xml")})

        seeds = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for sm in list(candidates):
            body, _, ctype = await self.fetch_text(client, sm)
            if not body or ("xml" not in (ctype or "")):
                continue
            try:
                rootxml = ET.fromstring(body)
                # sitemap index
                for loc in rootxml.findall(".//sm:sitemap/sm:loc", ns):
                    sub = loc.text.strip()
                    b2,_,c2 = await self.fetch_text(client, sub)
                    if b2 and "xml" in (c2 or ""):
                        r2 = ET.fromstring(b2)
                        for u in r2.findall(".//sm:url/sm:loc", ns):
                            seeds.append(u.text.strip())
                # plain urlset
                for u in rootxml.findall(".//sm:url/sm:loc", ns):
                    seeds.append(u.text.strip())
            except Exception:
                continue
        return seeds

    # ----- main loop -----
    async def run(self):
        async with httpx.AsyncClient(http2=True) as client:
            # 1) try sitemap bootstrap
            seeds = await self.load_sitemaps(client)
            q = deque()
            if seeds:
                for u in seeds:
                    u = norm_url(self.root, u)
                    if u and same_reg_domain(self.start_url, u) and u not in self.seen:
                        self.seen.add(u); q.append(u)
            else:
                q.append(self.start_url); self.seen.add(self.start_url)

            sem = asyncio.Semaphore(CONCURRENCY)

            async def worker():
                while q and len(self.results) < MAX_PAGES:
                    url = q.popleft()

                    if self.exclude_re and self.exclude_re.search(url):
                        continue
                    if not self.robots_can_fetch(url):
                        continue

                    # HEAD preflight
                    allowed, ctype_head, clen, final_url = await self.head_ok(client, url)
                    if not allowed:
                        continue

                    async with sem:
                        html, final_url, nbytes = await self.get_html(client, url)

                    if not html or not final_url:
                        continue

                    # save raw HTML
                    saved_path = self.save_html(final_url, html)

                    # minimal parse for links + metrics
                    try:
                        doc = HTMLParser(html)
                        client_hint = looks_like_client_rendered(html)
                        # enqueue new links
                        for node in doc.css("a[href]"):
                            nxt = norm_url(final_url, node.attributes.get("href"))
                            if not nxt:
                                continue
                            if not same_reg_domain(self.start_url, nxt):
                                continue
                            if self.exclude_re and self.exclude_re.search(nxt):
                                continue
                            if nxt not in self.seen:
                                self.seen.add(nxt)
                                q.append(nxt)
                    except Exception:
                        client_hint = False

                    self.results.append({
                        "url": final_url,
                        "file": os.path.relpath(saved_path),
                        "content_length": nbytes or clen or "",
                        "client_rendered_hint": client_hint,
                    })

            tasks = [asyncio.create_task(worker()) for _ in range(CONCURRENCY)]
            await asyncio.gather(*tasks)

        # write index
        with open(self.index_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["url","file","content_length","client_rendered_hint"])
            w.writeheader()
            for row in self.results:
                w.writerow(row)

        return len(self.results)

def main():
    if len(sys.argv) < 2:
        print("Usage: python crawler.py https://example.com")
        sys.exit(1)
    start_url = sys.argv[1]
    crawler = Crawler(start_url=start_url, out_dir="./pages")
    total = asyncio.run(crawler.run())
    print(f"Saved {total} HTML pages to ./pages and index.csv")

if __name__ == "__main__":
    main()
