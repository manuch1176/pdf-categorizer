# PDF Sorter

Automatically split a large scanned OCR'd PDF into individual documents. Uses an LLM (via OpenRouter) to classify pages and group consecutive pages that form a single logical document.

## Installation

```bash
# Clone or navigate to the project directory
cd pdfsorter

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

## Usage

```bash
# Basic usage — output files appear next to input.pdf
python pdfsorter.py scan.pdf

# Specify output directory
python pdfsorter.py scan.pdf --output ./sorted/

# Preview what would be created (no files written)
python pdfsorter.py scan.pdf --dry-run

# Override the model
python pdfsorter.py scan.pdf --model anthropic/claude-3-5-haiku

# Enable verbose output (prints extracted text)
python pdfsorter.py scan.pdf --verbose
```

## Configuration

Edit `config.py` to change:
- `MODEL`: Default LLM model (OpenRouter model ID)
- `CHUNK_THRESHOLD`: Max pages before splitting into chunks (default 80)

## How It Works

1. **Extract**: Reads text from each page using PyMuPDF
2. **Classify**: Sends all page texts to an LLM, asking it to group consecutive pages and identify each group's date and title
3. **Parse**: Validates the LLM's JSON response and fills in missing dates/titles with fallbacks
4. **Export**: Splits the original PDF and saves each entity as a separate file named `YYMMDD title.pdf`

## Requirements

- Python 3.11+
- PyMuPDF (PDF extraction and splitting)
- openai SDK (for OpenRouter API)
- python-dotenv (for environment variable management)

See `requirements.txt` for exact versions.

## Troubleshooting

**"OPENROUTER_API_KEY not set"**
- Check that `.env` exists and contains a valid API key

**LLM returns malformed JSON**
- The parser will retry with stricter formatting instructions
- If it still fails, documents default to one entity per page with fallback titles

**Pages not grouped as expected**
- Check the extracted text (use `--verbose`) to see what the LLM sees
- Try a different model using `--model`

## See Also

- `ARCHITECTURE.md` — full design documentation
- `TASKS.md` — implementation checklist
- `CLAUDE.md` — Claude Code instructions
