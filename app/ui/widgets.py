from PySide6.QtWidgets import (
  QFrame,
  QVBoxLayout,
  QLabel,
  QPushButton,
  QSizePolicy,
)


class ToolCard(QFrame):
  """
  Simple reusable card widget for the Home page.

  Each card displays:
  - tool name
  - category
  - description
  - open button
  """

  def __init__(self, name: str, category: str, description: str, open_callback):
    super().__init__()
    self.setObjectName("toolCard")

    layout = QVBoxLayout(self)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(8)

    title = QLabel(name)
    title.setObjectName("sectionTitle")

    category_label = QLabel(f"Category: {category}")
    category_label.setObjectName("pageSubtitle")

    description_label = QLabel(description)
    description_label.setWordWrap(True)

    open_button = QPushButton("Open")
    open_button.clicked.connect(open_callback)
    open_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    layout.addWidget(title)
    layout.addWidget(category_label)
    layout.addWidget(description_label)
    layout.addWidget(open_button)
    layout.addStretch()