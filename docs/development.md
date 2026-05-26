# Development

This project is intentionally simple: use a virtual environment, install pip
dependencies, and run the desktop app directly.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

## Run The App

```bash
python app.py
```

## Lightweight Verification

Compile the app package after code changes:

```bash
.venv/Scripts/python.exe -m compileall app
```

GUI changes should also be checked manually by launching the app and exercising
the touched workflow.

## Coding Style

- Use 2-space indentation in Python.
- Prefer readable, direct code over clever abstractions.
- Keep tool-specific behavior inside the relevant tool folder.
- Keep shared UI patterns inside `app/ui/`.
- Keep runtime dependencies in `requirements.txt`.
- Keep packaging dependencies in `requirements-build.txt`.

## Adding A New Tool

1. Create a folder under `app/tools/<tool_name>/`.
2. Add a `page.py` file with a QWidget subclass that inherits from
   `ToolPageBase`.
3. Add a `service.py` file if the tool has processing logic worth separating
   from UI behavior.
4. Register the tool in `app/core/tool_registry.py`.

Example registry entry:

```python
ToolDefinition(
  tool_id="example_tool",
  name="Example Tool",
  description="Short description shown on the home page.",
  category="Files",
  page_class=ExampleToolPage,
)
```

## Reusing UI Components

Before building new UI, check `app/ui/`.

Use `FileSelectionPanel` for workflows that need a file list, add/remove
buttons, and count text.

Use `ReorderableFileListWidget` when ordered file paths matter.

Avoid creating slightly different copies of shared widgets inside tool folders.
