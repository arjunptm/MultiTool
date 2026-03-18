# MultiTool

MultiTool is a Windows-only personal utility suite built in Python using PySide6 (Qt for Python).

It is designed as a scalable framework of small tools, where each tool is modular, easy to extend, and integrated into a single clean desktop UI.

---

## Features

- Simple launcher UI listing all available tools
- Modular architecture - each tool lives in its own folder
- Clean navigation between Home and tool pages
- Reusable UI components for rapid tool development
- Designed for personal use and iterative expansion

---

## Project Structure

app/
  core/
    tool_registry.py        # Central registry of all tools

  ui/
    tool_page_base.py       # Base layout for all tools
    home_page.py            # Main launcher screen
    widgets.py              # Generic UI widgets (e.g., ToolCard)
    file_widgets.py         # Reusable file-related UI components (NEW)

  tools/
    pdf_combine/
      page.py               # Tool UI + behavior
      service.py            # Tool-specific logic

    <future_tools>/
      page.py
      service.py (optional)

app.py                      # Entry point
requirements.txt           # Python dependencies
prompt.txt                 # ChatGPT development prompt

---

## Shared UI Layer

Reusable UI components live in app/ui/.

Currently available:

- ToolPageBase
  - Provides consistent layout for all tools
  - Includes title, subtitle, and back navigation

- file_widgets.py
  - ReorderableFileListWidget
    - Drag-and-drop file list
    - Maintains ordered file paths
  - FileSelectionPanel
    - Complete file selection UI:
      - title + subtitle
      - file list
      - Add / Remove buttons
      - file count label

Important:

If multiple tools need similar UI, it should be moved into app/ui/ instead of duplicating code inside tool folders.

---

## How to Add a New Tool

1. Create a new folder:

app/tools/<tool_name>/

2. Add a page.py file with a QWidget that inherits from ToolPageBase

3. (Optional) Add a service.py file for logic

4. Register the tool in:

app/core/tool_registry.py

---

## Reusing Existing UI Components

Before building UI from scratch, check app/ui/.

Use:

- FileSelectionPanel for tools that work with files
- ReorderableFileListWidget when file ordering matters

Avoid:

- Copy-pasting UI between tools
- Creating slightly different versions of the same widget

---

## What stays inside a tool

Each tool should contain:

- Its own processing logic (e.g., PDF handling, image resizing)
- File validation rules
- Tool-specific UI behavior
- Dialogs and workflows

Shared UI patterns should NOT live inside tool folders.

---

## Setup

### 1. Clone the repository

git clone <your-repo-url>
cd MultiTool

---

### 2. Create a virtual environment (recommended)

python -m venv .venv

---

### 3. Activate the virtual environment (IMPORTANT)

This must be done every time you open a new terminal before running the app.

Since this project is developed on Windows:

If you are using Bash (Git Bash / WSL / similar):

source .venv/Scripts/activate

If you are using Command Prompt:

.venv\Scripts\activate.bat

If you are using PowerShell:

.venv\Scripts\Activate.ps1

After activation, your terminal should show something like:

(.venv) ...

---

### 4. Install dependencies

pip install -r requirements.txt

---

### 5. Run the app

python app.py

---

## Project Archive Notes

When sharing this project (e.g., uploading to ChatGPT):

- The .venv/ folder is intentionally excluded
- __pycache__/ is excluded
- Dependencies are defined in requirements.txt

You can safely recreate the environment using pip.

---

## Creating a Clean Archive (Recommended)

Instead of zipping manually (which includes .venv), use:

git archive -o multitool-$(date +%Y%m%d).zip HEAD

This creates a clean archive with only tracked files.

---

## Contributing (Personal Project)

This is a personal project, and design decisions are made by the project owner.

That said, contributions and improvements are welcome.

---

## Developing with ChatGPT

This project is designed to work well with ChatGPT-assisted development.

To continue development in a new thread:

1. Zip the project (preferably using git archive)
2. Upload the ZIP
3. Paste the contents of prompt.txt
4. Describe what you want to build next

ChatGPT will use the prompt + codebase to continue development consistently.

---

## Design Philosophy

This project follows a framework-first approach:

- Keep tools modular and self-contained
- Share UI patterns through app/ui/
- Avoid duplicating UI logic across tools
- Prefer simple, readable abstractions

If something is reused across tools, it should be promoted to the shared UI layer.

---

## Acknowledgements

This project is:

- Designed and maintained as a personal utility suite
- Built entirely with the help of ChatGPT as a development assistant

---

## Future Ideas

- Image Resizer
- Bulk File Renamer
- File Format Converter
- Media Tools
- Progress indicators + threading
- Packaging as a Windows executable (.exe)