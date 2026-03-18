# MultiTool

MultiTool is a Windows-focused desktop utility application built in Python using PySide6. It is designed as a modular, extensible framework for everyday file and productivity tools.

The goal of this project is to provide a single, clean interface for a growing collection of utilities such as PDF operations, image processing, and file management tools - all within one cohesive desktop app.

---

## Features

### Framework

* Desktop GUI built with PySide6 (Qt for Python)
* Modular architecture for adding new tools easily
* Centralized tool registry system
* Consistent UI layout using reusable components

### Current Tool: PDF Combine

* Add multiple PDF files via native file picker
* Append files across multiple selections
* Drag-and-drop reordering
* Remove selected files
* Preview PDFs inside the app
* Combine PDFs in selected order
* Save output using native file dialog

#### Combine Modes

* **Combine**

  * Standard merge preserving original structure

* **Flatten and Combine**

  * Renders pages into a non-editable format before combining
  * Useful for locking in form fields and improving cross-device compatibility
  * Tradeoff: text may no longer be selectable/searchable

---

## Project Structure

```text
MultiTool/
  app.py
  requirements.txt
  prompt.txt

  app/
    main_window.py

    core/
      tool_registry.py

    ui/
      home_page.py
      tool_page_base.py
      widgets.py
      styles.py

    tools/
      pdf_combine/
        page.py
        service.py

    utils/
```

### Key Concepts

* **ToolPageBase**
  Provides consistent layout for all tools (title, description, content area, navigation)

* **Tool Registry**
  Central place to register and expose tools to the home screen

* **Service Layer (`service.py`)**
  Keeps business logic separate from UI code

* **Split Action Buttons**
  Used for actions with multiple modes (e.g., Combine vs Flatten)

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd MultiTool
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate it

Git Bash:

```bash
source .venv/Scripts/activate
```

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the App

```bash
python app.py
```

Or without activating the environment:

```bash
.venv/Scripts/python app.py
```

---

## How to Add a New Tool

1. Create a new folder under:

   ```
   app/tools/<tool_name>/
   ```

2. Add:

   * `page.py` (UI)
   * optionally `service.py` (logic)

3. Create a page class that inherits from `ToolPageBase`

4. Register it in:

   ```
   app/core/tool_registry.py
   ```

Once registered, it will automatically appear on the home screen.

---

## Contributing / Development Workflow

This project uses an **AI-assisted development workflow**. Contributions can follow a traditional approach or use ChatGPT as a coding assistant.

### Option 1 - Standard Development

* Fork the repository
* Create a feature branch
* Make changes following existing patterns
* Submit a pull request

---

### Option 2 - ChatGPT-Assisted Workflow (Recommended)

This repository includes a `prompt.txt` file that contains the project context and design guidelines.

#### Steps

1. Create a clean project archive (excluding `.venv` and generated files)

   Recommended (if using Git):

   ```bash
   git archive -o multitool-$(date +%Y%m%d).zip HEAD
   ```

   This automatically excludes:

   * `.venv/`
   * `__pycache__/`
   * other untracked/generated files

   Alternatively (manual):

   * Zip the `MultiTool/` folder
   * Exclude `.venv/` and cache files

2. Open a new ChatGPT session

3. Upload the generated `multitool.zip` file

4. Paste the contents of `prompt.txt`

5. Add your request, for example:

   * “Add a PDF split tool”
   * “Improve the UI for the file list”
   * “Add progress indicators for long operations”

6. Let ChatGPT:

   * analyze the codebase
   * summarize its understanding
   * propose and generate changes

7. Review the output and apply changes locally

---

### Notes

* The `.venv` folder is intentionally excluded from the archive
* Dependencies are defined in `requirements.txt`
* The environment should be recreated locally using pip

---

### Why this workflow exists

* Ensures continuity across development sessions
* Preserves architecture and design intent
* Reduces onboarding friction for contributors
* Allows rapid prototyping while maintaining structure

---

## Design Philosophy

This project follows a **framework-first approach**:

* Build a strong, scalable foundation before adding many tools
* Keep tools modular and self-contained
* Favor readability and maintainability over clever abstractions
* Reuse UI patterns across tools for consistency

---

## Future Plans

* PDF tools:

  * Split PDF
  * Extract pages
  * Rotate/reorder pages

* File tools:

  * Bulk rename
  * File organizer

* Image tools:

  * Resize images
  * Format conversion

* App improvements:

  * Persistent settings
  * Progress indicators for long tasks
  * Packaging as a Windows executable

---

## Acknowledgements

This is a personal project developed and designed by me.

All architectural decisions, feature planning, and implementation direction are made by me, with significant assistance from ChatGPT in:

* generating code
* iterating on design patterns
* refining architecture
* debugging and improving implementations

ChatGPT is used as a development assistant, while I retain full control over the design and evolution of the project.

---

## License

This project is currently for personal use. A license may be added in the future if the project is made public.
