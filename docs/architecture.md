# Architecture

MultiTool uses a small framework-style structure so new tools can be added
without rewriting the main application shell.

## Entry Point

`app.py` creates the `QApplication`, applies the shared stylesheet from
`app/ui/styles.py`, creates `MainWindow`, and starts the Qt event loop.

## Main Window

`app/main_window.py` owns the top-level `QMainWindow` and a `QStackedWidget`.
The stack contains:

- the home page
- one page per registered tool
- a fallback missing-tool page for registry mistakes

Navigation is intentionally centralized in `MainWindow`.

## Tool Registry

`app/core/tool_registry.py` defines `ToolDefinition` metadata and returns the
list of registered tools.

Each tool definition includes:

- `tool_id`
- `name`
- `description`
- `category`
- `page_class`

The home page reads this registry to display tool cards. The main window uses
the same registry to instantiate tool pages.

## Shared UI Layer

Reusable UI code belongs in `app/ui/`.

Current shared pieces include:

- `ToolPageBase`: common tool page shell with title, subtitle, back navigation,
  and a content area.
- `HomePage`: launcher page grouped by tool category.
- `ToolCard`: reusable card for the home page.
- `FileSelectionPanel`: reusable file selection panel with buttons, count text,
  and a reorderable file list.
- `ReorderableFileListWidget`: drag-and-drop file list that stores full paths.
- `styles.py`: shared application stylesheet.

If multiple tools need the same UI pattern, move that pattern into `app/ui/`
instead of duplicating it inside tool folders.

## Tool Modules

Each tool lives in `app/tools/<tool_name>/`.

Typical files:

- `page.py`: QWidget subclass for the tool UI and user interaction.
- `service.py`: tool-specific processing logic, when needed.
- `__init__.py`: package marker.

Tool pages inherit from `ToolPageBase`. Tool-specific logic should stay inside
the tool folder unless it becomes genuinely reusable.

## Current Tools

`pdf_combine` combines and optionally raster-flattens multiple PDFs.

`sign_pdf` adds one visual signature to one selected page of a PDF. It supports
uploaded signature images, drawn signatures, drag placement, resizing, scaling,
rotation, and saving a signed copy.

`image_resize` and `bulk_rename` are placeholders for future tools.
