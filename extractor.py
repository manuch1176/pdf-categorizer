"""PDF text extraction module using PyMuPDF."""

import fitz


def extract_pages(pdf_path: str) -> list[dict]:
    """
    Extract text from each page of a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of dicts: [{"page": 1, "text": "..."}, ...]
        Pages are 1-indexed.
    """
    doc = fitz.open(pdf_path)
    pages = []

    for i in range(len(doc)):
        text = doc[i].get_text()
        pages.append({
            "page": i + 1,
            "text": text
        })

    doc.close()
    return pages
