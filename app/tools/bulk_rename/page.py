from PySide6.QtWidgets import QLabel

from app.ui.tool_page_base import ToolPageBase


class BulkRenamePage(ToolPageBase):
  """
  Placeholder page for the future Bulk Rename Files tool.
  """

  def __init__(self, tool_definition, go_home_callback):
    super().__init__(tool_definition, go_home_callback)

    info = QLabel(
      "This is a placeholder page for the future bulk file renaming tool.\n\n"
      "Later, this page can contain:\n"
      "- folder selection\n"
      "- rename pattern rules\n"
      "- preview of name changes\n"
      "- conflict detection\n"
      "- execute and rollback options"
    )
    info.setWordWrap(True)

    self.content_layout.addWidget(info)