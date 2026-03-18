from PySide6.QtWidgets import (
  QWidget,
  QVBoxLayout,
  QHBoxLayout,
  QLabel,
  QPushButton,
  QFrame,
)


class ToolPageBase(QWidget):
  """
  Base class for all tool pages.

  Every tool page gets:
  - title
  - description
  - back button
  - content container

  Subclasses can populate self.content_layout with tool-specific widgets.
  """

  def __init__(self, tool_definition, go_home_callback):
    super().__init__()
    self.tool_definition = tool_definition
    self.go_home_callback = go_home_callback

    self._build_shell()

  def _build_shell(self) -> None:
    root = QVBoxLayout(self)
    root.setContentsMargins(24, 24, 24, 24)
    root.setSpacing(16)

    top_bar = QHBoxLayout()
    top_bar.addStretch()

    back_button = QPushButton("Back to Home")
    back_button.setObjectName("secondaryButton")
    back_button.clicked.connect(self.go_home_callback)
    top_bar.addWidget(back_button)

    title = QLabel(self.tool_definition.name)
    title.setObjectName("pageTitle")

    subtitle = QLabel(self.tool_definition.description)
    subtitle.setObjectName("pageSubtitle")
    subtitle.setWordWrap(True)

    content_frame = QFrame()
    content_frame.setObjectName("toolCard")
    self.content_layout = QVBoxLayout(content_frame)
    self.content_layout.setContentsMargins(20, 20, 20, 20)
    self.content_layout.setSpacing(12)

    root.addLayout(top_bar)
    root.addWidget(title)
    root.addWidget(subtitle)
    root.addWidget(content_frame)
    root.addStretch()