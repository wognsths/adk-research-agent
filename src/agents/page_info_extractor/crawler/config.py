# -*- coding: utf-8 -*-
"""
Config for Smart HTML crawler.
"""

# Crawl scale/perf
MAX_PAGES = 3             # max pages to visit
CONCURRENCY = 20           # concurrent HTTP requests
TIMEOUT = 15               # seconds
MAX_BYTES = 2_000_000      # skip resources larger than this (bytes)

# Content allowlist (HTML)
ALLOWED_HTML = {"text/html"}

# Politeness / robots
RESPECT_ROBOTS = True

# URL/path exclusions (regex). Add patterns to avoid admin/auth/search, etc.
EXCLUDE_REGEX = r"/(admin|auth|login|logout|cart|user-api-key|search\?|tag/|session|my/)"
