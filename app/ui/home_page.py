from collections import defaultdict

from PySide6.QtWidgets import (
  QWidget,
  QVBoxLayout,
  QLabel,
  QScrollArea,
  QGridLayout,
  QFrame,
)

from app.ui.widgets import ToolCard


class HomePage(QWidget):
  """
  Home page listing all registered tools.

  It does not know how tools work internally.
  It only displays metadata and calls the provided open callback.
  """

  def __init__(self, tools, open_tool_callback):
    super().__init__()
    self.tools = tools
    self.open_tool_callback = open_tool_callback

    self._build_ui()

  def _build_ui(self) -> None:
    outer_layout = QVBoxLayout(self)
    outer_layout.setContentsMargins(24, 24, 24, 24)
    outer_layout.setSpacing(16)

    header = QLabel("MultiTool")
    header.setObjectName("appHeader")

    subtitle = QLabel(
      "A desktop utility suite framework. Choose a tool below."
    )
    subtitle.setObjectName("pageSubtitle")

    outer_layout.addWidget(header)
    outer_layout.addWidget(subtitle)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)

    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 8, 0, 8)
    content_layout.setSpacing(24)

    grouped_tools = defaultdict(list)
    for tool in self.tools:
      grouped_tools[tool.category].append(tool)

    for category, tools_in_category in grouped_tools.items():
      section = self._build_category_section(category, tools_in_category)
      content_layout.addWidget(section)

    content_layout.addStretch()
    scroll.setWidget(content)

    outer_layout.addWidget(scroll)

  def _build_category_section(self, category: str, tools) -> QWidget:
    section = QFrame()
    layout = QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)

    title = QLabel(category)
    title.setObjectName("sectionTitle")
    layout.addWidget(title)

    grid = QGridLayout()
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(16)

    for index, tool in enumerate(tools):
      row = index // 2
      col = index % 2

      card = ToolCard(
        name=tool.name,
        category=tool.category,
        description=tool.description,
        open_callback=lambda checked=False, tool_id=tool.tool_id: self.open_tool_callback(tool_id),
      )
      grid.addWidget(card, row, col)

    layout.addLayout(grid)
    return section