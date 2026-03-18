from dataclasses import dataclass
from typing import Type

from app.tools.pdf_combine.page import PdfCombinePage
from app.tools.image_resize.page import ImageResizePage
from app.tools.bulk_rename.page import BulkRenamePage


@dataclass(frozen=True)
class ToolDefinition:
  """
  Metadata describing a tool.

  page_class should be a QWidget subclass that accepts:
    - tool_definition
    - go_home_callback
  """
  tool_id: str
  name: str
  description: str
  category: str
  page_class: Type


def get_registered_tools() -> list[ToolDefinition]:
  """
  Central registry of tools.

  To add a new tool later:
  1. Create its page class under app/tools/<tool_name>/page.py
  2. Import it here
  3. Add a ToolDefinition entry below
  """
  return [
    ToolDefinition(
      tool_id="pdf_combine",
      name="Combine PDFs",
      description="Combine multiple PDF files, reorder pages, preview them, and optionally flatten before merging.",
      category="Documents",
      page_class=PdfCombinePage,
    ),
    ToolDefinition(
      tool_id="image_resize",
      name="Resize Images",
      description="Placeholder page for a future batch image resizing utility.",
      category="Images",
      page_class=ImageResizePage,
    ),
    ToolDefinition(
      tool_id="bulk_rename",
      name="Bulk Rename Files",
      description="Placeholder page for a future bulk file renaming utility.",
      category="Files",
      page_class=BulkRenamePage,
    ),
  ]