# SmartCrawler (raw HTML)

Same "smart" crawl (robots + sitemap + MIME/size preflight + filters), but saves **raw HTML**.

## Install
```bash
pip install httpx==0.27.0 selectolax==0.3.21 tldextract==5.1.2
```

## Run
```bash
python crawler.py https://example.com
```
Outputs:
- `./pages/<sha1>.html` — raw HTML
- `./index.csv` — url, file, content_length, client_rendered_hint
