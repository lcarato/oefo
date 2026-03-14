# Installation Guide

This guide provides step-by-step instructions for installing OEFO and configuring it for development or production use.

## Prerequisites

- **Python 3.10 or higher** (check with `python --version`)
- **Git** (for cloning the repository)
- **pip** (included with Python 3.10+)

## System Dependencies

OEFO relies on external tools for PDF processing and optical character recognition. Install these before proceeding with Python setup.

### macOS (via Homebrew)

If you don't have Homebrew installed, visit [brew.sh](https://brew.sh).

```bash
brew install poppler tesseract
```

**Apple Silicon (M-series) Note:** Homebrew automatically installs ARM64-native versions of poppler and tesseract on M1/M2/M3 Macs. No special configuration is needed; just run the commands above.

### Linux (Ubuntu/Debian via apt)

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

For other Linux distributions, use your package manager (dnf on Fedora, pacman on Arch, etc.) to install equivalents of `poppler` and `tesseract`.

### Windows

Windows support for OEFO is experimental. You can:
1. Use Windows Subsystem for Linux (WSL) and follow the Linux instructions
2. Install pre-compiled binaries:
   - Poppler: Download from [blog.alivate.com.au/poppler-windows/](https://blog.alivate.com.au/poppler-windows/) and add to PATH
   - Tesseract: Download installer from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Python Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/lcarato/oefo.git
cd oefo
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment:

**macOS / Linux:**
```bash
source venv/bin/activate
```

**Windows (cmd):**
```cmd
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

### Step 3: Upgrade pip and Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -e .
```

For development (includes testing and linting tools):

```bash
pip install -e ".[dev]"
```

## Environment Configuration

OEFO requires at least one LLM provider API key to function. Configuration is managed via environment variables or a `.env` file.

### Create a `.env` File

In the project root directory, create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your API credentials:

```env
# At least one LLM provider is required
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxx
# Optional fallback provider
OPENAI_API_KEY=sk-xxxxxxxxxxxxxx

# Optional configuration
OEFO_DATA_DIR=./data
OEFO_LOG_LEVEL=INFO
OEFO_TRACEABILITY=FULL
```

### Required API Keys

- **Anthropic API Key** (preferred):
  1. Visit [console.anthropic.com](https://console.anthropic.com)
  2. Create an account or log in
  3. Navigate to "API Keys"
  4. Click "Create Key"
  5. Copy the key and paste into `.env` as `ANTHROPIC_API_KEY`

- **OpenAI API Key** (optional fallback):
  1. Visit [platform.openai.com](https://platform.openai.com/api-keys)
  2. Create an account or log in
  3. Click "Create new secret key"
  4. Copy and paste into `.env` as `OPENAI_API_KEY`

Alternatively, set environment variables directly:

```bash
export ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxxx"
oefo --help
```

## Verification Steps

### Check Installation

Verify that the CLI is accessible:

```bash
oefo --help
```

You should see the command-line help output.

### Validate Environment

Check that all dependencies are correctly installed:

```bash
python scripts/oefo_env_check.py
```

This script validates:
- Python version
- System dependencies (poppler, tesseract)
- Python package dependencies
- LLM provider connectivity (if configured)
- Data directory access

### Quick Test Run

Extract data from a sample PDF:

```bash
# First ensure you have sample data
oefo scrape ifc --limit 1

# Extract from the downloaded PDF
oefo extract ./data/raw/ifc --source-type dfi --limit 1
```

## Troubleshooting

### "poppler-utils not found" or "tesseract not found"

**Cause:** System dependencies not installed or not in PATH.

**Solution:**
- Verify installation: `which poppler-config` (macOS/Linux) or `where poppler` (Windows)
- Reinstall: `brew install poppler tesseract` (macOS) or `sudo apt-get install poppler-utils tesseract-ocr` (Linux)
- On macOS, if Homebrew installation didn't add to PATH, try: `export PATH="/usr/local/bin:$PATH"`

### "ModuleNotFoundError: No module named 'oefo'"

**Cause:** OEFO not installed in editable mode.

**Solution:**
```bash
# Ensure virtual environment is activated, then:
pip install -e .
```

### "ANTHROPIC_API_KEY not set"

**Cause:** API key not configured.

**Solution:**
1. Create `.env` file in project root with your API key
2. Or set environment variable: `export ANTHROPIC_API_KEY="your-key"`
3. Verify: `python -c "import os; print('Key set:', bool(os.getenv('ANTHROPIC_API_KEY')))"`

### "Connection refused" or timeout errors during scraping

**Cause:** Network connectivity issue or target website blocking requests.

**Solution:**
- Check internet connection: `ping google.com`
- Try again with retry logic: `oefo scrape ifc --retries 3`
- Check if website is down: Visit the website in a browser
- Configure a proxy if behind corporate firewall: Set `HTTP_PROXY` and `HTTPS_PROXY` environment variables

### CI/CD Failures on Specific Python Version

**Cause:** Platform-specific dependency issues or version incompatibilities.

**Solution:**
- Test locally on the same Python version: `python3.10 --version`
- Check GitHub Actions logs for specific error messages
- Common fixes:
  - Update setuptools: `pip install --upgrade setuptools`
  - Clear pip cache: `pip cache purge` then reinstall
  - For macOS ARM64 issues: Use `arch -arm64 brew install ...`

## Next Steps

Once installation is complete, see the following for usage instructions:

- [Architecture Overview](ARCHITECTURE.md) — Understanding the system design
- [Main README](../README.md) — Quick start and CLI reference
- [Agent Operations](../OEFO_Agent_Autonomous_Operations.md) — Autonomous pipeline operation
- [OpenClaw Integration](OPENCLAW.md) — Scheduled automated operations

