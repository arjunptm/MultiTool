from PySide6.QtWidgets import QLabel

from app.ui.tool_page_base import ToolPageBase


class PdfCombinePage(ToolPageBase):
  """
  Placeholder page for the future PDF Combine tool.
  """

  def __init__(self, tool_definition, go_home_callback):
    super().__init__(tool_definition, go_home_callback)

    info = QLabel(
      "This is a placeholder page for the future PDF combining tool.\n\n"
      "Later, this page can contain:\n"
      "- file selection\n"
      "- ordering controls\n"
      "- merge button\n"
      "- output path selection\n"
      "- validation and status messages"
    )
    info.setWordWrap(True)

    self.content_layout.addWidget(info)