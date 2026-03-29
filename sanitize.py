"""Filename sanitization utilities."""

import re
import os


def sanitize_title(title: str) -> str:
    """
    Sanitize a title for use in a filename.

    - Strip leading/trailing whitespace
    - Replace illegal characters (/ \\ : * ? " < > |) with space
    - Collapse multiple spaces into one
    - Truncate to 80 characters

    Args:
        title: Raw title string.

    Returns:
        Sanitized title safe for filenames.
    """
    # Replace illegal filename characters with space
    illegal_chars = r'[/\\:*?"<>|]'
    sanitized = re.sub(illegal_chars, ' ', title)

    # Collapse multiple spaces into one
    sanitized = re.sub(r'\s+', ' ', sanitized)

    # Strip whitespace
    sanitized = sanitized.strip()

    # Truncate to 80 chars
    sanitized = sanitized[:80]

    return sanitized


def make_filename(date: str, title: str) -> str:
    """
    Build a filename from date and title.

    Args:
        date: 6-digit YYMMDD date string.
        title: Document title.

    Returns:
        Filename in format "YYMMDD title.pdf".
    """
    sanitized_title = sanitize_title(title)
    return f"{date} {sanitized_title}.pdf"


def handle_duplicate_filename(output_dir: str, filename: str) -> str:
    """
    If filename exists, append _2, _3, etc. to avoid overwriting.

    Args:
        output_dir: Output directory path.
        filename: Target filename.

    Returns:
        Unique filename (either original or with _N suffix).
    """
    full_path = os.path.join(output_dir, filename)
    if not os.path.exists(full_path):
        return filename

    # Split filename into name and extension
    base, ext = os.path.splitext(filename)
    counter = 2
    while True:
        new_filename = f"{base}_{counter}{ext}"
        new_path = os.path.join(output_dir, new_filename)
        if not os.path.exists(new_path):
            return new_filename
        counter += 1
