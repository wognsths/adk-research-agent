# page_info_extractor/eval/eval.py
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Any

from google import genai
from google.genai import types, errors

from .config import Settings
from .html_processor import HTMLProcessor


# Explicit JSON schema: ARRAY of OBJECTs
EVAL_SCHEMA = types.Schema(
    type="ARRAY",
    items=types.Schema(
        type="OBJECT",
        required=["is_valid", "core_informations"],
        properties={
            "is_valid": types.Schema(type="BOOLEAN"),
            "core_informations": types.Schema(
                type="ARRAY",
                items=types.Schema(type="STRING"),
            ),
        },
    ),
)

SYSTEM_INSTRUCTION = (
    "You are an information validator. Given a user query and an HTML page, "
    "decide whether the page contains information that directly matches the query. "
    "If yes, set is_valid=true and extract the minimal core facts, as it is."
    "If not, set is_valid=false and return an empty list. Respond ONLY in JSON."
)


def _build_contents(query: str, html_text: str, preprocess: bool = True) -> List[types.Content]:
    # Preprocess HTML to extract clean text content
    if preprocess:
        clean_text = HTMLProcessor.clean_html(html_text)
        content_text = f"QUERY:\n{query}\n\nCLEANED CONTENT:\n{clean_text}"
        
        return [
            types.Content(
                role="user",
                parts=[types.Part(text=content_text)],
            )
        ]
    else:
        # Use original HTML format if preprocessing is disabled
        return [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=f"QUERY:\n{query}"),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="text/html",
                            data=html_text.encode("utf-8"),
                        )
                    ),
                ],
            )
        ]


@dataclass
class ExtractResult:
    file: str
    json: Any  # parsed JSON returned by the model


class PageInfoExtractor:
    """LLM-based HTML validator/extractor with async concurrency & retries."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        self.client = genai.Client(api_key=self.settings.google_api_key)  # uses GOOGLE_API_KEY from env
        self.model = self.settings.model
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=EVAL_SCHEMA,
            temperature=self.settings.temperature,
            max_output_tokens=self.settings.max_output_tokens,
        )

    async def _evaluate_one(self, query: str, html_text: str, *, timeout_s: int | None = None) -> Any:
        timeout_s = timeout_s or self.settings.request_timeout_s
        contents = _build_contents(query, html_text, preprocess=self.settings.preprocess_html)

        delay = 1.0
        last_err: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                resp = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=self.config,
                    ),
                    timeout=timeout_s,
                )
                print(resp)
                
                # Check if response has valid text content
                if resp.text is None:
                    raise ValueError(f"Response text is None. Response: {resp}")
                
                return json.loads(resp.text)
            except (errors.APIError, asyncio.TimeoutError, ValueError, json.JSONDecodeError) as e:
                last_err = e
                if attempt == self.settings.max_retries - 1:
                    raise
                await asyncio.sleep(delay)
                delay *= 2
        # Should not reach here
        raise RuntimeError(f"Unexpected retry loop exit: {last_err}")

    async def evaluate_files(self, query: str, files: Iterable[Path]) -> List[ExtractResult]:
        sem = asyncio.Semaphore(self.settings.max_concurrency)

        async def run_one(p: Path) -> ExtractResult:
            async with sem:
                text = p.read_text(encoding="utf-8", errors="ignore")
                # Optional size cap
                if len(text.encode("utf-8")) > self.settings.max_html_bytes:
                    text = text[: self.settings.max_html_bytes]
                data = await self._evaluate_one(query, text)
                return ExtractResult(file=str(p), json=data)

        tasks = [asyncio.create_task(run_one(path)) for path in files]
        return await asyncio.gather(*tasks)
