# page_info_extractor/eval/main.py
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import List

from .config import Settings
from .eval import PageInfoExtractor


def _glob_htmls(pages_dir: Path, pattern: str, limit: int | None) -> List[Path]:
    candidates = sorted(pages_dir.rglob(pattern))
    if limit is not None:
        candidates = candidates[:limit]
    return [p for p in candidates if p.is_file()]


async def _amain_from_args(args) -> int:
    settings = Settings.load()
    extractor = PageInfoExtractor(settings)

    pages_dir = settings.pages_dir if args.pages_dir is None else Path(args.pages_dir).resolve()
    files = _glob_htmls(pages_dir, args.glob, args.limit)
    if not files:
        print(f"No files matched under {pages_dir} with pattern '{args.glob}'.")
        return 1

    print(f"Evaluating {len(files)} files with concurrency={settings.max_concurrency} on model={settings.model}…")
    results = await extractor.evaluate_files(args.query, files)

    out_path = settings.output_jsonl if args.output is None else Path(args.output).resolve()
    with out_path.open("w", encoding="utf-8") as f:
        for r in results:
            # r.json is already a list[ {is_valid, core_informations}, ... ]
            rec = {"file": r.file, "result": r.json}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Saved JSONL to {out_path}")
    return 0


async def _amain(query: str, pages_dir: str, glob_pattern: str = "*.html", limit: int = None) -> List[dict]:
    """
    Evaluate HTML files for a given query and return extracted information.
    
    Args:
        query: Query to validate against HTML pages
        pages_dir: Directory containing HTML files
        glob_pattern: Pattern to find HTML files
        limit: Optional limit on number of files
        
    Returns:
        List of extraction results
    """
    settings = Settings.load()
    extractor = PageInfoExtractor(settings)

    pages_path = Path(pages_dir).resolve()
    files = _glob_htmls(pages_path, glob_pattern, limit)
    if not files:
        return []

    print(f"Evaluating {len(files)} files with concurrency={settings.max_concurrency} on model={settings.model}…")
    results = await extractor.evaluate_files(query, files)

    # Convert to dict format
    result_list = []
    for r in results:
        result_list.append({"file": r.file, "result": r.json})
    
    return result_list


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-evaluate HTML pages for core info presence using Gemini.")
    parser.add_argument("--query", required=True, help="User query to validate against each HTML page.")
    parser.add_argument("--pages_dir", default=None, help="Directory containing HTML files (default: from config/.env).")
    parser.add_argument("--glob", default="*.html", help="Glob pattern to find HTML files recursively.")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of files.")
    parser.add_argument("--output", default=None, help="Output JSONL path (default: from config/.env).")

    args = parser.parse_args()
    try:
        exit(asyncio.run(_amain_from_args(args)))
    except KeyboardInterrupt:
        print("Interrupted.")
        exit(130)


if __name__ == "__main__":
    main()
