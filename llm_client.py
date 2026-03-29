"""LLM client for document classification via OpenRouter."""

import os
import json
import time
import openai
from openai import OpenAI
import config

_MAX_RETRIES = 3


def chunk_pages(pages: list[dict], threshold: int = None, overlap: int = 5) -> list[list[dict]]:
    """
    Split pages into overlapping chunks if needed.

    Args:
        pages: List of page dicts with 'page' and 'text' keys.
        threshold: Page count threshold; if pages exceed this, chunk them.
        overlap: Number of pages to overlap between chunks.

    Returns:
        List of page chunks. If pages fit in one chunk, returns [pages].
    """
    if threshold is None:
        threshold = config.CHUNK_THRESHOLD

    if len(pages) <= threshold:
        return [pages]

    chunks = []
    chunk_size = threshold
    i = 0
    while i < len(pages):
        end = min(i + chunk_size, len(pages))
        chunks.append(pages[i:end])
        if end >= len(pages):
            break
        i = end - overlap

    return chunks


def build_prompt() -> tuple[str, str]:
    """
    Build system and user message templates.

    Returns:
        Tuple of (system_message, user_message_template).
    """
    system_message = """You are a document classifier. You will receive text from multiple pages of a scanned PDF, separated by '--- PAGE N ---' markers.

Your task:
1. Group consecutive pages that form a single logical document (e.g., a multi-page invoice, a contract, etc.).
2. For each group, identify:
   - The list of consecutive page numbers (1-indexed) that form this entity
   - The most relevant date found in the text (in YYMMDD format; if the text contains European-style dates like dd.mm.yyyy, convert them)
   - A short English title (3–6 words, no special characters, no slashes or colons)
3. Return ONLY a valid JSON array, with no markdown fences, no prose, no explanation.

The JSON array should have this structure:
[
  {"pages": [1, 2], "date": "231015", "title": "Dentist Invoice Dr Mueller"},
  {"pages": [3], "date": "231101", "title": "Museum Annual Subscription"}
]

If you cannot find a date, use "000000". If the title is unclear, use "Unknown Document"."""

    user_message_template = """Here are the page texts:

{page_text}"""

    return system_message, user_message_template


def format_pages_for_prompt(pages: list[dict]) -> str:
    """
    Concatenate page texts with clear separators.

    Args:
        pages: List of page dicts with 'page' and 'text' keys.

    Returns:
        Formatted string with page markers.
    """
    lines = []
    for page_dict in pages:
        page_num = page_dict["page"]
        text = page_dict["text"]
        lines.append(f"--- PAGE {page_num} ---")
        lines.append(text)
    return "\n".join(lines)


def classify_pages(pages: list[dict], model: str = None, extra_nudge: str = None) -> str:
    """
    Call OpenRouter to classify and group pages.

    Args:
        pages: List of page dicts with 'page' and 'text' keys.
        model: Model ID (uses config.MODEL if not provided).
        extra_nudge: Optional extra instruction appended to the user message (used for JSON retry).

    Returns:
        Raw response string from the LLM (should be JSON).

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    if model is None:
        model = config.MODEL

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in environment")

    client = OpenAI(
        api_key=api_key,
        base_url=config.OPENROUTER_BASE_URL,
    )

    system_msg, user_template = build_prompt()
    page_text = format_pages_for_prompt(pages)
    user_msg = user_template.format(page_text=page_text)
    if extra_nudge:
        user_msg = user_msg + "\n\n" + extra_nudge

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4096,
            )
            break
        except (openai.RateLimitError, openai.APITimeoutError, openai.APIError) as e:
            if attempt == _MAX_RETRIES - 1:
                raise
            wait = 2 ** (attempt + 1)
            print(f"  LLM error ({e}); retrying in {wait}s...", flush=True)
            time.sleep(wait)

    try:
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Response content is None")
        return content
    except (AttributeError, IndexError, TypeError) as e:
        raise ValueError(f"Unexpected response structure: {e}")
