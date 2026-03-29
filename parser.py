"""Parser for LLM responses."""

import json
import re


def parse_entities(llm_response: str) -> list[dict]:
    """
    Parse and validate JSON response from LLM.

    Args:
        llm_response: Raw response string from the LLM.

    Returns:
        List of validated entity dicts: [{"pages": [...], "date": "...", "title": "..."}, ...]

    Raises:
        ValueError: If JSON cannot be parsed even after cleanup.
    """
    # Try to extract JSON from the response (in case there's markdown or prose)
    json_str = extract_json(llm_response)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    # Validate and sanitize each entity
    entities = []
    for item in data:
        if not isinstance(item, dict):
            continue

        pages = item.get("pages", [])
        if not isinstance(pages, list):
            pages = []
        pages = [p for p in pages if isinstance(p, int)]

        date = item.get("date", "000000")
        if not isinstance(date, str):
            date = "000000"
        date = date.strip()
        if not re.match(r"^\d{6}$", date):
            date = "000000"

        title = item.get("title", "Unknown Document")
        if not isinstance(title, str):
            title = "Unknown Document"
        title = title.strip()
        if not title:
            title = "Unknown Document"

        if pages:
            entities.append({
                "pages": pages,
                "date": date,
                "title": title,
            })

    if not entities:
        raise ValueError("No valid entities parsed from LLM response")

    return entities


def extract_json(text: str) -> str:
    """
    Extract JSON content from text, stripping markdown fences if present.

    Args:
        text: Raw text that may contain JSON with markdown fences.

    Returns:
        JSON string (hopefully valid).
    """
    # Try to find JSON array within the text
    # Look for [ ... ] patterns
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        return match.group(0)

    # If that fails, return the whole text and let JSON parser handle it
    return text.strip()


def validate_entities(entities: list[dict], total_pages: int) -> list[dict]:
    """
    Perform post-parse validation and fallback creation for unmapped pages.

    Args:
        entities: Parsed entity list.
        total_pages: Total number of pages in the PDF.

    Returns:
        Validated entity list. If some pages are missing, create single-page fallback entities.
    """
    mapped_pages: dict[int, int] = {}  # page -> entity index
    for idx, entity in enumerate(entities):
        for page in entity["pages"]:
            if page in mapped_pages:
                prev_title = entities[mapped_pages[page]]["title"]
                print(
                    f"Warning: page {page} claimed by multiple entities "
                    f'("{prev_title}" and "{entity["title"]}")'
                )
            else:
                mapped_pages[page] = idx

        # Warn if page list is not consecutive
        pages_sorted = sorted(entity["pages"])
        if pages_sorted != list(range(pages_sorted[0], pages_sorted[-1] + 1)):
            print(
                f'Warning: entity "{entity["title"]}" has non-consecutive pages: {entity["pages"]}'
            )

    # Find unmapped pages
    all_pages = set(range(1, total_pages + 1))
    unmapped = sorted(all_pages - set(mapped_pages.keys()))

    # Create fallback entities for unmapped pages
    for page in unmapped:
        entities.append({
            "pages": [page],
            "date": "000000",
            "title": f"Unknown Document p{page}",
        })

    # Sort entities by first page number
    entities.sort(key=lambda e: e["pages"][0])

    return entities
