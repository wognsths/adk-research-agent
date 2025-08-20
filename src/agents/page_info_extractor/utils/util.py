from urllib.parse import urlparse
import json
from typing import Any, Dict

def ensure_https(url: str) -> str:
    if not url:
        return url
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    return url

def coerce_to_dict(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        raw_str = raw.strip()
        # JSON blob일 가능성
        if raw_str.startswith("{") and raw_str.endswith("}"):
            try:
                return json.loads(raw_str)
            except json.JSONDecodeError:
                pass
        if "|" in raw_str:
            url_part, req_part = raw_str.split("|", 1)
            return {"url": url_part.strip(), "request": req_part.strip(), "valid": True}
        return {"url": "", "request": raw_str, "valid": False}
    return {"url": "", "request": "", "valid": False}