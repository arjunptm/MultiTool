from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
  QFrame,
  QHBoxLayout,
  QLabel,
  QListWidget,
  QListWidgetItem,
  QPushButton,
  QVBoxLayout,
  QWidget,
)


class ReorderableFileListWidget(QListWidget):
  """
  Generic file list widget for tools that work with ordered files.

  Supports:
  - single selection
  - drag-and-drop reordering
  - storing full file path in UserRole
  """

  def __init__(self, minimum_width: int = 320):
    super().__init__()

    self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
    self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
    self.setDefaultDropAction(Qt.DropAction.MoveAction)
    self.setAlternatingRowColors(True)
    self.setMinimumWidth(minimum_width)

  def add_file_item(self, file_path: str, label: str | None = None) -> None:
    path = Path(file_path)

    item = QListWidgetItem(label or path.name)
    item.setData(Qt.ItemDataRole.UserRole, str(path))
    item.setToolTip(str(path))
    self.addItem(item)

  def get_paths(self) -> list[str]:
    paths = []
    for index in range(self.count()):
      item = self.item(index)
      if item is not None:
        paths.append(item.data(Qt.ItemDataRole.UserRole))
    return paths

  def remove_selected(self) -> QListWidgetItem | None:
    current_row = self.currentRow()
    if current_row < 0:
      return None
    return self.takeItem(current_row)


class FileSelectionPanel(QFrame):
  """
  Reusable left-side file selection panel for tools.

  Provides:
  - title
  - subtitle
  - reorderable file list
  - Add / Remove buttons
  - count label

  Tool-specific pages remain responsible for:
  - opening file dialogs
  - validating file types
  - duplicate handling
  - any processing logic
  """

  add_requested = Signal()
  remove_requested = Signal()
  selection_changed = Signal(object, object)
  order_changed = Signal()

  def __init__(
    self,
    title: str,
    subtitle: str,
    add_button_text: str = "Add Files",
    remove_button_text: str = "Remove Selected",
    parent: QWidget | None = None,
  ):
    super().__init__(parent)

    self.setObjectName("toolCard")

    layout = QVBoxLayout(self)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")

    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("pageSubtitle")
    subtitle_label.setWordWrap(True)

    self.file_list = ReorderableFileListWidget()

    button_row = QHBoxLayout()

    self.add_button = QPushButton(add_button_text)
    self.remove_button = QPushButton(remove_button_text)
    self.remove_button.setObjectName("secondaryButton")

    button_row.addWidget(self.add_button)
    button_row.addWidget(self.remove_button)

    self.count_label = QLabel("0 files selected")
    self.count_label.setObjectName("pageSubtitle")

    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    layout.addWidget(self.file_list)
    layout.addLayout(button_row)
    layout.addWidget(self.count_label)

    self._connect_internal_signals()

  def _connect_internal_signals(self) -> None:
    self.add_button.clicked.connect(self.add_requested.emit)
    self.remove_button.clicked.connect(self.remove_requested.emit)
    self.file_list.currentItemChanged.connect(self.selection_changed.emit)
    self.file_list.model().rowsMoved.connect(self._emit_order_changed)

  def _emit_order_changed(self, parent, start, end, destination, row) -> None:
    del parent, start, end, destination, row
    self.order_changed.emit()

  def add_file_item(self, file_path: str, label: str | None = None) -> None:
    self.file_list.add_file_item(file_path, label)

  def get_paths(self) -> list[str]:
    return self.file_list.get_paths()

  def remove_selected(self) -> QListWidgetItem | None:
    return self.file_list.remove_selected()

  def set_current_row(self, row: int) -> None:
    self.file_list.setCurrentRow(row)

  def current_item(self) -> QListWidgetItem | None:
    return self.file_list.currentItem()

  def count(self) -> int:
    return self.file_list.count()

  def set_count_text(self, text: str) -> None:
    self.count_label.setText(text)