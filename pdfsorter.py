#!/usr/bin/env python3
"""PDF Sorter — CLI entrypoint."""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

import config
from extractor import extract_pages
from llm_client import classify_pages, chunk_pages
from parser import parse_entities, validate_entities
from exporter import export_entities


def main():
    parser = argparse.ArgumentParser(
        description="Split a scanned PDF into individual documents using LLM classification."
    )
    parser.add_argument("input", help="Path to input PDF file")
    parser.add_argument(
        "--output",
        help="Output directory (default: same as input file)",
        default=None,
    )
    parser.add_argument(
        "--model",
        help="Override model from config.py",
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print entity list without writing files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extracted page text for debugging",
    )

    args = parser.parse_args()

    # Load .env
    load_dotenv()

    # Validate API key early — before doing any expensive work
    if not os.getenv("OPENROUTER_API_KEY"):
        print(
            "Error: OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Set output directory
    if args.output:
        output_dir = args.output
    else:
        output_dir = os.path.dirname(args.input)
        if not output_dir:
            output_dir = "."

    # Step 1: Extract text
    print("Extracting text from PDF...")
    try:
        pages = extract_pages(args.input)
    except Exception as e:
        print(f"Error extracting PDF: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Extracted {len(pages)} pages")

    if args.verbose:
        for page in pages:
            print(f"--- PAGE {page['page']} ---")
            print(page['text'][:200] + "..." if len(page['text']) > 200 else page['text'])

    # Step 2: Determine if chunking is needed
    model = args.model or config.MODEL
    if len(pages) > config.CHUNK_THRESHOLD:
        print(f"  Pages exceed threshold ({config.CHUNK_THRESHOLD}); will chunk")
        page_chunks = chunk_pages(pages, threshold=config.CHUNK_THRESHOLD)
    else:
        page_chunks = [pages]

    # Step 3: Classify with LLM
    print(f"Calling LLM ({model})...")
    all_entities = []
    for i, chunk in enumerate(page_chunks):
        if len(page_chunks) > 1:
            print(f"  Chunk {i+1}/{len(page_chunks)} (pages {chunk[0]['page']}-{chunk[-1]['page']})")
        try:
            response = classify_pages(chunk, model=model)
            try:
                entities = parse_entities(response)
            except ValueError:
                # JSON parse failed — retry once with an explicit nudge
                print("  JSON parse failed; retrying with stricter prompt...")
                response = classify_pages(
                    chunk,
                    model=model,
                    extra_nudge="IMPORTANT: Return ONLY a raw JSON array with no markdown, no prose, no explanation.",
                )
                entities = parse_entities(response)
            all_entities.extend(entities)
        except Exception as e:
            print(f"Error calling LLM: {e}", file=sys.stderr)
            sys.exit(1)

    # Step 4: Validate and fill gaps
    print(f"Parsed {len(all_entities)} entities")
    all_entities = validate_entities(all_entities, len(pages))

    # Step 5: Print summary
    print("\nEntity summary:")
    for entity in all_entities:
        page_range = f"{entity['pages'][0]}-{entity['pages'][-1]}" if len(entity['pages']) > 1 else str(entity['pages'][0])
        print(f"  {entity['date']} | {entity['title']:<40} | pages {page_range}")

    if args.dry_run:
        print("\n(dry-run: no files written)")
        return

    # Step 6: Export
    print(f"\nExporting to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    try:
        created = export_entities(args.input, all_entities, output_dir=output_dir)
        print(f"\nSuccess! Created {len(created)} files.")
    except Exception as e:
        print(f"Error exporting PDFs: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
