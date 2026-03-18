from PySide6.QtWidgets import QLabel

from app.ui.tool_page_base import ToolPageBase


class ImageResizePage(ToolPageBase):
  """
  Placeholder page for the future Image Resize tool.
  """

  def __init__(self, tool_definition, go_home_callback):
    super().__init__(tool_definition, go_home_callback)

    info = QLabel(
      "This is a placeholder page for the future image resizing tool.\n\n"
      "Later, this page can contain:\n"
      "- image or folder selection\n"
      "- width/height settings\n"
      "- aspect ratio options\n"
      "- output folder selection\n"
      "- preview and batch processing"
    )
    info.setWordWrap(True)

    self.content_layout.addWidget(info)