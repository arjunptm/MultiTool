from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
  QMainWindow,
  QStackedWidget,
  QWidget,
  QVBoxLayout,
  QLabel,
)

from app.core.tool_registry import get_registered_tools
from app.ui.home_page import HomePage


class MainWindow(QMainWindow):
  """
  Main application window.

  Responsibilities:
  - Own the stacked page container
  - Create and keep references to all pages
  - Handle navigation between Home and tool pages
  """

  def __init__(self):
    super().__init__()

    self.setWindowTitle("MultiTool")
    self.resize(1000, 700)

    self._stack = QStackedWidget()
    self.setCentralWidget(self._stack)

    self._pages = {}
    self._tool_pages = {}

    self._build_pages()

  def _build_pages(self) -> None:
    """
    Create the home page and all registered tool pages.
    """
    self.home_page = HomePage(
      tools=get_registered_tools(),
      open_tool_callback=self.open_tool,
    )
    self._pages["home"] = self.home_page
    self._stack.addWidget(self.home_page)

    for tool in get_registered_tools():
      page = tool.page_class(
        tool_definition=tool,
        go_home_callback=self.go_home,
      )
      self._tool_pages[tool.tool_id] = page
      self._stack.addWidget(page)

    self.go_home()

  def go_home(self) -> None:
    """
    Navigate back to the Home screen.
    """
    self._stack.setCurrentWidget(self.home_page)

  def open_tool(self, tool_id: str) -> None:
    """
    Navigate to a specific tool page by its registered id.
    """
    page = self._tool_pages.get(tool_id)
    if page is None:
      fallback = self._build_missing_page(tool_id)
      self._stack.addWidget(fallback)
      self._stack.setCurrentWidget(fallback)
      return

    self._stack.setCurrentWidget(page)

  def _build_missing_page(self, tool_id: str) -> QWidget:
    """
    Fallback page in case a tool id is missing or misconfigured.
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(40, 40, 40, 40)
    layout.setSpacing(16)

    title = QLabel("Tool Not Found")
    title.setObjectName("pageTitle")

    body = QLabel(
      f"No page was found for tool id: {tool_id}\n\n"
      "This usually means the registry entry is incorrect."
    )
    body.setAlignment(Qt.AlignmentFlag.AlignTop)
    body.setWordWrap(True)

    layout.addWidget(title)
    layout.addWidget(body)

    return page