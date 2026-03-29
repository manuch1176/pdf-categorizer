# PDF Sorter — Architecture

## Goal

Take a single large PDF (typically ~100 pages) that has already had OCR applied, and automatically split it into individual document files. Each output file represents one logical document ("entity") and is named with the document date and a descriptive title derived from the content.

---

## Tech Stack

| Component | Library | Rationale |
|-----------|---------|-----------|
| PDF text extraction | `PyMuPDF` (fitz) | Fast, accurate text extraction from OCR'd PDFs; also handles PDF splitting |
| PDF splitting/export | `PyMuPDF` (fitz) | Same library — avoids a second dependency |
| LLM client | `openai` SDK | OpenRouter exposes an OpenAI-compatible API |
| CLI | `argparse` (stdlib) | No extra dependency needed for a simple CLI |
| Config / secrets | `python-dotenv` | Loads API key from `.env` without hardcoding |

**Python version:** 3.11+

---

## Processing Pipeline

```
input.pdf
    │
    ▼
┌─────────────────────────────┐
│  [1] Text Extraction        │
│  PyMuPDF: read each page    │
│  Output: [{page, text}, …]  │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  [2] LLM Analysis (OpenRouter)          │
│  - Concatenate all page texts           │
│  - Single API call with structured      │
│    JSON output request                  │
│  - LLM groups consecutive pages,        │
│    extracts date + title per group      │
│  Output: [{pages, date, title}, …]      │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  [3] Split & Export (PyMuPDF)           │
│  - For each entity: copy page range     │
│    from source PDF into new PDF         │
│  - Sanitize title (remove illegal chars)│
│  - Write "YYMMDD title.pdf"             │
└────────────┬────────────────────────────┘
             │
             ▼
output_dir/
    ├── 231015 Dentist Invoice Dr Mueller.pdf
    ├── 231101 Museum Annual Subscription.pdf
    ├── 240203 Organization XYZ Membership.pdf
    └── …
```

---

## LLM Integration

### Provider
OpenRouter (`https://openrouter.ai/api/v1`), using the `openai` Python SDK pointed at OpenRouter's base URL.

### Model Configuration
The model name is set as a constant in `config.py` and can be changed freely. Default: a capable, cost-efficient model such as `google/gemini-2.0-flash-001` or `anthropic/claude-3-5-haiku`.

### Prompt Design
A single system + user message call:

**System message:** Instructs the LLM to act as a document classifier. It must:
- Read page texts separated by `--- PAGE N ---` markers
- Group **consecutive** pages that form a single logical document
- For each group, extract the most relevant date found in the text (European format dd.mm.yyyy is common; output must be YYMMDD)
- Generate a short, descriptive English title (3–6 words, no special characters)
- Return **only** a JSON array — no prose, no markdown fences

**User message:** The full concatenated page text block.

### Output JSON Schema
```json
[
  {
    "pages": [1, 2],
    "date": "231015",
    "title": "Dentist Invoice Dr Mueller"
  },
  {
    "pages": [3],
    "date": "231101",
    "title": "Museum Annual Subscription"
  }
]
```

- `pages`: 1-indexed list of consecutive page numbers belonging to this entity
- `date`: 6-digit string YYMMDD; `"000000"` if no date found
- `title`: human-readable title, safe for use in a filename

### Fallback / Error Handling for LLM Response
- If JSON parse fails: retry once with an explicit "return only raw JSON" reminder
- If `date` is missing or malformed: use `"000000"` as fallback prefix
- If `title` is empty or missing: use `"Unknown Document"` + page range as fallback
- If a page is not assigned to any entity by the LLM: create a single-page entity for it with fallback naming

---

## PDF Handling

### Text Extraction
```python
import fitz  # PyMuPDF
doc = fitz.open("input.pdf")
pages = [{"page": i + 1, "text": doc[i].get_text()} for i in range(len(doc))]
```

### Splitting and Export
```python
output_doc = fitz.open()
output_doc.insert_pdf(source_doc, from_page=start-1, to_page=end-1)
output_doc.save("YYMMDD title.pdf")
```
Pages are 0-indexed in PyMuPDF but 1-indexed in all user-facing logic and LLM prompts.

---

## File Naming

Pattern: `YYMMDD descriptive title.pdf`

Examples:
- `231015 Dentist Invoice Dr Mueller.pdf`
- `240101 Swiss Museum Annual Pass.pdf`
- `000000 Unknown Document p4.pdf` (fallback)

**Sanitization rules applied to LLM-generated titles:**
- Strip leading/trailing whitespace
- Replace `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|` with a space or dash
- Collapse multiple spaces into one
- Truncate to 80 characters max

---

## Configuration

| Setting | Where | Default |
|---------|-------|---------|
| OpenRouter API key | `.env` → `OPENROUTER_API_KEY` | — (required) |
| Model name | `config.py` → `MODEL` | `google/gemini-2.0-flash-001` |
| Output directory | `--output` CLI flag | Same directory as input PDF |
| Max pages before chunking | `config.py` → `CHUNK_THRESHOLD` | `80` |

---

## Chunking Strategy for Large PDFs

If the PDF has more than `CHUNK_THRESHOLD` pages, the page texts are split into overlapping batches (e.g., batches of 60 pages with a 5-page overlap). The LLM is called once per batch. Entities that span a chunk boundary are detected by checking if the last group of one batch and the first group of the next share continuity signals, and merged if needed.

For typical use (~100 pages), a single call to a model with a 128k+ context window is sufficient and preferred.

---

## CLI Interface

```
python pdfsorter.py <input.pdf> [--output <dir>] [--model <model-id>] [--dry-run]
```

| Flag | Description |
|------|-------------|
| `input.pdf` | Path to the scanned, OCR'd PDF (required) |
| `--output <dir>` | Output directory (default: same folder as input) |
| `--model <id>` | Override model from config.py at runtime |
| `--dry-run` | Print entity list without writing any files |

---

## Error Handling Summary

| Situation | Behavior |
|-----------|----------|
| Page has no text (image-only page) | Included in adjacent entity; noted in output |
| LLM returns malformed JSON | One retry; if still broken, fall back to one entity per page |
| No date found in document | Prefix `000000` |
| Duplicate output filename | Append `_2`, `_3`, etc. |
| Missing API key | Exit immediately with a clear error message |
