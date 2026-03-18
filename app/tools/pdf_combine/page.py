import os
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
  QFrame,
  QHBoxLayout,
  QLabel,
  QMenu,
  QMessageBox,
  QSplitter,
  QToolButton,
  QVBoxLayout,
  QWidget,
)

from app.tools.pdf_combine.service import (
  combine_pdfs,
  flatten_and_combine_pdfs,
)
from app.ui.file_widgets import FileSelectionPanel
from app.ui.tool_page_base import ToolPageBase
from app.utils.file_dialogs import get_open_file_names, get_save_file_name


@dataclass(frozen=True)
class CombineMode:
  """
  Metadata for a combine mode.

  This keeps the UI scalable:
  - menu label
  - button label
  - description text
  - whether the mode uses raster flattening
  """
  mode_id: str
  menu_label: str
  button_label: str
  description: str
  flatten: bool = False


class PdfCombinePage(ToolPageBase):
  """
  PDF combine tool page.

  Features:
  - Add multiple PDFs
  - Append more files later
  - Remove selected file
  - Drag to reorder files
  - Preview selected PDF
  - Combine modes via split action button
  - Description updates automatically based on selected mode
  """

  def __init__(self, tool_definition, go_home_callback):
    super().__init__(tool_definition, go_home_callback)

    self.pdf_document = QPdfDocument(self)
    self._known_files = set()

    self.combine_modes = self._build_combine_modes()
    self._current_mode_id = "combine"

    self._build_pdf_ui()
    self._connect_signals()
    self._apply_current_mode()

  def _build_combine_modes(self) -> dict[str, CombineMode]:
    """
    Central place to define available combine modes.

    Add future modes here and the UI will scale naturally.
    """
    return {
      "combine": CombineMode(
        mode_id="combine",
        menu_label="Combine",
        button_label="Combine",
        description=(
          "Standard combine mode. Merges the selected PDFs in the listed order "
          "while preserving the original PDF structure as much as possible."
        ),
        flatten=False,
      ),
      "flatten_and_combine": CombineMode(
        mode_id="flatten_and_combine",
        menu_label="Flatten and Combine",
        button_label="Flatten and Combine",
        description=(
          "Raster flatten mode. Each page is rendered visually and then combined "
          "into a new PDF. This is useful when you want to lock in visible form "
          "field values and avoid viewer compatibility issues, but text may no "
          "longer remain selectable or searchable."
        ),
        flatten=True,
      ),
    }

  def _build_pdf_ui(self) -> None:
    instructions = QLabel(
      "Add PDF files, reorder them by dragging in the left panel, preview the "
      "selected file on the right, and then combine them in the shown order."
    )
    instructions.setWordWrap(True)

    self.content_layout.addWidget(instructions)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.setChildrenCollapsible(False)

    left_panel = self._build_left_panel()
    right_panel = self._build_right_panel()

    splitter.addWidget(left_panel)
    splitter.addWidget(right_panel)
    splitter.setSizes([360, 640])

    self.content_layout.addWidget(splitter)

    bottom_row = QHBoxLayout()
    bottom_row.setSpacing(12)

    self.mode_description_label = QLabel("")
    self.mode_description_label.setObjectName("pageSubtitle")
    self.mode_description_label.setWordWrap(True)

    bottom_row.addWidget(self.mode_description_label, 1)

    self.combine_button = QToolButton()
    self.combine_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

    self.combine_menu = QMenu(self)
    self._mode_actions = {}

    for mode in self.combine_modes.values():
      action = QAction(mode.menu_label, self)
      action.triggered.connect(
        lambda checked=False, mode_id=mode.mode_id: self._set_current_mode(mode_id)
      )
      self.combine_menu.addAction(action)
      self._mode_actions[mode.mode_id] = action

    self.combine_button.setMenu(self.combine_menu)

    bottom_row.addWidget(self.combine_button, 0)

    self.content_layout.addLayout(bottom_row)

  def _build_left_panel(self) -> QWidget:
    self.file_panel = FileSelectionPanel(
      title="Selected PDF Files",
      subtitle="Drag files to reorder them. Top goes first in the final combined PDF.",
      add_button_text="Add Files",
      remove_button_text="Remove Selected",
    )
    return self.file_panel

  def _build_right_panel(self) -> QWidget:
    panel = QFrame()
    panel.setObjectName("toolCard")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel("Preview")
    title.setObjectName("sectionTitle")

    self.preview_name_label = QLabel("No file selected")
    self.preview_name_label.setObjectName("pageSubtitle")
    self.preview_name_label.setWordWrap(True)

    self.preview_path_label = QLabel("")
    self.preview_path_label.setObjectName("pageSubtitle")
    self.preview_path_label.setWordWrap(True)

    self.pdf_view = QPdfView()
    self.pdf_view.setDocument(self.pdf_document)
    self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
    self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    layout.addWidget(title)
    layout.addWidget(self.preview_name_label)
    layout.addWidget(self.preview_path_label, 0)
    layout.addWidget(self.pdf_view, 1)

    return panel

  def _connect_signals(self) -> None:
    self.file_panel.add_requested.connect(self._on_add_files_clicked)
    self.file_panel.remove_requested.connect(self._on_remove_selected_clicked)
    self.combine_button.clicked.connect(self._on_primary_combine_clicked)

    self.file_panel.selection_changed.connect(self._on_current_item_changed)
    self.file_panel.order_changed.connect(self._on_rows_moved)

    delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.file_panel.file_list)
    delete_shortcut.activated.connect(self._on_remove_selected_clicked)

  def _set_current_mode(self, mode_id: str) -> None:
    if mode_id not in self.combine_modes:
      return

    self._current_mode_id = mode_id
    self._apply_current_mode()

  def _apply_current_mode(self) -> None:
    """
    Apply the currently selected mode to the UI.

    This is the main scaling hook for future modes.
    """
    mode = self.combine_modes[self._current_mode_id]

    self.combine_button.setText(mode.button_label)
    self.mode_description_label.setText(f"Selected mode: {mode.description}")

    for current_mode_id, action in self._mode_actions.items():
      action.setCheckable(True)
      action.setChecked(current_mode_id == self._current_mode_id)

  def _on_primary_combine_clicked(self) -> None:
    mode = self.combine_modes[self._current_mode_id]
    self._on_combine_clicked(mode)

  def _on_add_files_clicked(self) -> None:
    file_paths, _ = get_open_file_names(
      self,
      "Select PDF Files",
      "PDF Files (*.pdf);;All Files (*.*)",
    )

    if not file_paths:
      return

    added_count = 0
    duplicate_count = 0

    for file_path in file_paths:
      normalized = self._normalize_path(file_path)
      if normalized in self._known_files:
        duplicate_count += 1
        continue

      self._known_files.add(normalized)
      self._add_file_item(file_path)
      added_count += 1

    self._update_file_count_label()

    if self.file_panel.count() > 0 and self.file_panel.current_item() is None:
      self.file_panel.set_current_row(0)

    if duplicate_count > 0:
      QMessageBox.information(
        self,
        "Some Files Skipped",
        f"Added {added_count} file(s).\n"
        f"Skipped {duplicate_count} duplicate file(s) that were already in the list.",
      )

  def _add_file_item(self, file_path: str) -> None:
    self.file_panel.add_file_item(file_path)

  def _on_remove_selected_clicked(self) -> None:
    current_row = self.file_panel.file_list.currentRow()
    if current_row < 0:
      QMessageBox.information(
        self,
        "No Selection",
        "Select a file in the list to remove it.",
      )
      return

    item = self.file_panel.remove_selected()
    if item is None:
      return

    removed_path = item.data(Qt.ItemDataRole.UserRole)
    normalized = self._normalize_path(removed_path)
    self._known_files.discard(normalized)

    del item

    self._update_file_count_label()

    if self.file_panel.count() == 0:
      self._clear_preview()
    else:
      new_row = min(current_row, self.file_panel.count() - 1)
      self.file_panel.set_current_row(new_row)

  def _on_current_item_changed(self, current, previous) -> None:
    del previous

    if current is None:
      self._clear_preview()
      return

    pdf_path = current.data(Qt.ItemDataRole.UserRole)
    self._load_preview(pdf_path)

  def _on_rows_moved(self) -> None:
    self._update_file_count_label()

  def _load_preview(self, pdf_path: str) -> None:
    self.preview_name_label.setText(Path(pdf_path).name)
    self.preview_path_label.setText(pdf_path)

    self.pdf_document.close()
    load_result = self.pdf_document.load(pdf_path)

    if load_result != QPdfDocument.Error.None_:
      self.preview_name_label.setText("Preview unavailable")
      self.preview_path_label.setText(
        f"Could not load preview for:\n{pdf_path}"
      )
      return

    self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
    self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

  def _clear_preview(self) -> None:
    self.pdf_document.close()
    self.preview_name_label.setText("No file selected")
    self.preview_path_label.setText("")

  def _on_combine_clicked(self, mode: CombineMode) -> None:
    ordered_paths = self.file_panel.get_paths()

    if not ordered_paths:
      QMessageBox.warning(
        self,
        "No Files",
        "Add at least one PDF file before combining.",
      )
      return

    if len(ordered_paths) == 1:
      response = QMessageBox.question(
        self,
        "Only One File",
        "Only one PDF is in the list.\n\n"
        "Do you still want to save an output file?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
      )
      if response != QMessageBox.StandardButton.Yes:
        return

    if mode.flatten:
      proceed = QMessageBox.question(
        self,
        mode.menu_label,
        "This mode will raster-flatten pages into a non-editable visual form.\n\n"
        "This is useful for locking in visible form-field values, but text may "
        "no longer be selectable/searchable and file size may increase.\n\n"
        "Continue?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
      )
      if proceed != QMessageBox.StandardButton.Yes:
        return

    suggested_name = self._build_default_output_name(
      ordered_paths,
      mode_id=mode.mode_id,
    )

    save_path, _ = get_save_file_name(
      self,
      "Save Output PDF",
      suggested_name,
      "PDF Files (*.pdf)",
    )

    if not save_path:
      return

    if not save_path.lower().endswith(".pdf"):
      save_path += ".pdf"

    try:
      if mode.flatten:
        flatten_and_combine_pdfs(ordered_paths, save_path)
      else:
        combine_pdfs(ordered_paths, save_path)
    except Exception as exc:
      QMessageBox.critical(
        self,
        "Combine Failed",
        f"Failed to create output PDF.\n\n{exc}",
      )
      return

    QMessageBox.information(
      self,
      "Output Saved",
      f"{mode.menu_label} completed successfully:\n{save_path}",
    )

  def _update_file_count_label(self) -> None:
    count = self.file_panel.count()
    suffix = "file" if count == 1 else "files"
    self.file_panel.set_count_text(f"{count} {suffix} selected")

  def _build_default_output_name(self, ordered_paths: list[str], mode_id: str) -> str:
    if not ordered_paths:
      return "combined.pdf"

    first_name = Path(ordered_paths[0]).stem

    suffix_map = {
      "combine": "_combined",
      "flatten_and_combine": "_flattened_combined",
    }
    suffix = suffix_map.get(mode_id, "_combined")

    return f"{first_name}{suffix}.pdf"

  def _normalize_path(self, file_path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(file_path)))