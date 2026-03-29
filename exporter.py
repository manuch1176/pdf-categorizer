"""PDF splitting and export module."""

import os
import fitz
from sanitize import make_filename, handle_duplicate_filename


def export_entities(source_pdf_path: str, entities: list[dict], output_dir: str = None) -> list[str]:
    """
    Split source PDF and export each entity as a separate file.

    Args:
        source_pdf_path: Path to source PDF.
        entities: List of entity dicts with 'pages', 'date', 'title'.
        output_dir: Output directory. If None, use same dir as source PDF.

    Returns:
        List of created filenames (relative to output_dir).
    """
    if output_dir is None:
        output_dir = os.path.dirname(source_pdf_path)
        if not output_dir:
            output_dir = "."

    os.makedirs(output_dir, exist_ok=True)

    source_doc = fitz.open(source_pdf_path)
    created_files = []

    for entity in entities:
        pages = entity["pages"]
        date = entity["date"]
        title = entity["title"]

        # Create output filename
        filename = make_filename(date, title)
        filename = handle_duplicate_filename(output_dir, filename)

        # Create new PDF with selected pages (convert 1-indexed to 0-indexed for PyMuPDF)
        output_doc = fitz.open()
        for page_num in pages:
            output_doc.insert_pdf(source_doc, from_page=page_num - 1, to_page=page_num - 1)

        # Save
        output_path = os.path.join(output_dir, filename)
        output_doc.save(output_path)
        output_doc.close()

        created_files.append(filename)
        page_range = f"{pages[0]}-{pages[-1]}" if len(pages) > 1 else str(pages[0])
        print(f"✓ {filename} (pages {page_range})")

    source_doc.close()
    return created_files
