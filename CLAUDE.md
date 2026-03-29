# PDF Sorter — Claude Code Instructions

## Project Description

A Python CLI tool that takes a single large OCR'd PDF (typically ~100 scanned pages) and splits it into individual document files. It uses an LLM via OpenRouter to understand each page's content, group consecutive pages that form a single logical document, extract a date, and generate a descriptive title. Each output file is named `YYMMDD descriptive title.pdf`.

---

## How to Run

```bash
# Basic usage — output files land next to input.pdf
python pdfsorter.py scan.pdf

# Specify output directory
python pdfsorter.py scan.pdf --output ./sorted/

# Preview what would be created (no files written)
python pdfsorter.py scan.pdf --dry-run

# Override the model at runtime
python pdfsorter.py scan.pdf --model anthropic/claude-3-5-haiku
```

---

## Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and paste your OpenRouter API key
```

---

## Changing the Model

Edit `config.py`:

```python
MODEL = "google/gemini-2.0-flash-001"  # change this to any OpenRouter model ID
```

Or pass `--model <id>` at runtime to override without editing the file.

---

## File Structure

```
pdfsorter/
├── pdfsorter.py       # CLI entrypoint — argparse, pipeline orchestration
├── extractor.py       # PDF text extraction (PyMuPDF)
├── llm_client.py      # OpenRouter API call + prompt builder + chunking
├── parser.py          # Parse and validate LLM JSON response
├── exporter.py        # Split source PDF into entity files (PyMuPDF)
├── sanitize.py        # Filename sanitization + duplicate handling
├── config.py          # MODEL, CHUNK_THRESHOLD, OPENROUTER_BASE_URL constants
├── requirements.txt   # PyMuPDF, openai, python-dotenv
├── .env               # OPENROUTER_API_KEY (not committed)
├── .env.example       # Template for .env
├── ARCHITECTURE.md    # Full design document
└── TASKS.md           # Implementation checklist
```

---

## Key Design Decisions to Preserve

1. **Single LLM call per run** (or per chunk if >80 pages) — do not call the LLM once per page; that would be slow and expensive.

2. **Structured JSON output from LLM** — the prompt asks for a raw JSON array with no markdown or prose. The parser strips fences if present, but the design relies on this structure. Do not change the output schema without updating both `llm_client.py` (prompt) and `parser.py` (validation).

3. **PyMuPDF for everything PDF-related** — use `fitz` for both text extraction and PDF splitting. Do not add `pypdf`, `pdfplumber`, or other PDF libraries unless there is a concrete reason.

4. **Pages are 1-indexed in all user-facing logic and LLM prompts** — PyMuPDF uses 0-indexed pages internally; convert at the boundary in `extractor.py` and `exporter.py`.

5. **Never delete the input file** — the tool is read-only with respect to the source PDF.

6. **Fallbacks over crashes** — if the LLM returns something unexpected, fall back gracefully (one entity per page, `000000` date prefix, `Unknown Document` title) rather than raising an unhandled exception.

---

## Dependencies

```
PyMuPDF>=1.24.0
openai>=1.0.0
python-dotenv>=1.0.0
```

---

## OpenRouter Notes

OpenRouter uses the OpenAI SDK with a different base URL:

```python
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
```

Model IDs use the format `provider/model-name`, e.g.:
- `google/gemini-2.0-flash-001`
- `anthropic/claude-3-5-haiku`
- `openai/gpt-4o-mini`
