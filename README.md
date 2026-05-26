# MultiTool

[![Release Windows Build](https://github.com/arjunptm/MultiTool/actions/workflows/release-windows.yml/badge.svg)](https://github.com/arjunptm/MultiTool/actions/workflows/release-windows.yml)
[![Latest Release](https://img.shields.io/github/v/release/arjunptm/MultiTool)](https://github.com/arjunptm/MultiTool/releases)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

MultiTool is a Windows-only personal utility suite built with Python and
PySide6. It provides a single desktop launcher for small, practical tools that
can be added over time without changing the core navigation structure.

## Current Tools

- Combine PDFs: merge multiple PDFs, reorder files, preview selections, and
  optionally flatten pages before combining.
- Sign PDF: add one visual signature to a selected PDF page by uploading an
  image or drawing a signature.
- Resize Images: placeholder for a future batch image resizing utility.
- Bulk Rename Files: placeholder for a future bulk file renaming utility.

## Quick Start

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
python app.py
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Repository Layout

```text
app/                    Application source
  core/                 Tool registry and core app metadata
  tools/                Individual tool modules
  ui/                   Shared UI components and styling
  utils/                Shared utility helpers
docs/                   Project documentation
.github/workflows/     GitHub Actions automation
app.py                  Application entry point
requirements.txt        Runtime dependencies
requirements-build.txt  Packaging dependencies
MultiTool.spec          PyInstaller build recipe
```

## Documentation

- [Architecture](docs/architecture.md)
- [Development](docs/development.md)
- [Packaging](docs/packaging.md)
- [Releases](docs/releases.md)
- [AI Collaboration](docs/ai-collaboration.md)
- [Roadmap](docs/roadmap.md)

## Build A Windows Executable

```bash
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean MultiTool.spec
```

The packaged app is created in `dist/MultiTool/`.

## Project Status

This is a personal project designed for steady, practical growth. The codebase
prioritizes readability, modular tools, and reusable UI patterns over broad
framework abstractions.
