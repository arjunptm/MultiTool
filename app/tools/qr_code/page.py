import random
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
  QButtonGroup,
  QColorDialog,
  QComboBox,
  QFrame,
  QGridLayout,
  QHBoxLayout,
  QLabel,
  QLineEdit,
  QMessageBox,
  QPushButton,
  QScrollArea,
  QSizePolicy,
  QSlider,
  QSplitter,
  QTabWidget,
  QToolButton,
  QVBoxLayout,
  QWidget,
)

from app.tools.qr_code.service import (
  EYE_STYLES,
  FRAME_STYLES,
  MAX_LOGO_BYTES,
  MODULE_STYLES,
  QrCodeDesign,
  QrCodeError,
  contrast_ratio,
  render_qr_image,
  render_qr_png,
  render_qr_svg,
  suggested_filename,
  validate_design,
)
from app.ui.tool_page_base import ToolPageBase
from app.utils.file_dialogs import get_open_file_names, get_save_file_name


COLOR_PRESETS = {
  "Classic": ("#111827", "#ffffff"),
  "Slate": ("#334155", "#f8fafc"),
  "Navy": ("#172554", "#eff6ff"),
  "Teal": ("#115e59", "#f0fdfa"),
  "Forest": ("#166534", "#f0fdf4"),
  "Plum": ("#6b216b", "#fdf4ff"),
  "Burgundy": ("#7f1d1d", "#fff7ed"),
  "Orange": ("#9a3412", "#fff7ed"),
}

FRAME_LABELS = {
  "none": "None",
  "rounded_label": "Rounded Label",
  "badge": "Badge",
  "speech_bubble": "Speech Bubble",
  "ticket": "Ticket",
  "hanging_tag": "Hanging Tag",
  "poster": "Poster",
}

MODULE_LABELS = {
  "square": "Square",
  "rounded": "Rounded",
  "dots": "Dots",
  "gapped": "Gapped Square",
  "vertical": "Vertical Bars",
}

EYE_LABELS = {
  "square": "Square",
  "rounded": "Rounded",
  "circle": "Circle",
  "soft": "Soft Corner",
}


class LogoDropZone(QFrame):
  file_dropped = Signal(str)
  clicked = Signal()

  def __init__(self):
    super().__init__()
    self.setObjectName("uploadZone")
    self.setAcceptDrops(True)
    self.setCursor(Qt.CursorShape.PointingHandCursor)
    self.setMinimumHeight(104)

    layout = QVBoxLayout(self)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(5)

    self.title = QLabel("Drop a logo here or click to browse")
    self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.title.setObjectName("uploadTitle")

    self.detail = QLabel("PNG, JPG, JPEG, or BMP · 5 MB maximum")
    self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.detail.setObjectName("pageSubtitle")

    layout.addWidget(self.title)
    layout.addWidget(self.detail)

  def mousePressEvent(self, event) -> None:
    if event.button() == Qt.MouseButton.LeftButton:
      self.clicked.emit()
    super().mousePressEvent(event)

  def dragEnterEvent(self, event) -> None:
    if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
      event.acceptProposedAction()

  def dropEvent(self, event) -> None:
    urls = event.mimeData().urls()
    if len(urls) == 1 and urls[0].isLocalFile():
      self.file_dropped.emit(urls[0].toLocalFile())
      event.acceptProposedAction()


class QrCodePage(ToolPageBase):
  """Website QR code editor with live preview and PNG/SVG export."""

  def __init__(self, tool_definition, go_home_callback):
    super().__init__(tool_definition, go_home_callback)

    self.foreground_color = "#111827"
    self.background_color = "#ffffff"
    self.module_style = "square"
    self.eye_style = "square"
    self.frame_style = "none"
    self.logo_bytes = b""
    self.logo_name = ""
    self._preview_image = QImage()
    self._validated_design: QrCodeDesign | None = None

    self.preview_timer = QTimer(self)
    self.preview_timer.setSingleShot(True)
    self.preview_timer.setInterval(220)
    self.preview_timer.timeout.connect(self._refresh_preview)

    self._build_ui()
    self._reset_design()

  def _build_ui(self) -> None:
    self.splitter = QSplitter(Qt.Orientation.Horizontal)
    self.splitter.setChildrenCollapsible(False)

    editor_scroll = QScrollArea()
    editor_scroll.setWidgetResizable(True)
    editor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    editor_scroll.setMinimumWidth(420)

    editor = QWidget()
    editor_layout = QVBoxLayout(editor)
    editor_layout.setContentsMargins(4, 4, 8, 4)
    editor_layout.setSpacing(12)
    editor_layout.addWidget(self._build_url_card())
    editor_layout.addWidget(self._build_design_card())
    editor_layout.addLayout(self._build_design_actions())
    editor_layout.addStretch()
    editor_scroll.setWidget(editor)

    preview_panel = self._build_preview_panel()
    self.splitter.addWidget(editor_scroll)
    self.splitter.addWidget(preview_panel)
    self.splitter.setStretchFactor(0, 3)
    self.splitter.setStretchFactor(1, 2)
    self.splitter.setSizes([570, 390])

    self.content_layout.addWidget(self.splitter)

  def _build_url_card(self) -> QFrame:
    card = QFrame()
    card.setObjectName("qrSectionCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(8)

    title = QLabel("1  Add your website")
    title.setObjectName("sectionTitle")
    description = QLabel("Enter the page visitors should open after scanning.")
    description.setObjectName("pageSubtitle")

    input_row = QHBoxLayout()
    self.url_input = QLineEdit()
    self.url_input.setObjectName("qrInput")
    self.url_input.setPlaceholderText("https://example.com")
    self.url_input.setClearButtonEnabled(False)
    self.url_input.textChanged.connect(self._schedule_preview)

    paste_button = QPushButton("Paste")
    paste_button.setObjectName("secondaryButton")
    paste_button.clicked.connect(self._paste_url)
    clear_button = QPushButton("Clear")
    clear_button.setObjectName("secondaryButton")
    clear_button.clicked.connect(self.url_input.clear)

    input_row.addWidget(self.url_input, 1)
    input_row.addWidget(paste_button)
    input_row.addWidget(clear_button)

    self.url_error = QLabel("")
    self.url_error.setObjectName("inlineError")
    self.url_error.setWordWrap(True)
    self.url_error.hide()

    layout.addWidget(title)
    layout.addWidget(description)
    layout.addLayout(input_row)
    layout.addWidget(self.url_error)
    return card

  def _build_design_card(self) -> QFrame:
    card = QFrame()
    card.setObjectName("qrSectionCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(10)

    title = QLabel("2  Make it yours")
    title.setObjectName("sectionTitle")
    description = QLabel("Choose from scan-friendly designs. Every tile is a preview of the style.")
    description.setObjectName("pageSubtitle")
    description.setWordWrap(True)

    self.design_tabs = QTabWidget()
    self.design_tabs.setObjectName("qrDesignTabs")
    self.design_tabs.addTab(self._build_frames_tab(), "Frames")
    self.design_tabs.addTab(self._build_colors_tab(), "Colors")
    self.design_tabs.addTab(self._build_patterns_tab(), "Patterns")
    self.design_tabs.addTab(self._build_logo_tab(), "Logo")

    layout.addWidget(title)
    layout.addWidget(description)
    layout.addWidget(self.design_tabs)
    return card

  def _build_frames_tab(self) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(4, 12, 4, 4)
    layout.setSpacing(10)

    self.frame_group = QButtonGroup(self)
    self.frame_group.setExclusive(True)
    self.frame_buttons = {}
    grid = QGridLayout()
    grid.setSpacing(8)
    for index, style in enumerate(FRAME_STYLES):
      button = self._preset_button(FRAME_LABELS[style], self._design_thumbnail(frame_style=style))
      self.frame_group.addButton(button, index)
      self.frame_buttons[style] = button
      grid.addWidget(button, index // 3, index % 3)
    self.frame_group.idClicked.connect(self._frame_selected)

    cta_row = QHBoxLayout()
    cta_label = QLabel("Frame text")
    self.frame_text_input = QLineEdit("SCAN ME")
    self.frame_text_input.setObjectName("qrInput")
    self.frame_text_input.setMaxLength(40)
    self.frame_text_input.textChanged.connect(self._schedule_preview)
    cta_row.addWidget(cta_label)
    cta_row.addWidget(self.frame_text_input, 1)

    layout.addLayout(grid)
    layout.addLayout(cta_row)
    return tab

  def _build_colors_tab(self) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(4, 12, 4, 4)
    layout.setSpacing(10)

    self.color_group = QButtonGroup(self)
    self.color_group.setExclusive(True)
    self.color_buttons = {}
    grid = QGridLayout()
    grid.setSpacing(8)
    for index, (name, colors) in enumerate(COLOR_PRESETS.items()):
      button = self._preset_button(name, self._color_thumbnail(*colors))
      self.color_group.addButton(button, index)
      self.color_buttons[name] = button
      grid.addWidget(button, index // 3, index % 3)
    self.color_group.idClicked.connect(self._color_preset_selected)

    custom_title = QLabel("Custom colors")
    custom_title.setObjectName("miniSectionTitle")
    custom_row = QHBoxLayout()
    self.foreground_button = QPushButton("Foreground")
    self.foreground_button.setObjectName("colorButton")
    self.foreground_button.clicked.connect(lambda: self._choose_color("foreground"))
    self.background_button = QPushButton("Background")
    self.background_button.setObjectName("colorButton")
    self.background_button.clicked.connect(lambda: self._choose_color("background"))
    custom_row.addWidget(self.foreground_button)
    custom_row.addWidget(self.background_button)

    self.contrast_label = QLabel("")
    self.contrast_label.setObjectName("pageSubtitle")

    layout.addLayout(grid)
    layout.addWidget(custom_title)
    layout.addLayout(custom_row)
    layout.addWidget(self.contrast_label)
    return tab

  def _build_patterns_tab(self) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(4, 12, 4, 4)
    layout.setSpacing(10)

    module_title = QLabel("QR pattern")
    module_title.setObjectName("miniSectionTitle")
    self.module_group = QButtonGroup(self)
    self.module_group.setExclusive(True)
    self.module_buttons = {}
    module_grid = QGridLayout()
    module_grid.setSpacing(8)
    for index, style in enumerate(MODULE_STYLES):
      button = self._preset_button(MODULE_LABELS[style], self._design_thumbnail(module_style=style))
      self.module_group.addButton(button, index)
      self.module_buttons[style] = button
      module_grid.addWidget(button, index // 3, index % 3)
    self.module_group.idClicked.connect(self._module_selected)

    eye_title = QLabel("Finder eyes")
    eye_title.setObjectName("miniSectionTitle")
    self.eye_group = QButtonGroup(self)
    self.eye_group.setExclusive(True)
    self.eye_buttons = {}
    eye_grid = QGridLayout()
    eye_grid.setSpacing(8)
    for index, style in enumerate(EYE_STYLES):
      button = self._preset_button(EYE_LABELS[style], self._design_thumbnail(eye_style=style))
      self.eye_group.addButton(button, index)
      self.eye_buttons[style] = button
      eye_grid.addWidget(button, index // 3, index % 3)
    self.eye_group.idClicked.connect(self._eye_selected)

    layout.addWidget(module_title)
    layout.addLayout(module_grid)
    layout.addWidget(eye_title)
    layout.addLayout(eye_grid)
    return tab

  def _build_logo_tab(self) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(4, 12, 4, 4)
    layout.setSpacing(10)

    self.logo_drop_zone = LogoDropZone()
    self.logo_drop_zone.clicked.connect(self._browse_logo)
    self.logo_drop_zone.file_dropped.connect(self._load_logo)

    self.logo_preview = QLabel("No logo selected")
    self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.logo_preview.setMinimumHeight(80)
    self.logo_preview.setObjectName("logoPreview")

    size_row = QHBoxLayout()
    size_label = QLabel("Logo size")
    self.logo_size_slider = QSlider(Qt.Orientation.Horizontal)
    self.logo_size_slider.setRange(10, 18)
    self.logo_size_slider.setValue(16)
    self.logo_size_slider.valueChanged.connect(self._logo_size_changed)
    self.logo_size_value = QLabel("16%")
    self.logo_size_value.setMinimumWidth(36)
    size_row.addWidget(size_label)
    size_row.addWidget(self.logo_size_slider, 1)
    size_row.addWidget(self.logo_size_value)

    self.remove_logo_button = QPushButton("Remove Logo")
    self.remove_logo_button.setObjectName("secondaryButton")
    self.remove_logo_button.clicked.connect(self._remove_logo)

    note = QLabel("Logos are placed on a light backing plate and limited to 18% for scan reliability.")
    note.setObjectName("pageSubtitle")
    note.setWordWrap(True)

    layout.addWidget(self.logo_drop_zone)
    layout.addWidget(self.logo_preview)
    layout.addLayout(size_row)
    layout.addWidget(self.remove_logo_button)
    layout.addWidget(note)
    return tab

  def _build_design_actions(self) -> QHBoxLayout:
    row = QHBoxLayout()
    surprise_button = QPushButton("Surprise Me")
    surprise_button.clicked.connect(self._surprise_me)
    reset_button = QPushButton("Reset Design")
    reset_button.setObjectName("secondaryButton")
    reset_button.clicked.connect(self._reset_design)
    row.addWidget(surprise_button)
    row.addWidget(reset_button)
    row.addStretch()
    return row

  def _build_preview_panel(self) -> QFrame:
    panel = QFrame()
    panel.setObjectName("previewCard")
    panel.setMinimumWidth(320)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)

    title = QLabel("3  Preview and save")
    title.setObjectName("sectionTitle")

    self.preview_label = QLabel("Enter a website URL to begin")
    self.preview_label.setObjectName("qrPreview")
    self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.preview_label.setMinimumSize(280, 280)
    self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    self.safety_status = QLabel("Waiting for a website URL")
    self.safety_status.setObjectName("safetyNeutral")
    self.safety_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.safety_status.setWordWrap(True)

    output_row = QHBoxLayout()
    self.format_combo = QComboBox()
    self.format_combo.setObjectName("qrCombo")
    self.format_combo.addItems(["PNG", "SVG"])
    self._configure_combo_popup(self.format_combo)
    self.format_combo.currentTextChanged.connect(self._format_changed)
    self.size_combo = QComboBox()
    self.size_combo.setObjectName("qrCombo")
    self.size_combo.addItems(["512 px", "1024 px", "2048 px"])
    self._configure_combo_popup(self.size_combo)
    self.size_combo.setCurrentText("1024 px")
    output_row.addWidget(QLabel("Format"))
    output_row.addWidget(self.format_combo)
    output_row.addWidget(QLabel("Size"))
    output_row.addWidget(self.size_combo)

    self.save_button = QPushButton("Save QR Code")
    self.save_button.setObjectName("saveQrButton")
    self.save_button.setEnabled(False)
    self.save_button.clicked.connect(self._save_qr_code)

    layout.addWidget(title)
    layout.addWidget(self.preview_label, 1)
    layout.addWidget(self.safety_status)
    layout.addLayout(output_row)
    layout.addWidget(self.save_button)
    return panel

  def _preset_button(self, label: str, pixmap: QPixmap) -> QToolButton:
    button = QToolButton()
    button.setObjectName("presetTile")
    button.setCheckable(True)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
    button.setText(label)
    button.setIcon(QIcon(pixmap))
    button.setIconSize(QSize(72, 60))
    button.setMinimumSize(104, 92)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return button

  def _design_thumbnail(self, **changes) -> QPixmap:
    design_values = {
      "url": "https://example.com",
      "foreground_color": "#111827",
      "background_color": "#ffffff",
      "module_style": "square",
      "eye_style": "square",
      "frame_style": "none",
      "frame_text": "SCAN",
    }
    design_values.update(changes)
    image = render_qr_image(QrCodeDesign(**design_values), 144)
    return QPixmap.fromImage(image)

  def _color_thumbnail(self, foreground: str, background: str) -> QPixmap:
    pixmap = QPixmap(120, 76)
    pixmap.fill(QColor(background))
    painter = QPainter(pixmap)
    painter.fillRect(8, 8, 104, 60, QColor(foreground))
    painter.fillRect(28, 23, 22, 22, QColor(background))
    painter.fillRect(34, 29, 10, 10, QColor(foreground))
    painter.end()
    return pixmap

  def _paste_url(self) -> None:
    from PySide6.QtWidgets import QApplication

    self.url_input.setText(QApplication.clipboard().text().strip())

  def _schedule_preview(self) -> None:
    self.preview_timer.start()

  def _refresh_preview(self) -> None:
    value = self.url_input.text().strip()
    if not value:
      self._validated_design = None
      self._preview_image = QImage()
      self.preview_label.clear()
      self.preview_label.setText("Enter a website URL to begin")
      self.url_error.hide()
      self._set_safety_status("Waiting for a website URL", "neutral")
      self.save_button.setEnabled(False)
      return

    try:
      design = validate_design(self._current_design())
      image = render_qr_image(design, 900)
    except QrCodeError as exc:
      self._validated_design = None
      self._preview_image = QImage()
      self.preview_label.clear()
      self.preview_label.setText("Adjust the highlighted settings to preview")
      self.url_error.setText(str(exc))
      self.url_error.show()
      self._set_safety_status("Not ready to export", "error")
      self.save_button.setEnabled(False)
      return

    self._validated_design = design
    self._preview_image = image
    self.url_error.hide()
    self._update_preview_pixmap()
    ratio = contrast_ratio(design.foreground_color, design.background_color)
    self._set_safety_status(f"Ready to scan · {ratio:.1f}:1 color contrast · high error correction", "good")
    self.save_button.setEnabled(True)

  def _current_design(self) -> QrCodeDesign:
    return QrCodeDesign(
      url=self.url_input.text(),
      foreground_color=self.foreground_color,
      background_color=self.background_color,
      module_style=self.module_style,
      eye_style=self.eye_style,
      frame_style=self.frame_style,
      frame_text=self.frame_text_input.text(),
      logo_bytes=self.logo_bytes,
      logo_scale=self.logo_size_slider.value() / 100,
    )

  def _set_safety_status(self, text: str, state: str) -> None:
    names = {"good": "safetyGood", "error": "safetyError", "neutral": "safetyNeutral"}
    self.safety_status.setText(text)
    self.safety_status.setObjectName(names[state])
    self.safety_status.style().unpolish(self.safety_status)
    self.safety_status.style().polish(self.safety_status)

  def _update_preview_pixmap(self) -> None:
    if self._preview_image.isNull():
      return
    target = self.preview_label.size() - QSize(12, 12)
    pixmap = QPixmap.fromImage(self._preview_image).scaled(
      target,
      Qt.AspectRatioMode.KeepAspectRatio,
      Qt.TransformationMode.SmoothTransformation,
    )
    self.preview_label.setPixmap(pixmap)

  def _frame_selected(self, button_id: int) -> None:
    self.frame_style = FRAME_STYLES[button_id]
    self.frame_text_input.setEnabled(self.frame_style != "none")
    self._schedule_preview()

  def _color_preset_selected(self, button_id: int) -> None:
    name = tuple(COLOR_PRESETS)[button_id]
    self.foreground_color, self.background_color = COLOR_PRESETS[name]
    self._update_color_buttons()
    self._schedule_preview()

  def _module_selected(self, button_id: int) -> None:
    self.module_style = MODULE_STYLES[button_id]
    self._schedule_preview()

  def _eye_selected(self, button_id: int) -> None:
    self.eye_style = EYE_STYLES[button_id]
    self._schedule_preview()

  def _choose_color(self, target: str) -> None:
    current = self.foreground_color if target == "foreground" else self.background_color
    selected = QColorDialog.getColor(QColor(current), self, f"Choose {target} color")
    if not selected.isValid():
      return
    if target == "foreground":
      self.foreground_color = selected.name()
    else:
      self.background_color = selected.name()
    self._clear_button_group(self.color_group)
    self._update_color_buttons()
    self._schedule_preview()

  def _update_color_buttons(self) -> None:
    self.foreground_button.setStyleSheet(
      f"background: {self.foreground_color}; color: {_readable_text(self.foreground_color)};"
    )
    self.background_button.setStyleSheet(
      f"background: {self.background_color}; color: {_readable_text(self.background_color)}; border: 1px solid #cbd5e1;"
    )
    ratio = contrast_ratio(self.foreground_color, self.background_color)
    self.contrast_label.setText(f"Contrast: {ratio:.1f}:1 · minimum 4.5:1")

  def _browse_logo(self) -> None:
    paths, _ = get_open_file_names(
      self,
      "Choose QR Code Logo",
      "Logo Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)",
    )
    if paths:
      self._load_logo(paths[0])

  def _load_logo(self, file_path: str) -> None:
    path = Path(file_path)
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
      QMessageBox.warning(self, "Unsupported Logo", "Choose a PNG, JPG, JPEG, or BMP image.")
      return
    try:
      if path.stat().st_size > MAX_LOGO_BYTES:
        raise QrCodeError("Logo images must be 5 MB or smaller.")
      image_bytes = path.read_bytes()
    except (OSError, QrCodeError) as exc:
      QMessageBox.warning(self, "Could Not Load Logo", str(exc))
      return

    image = QImage.fromData(image_bytes)
    if image.isNull():
      QMessageBox.warning(self, "Could Not Load Logo", "The selected file is not a readable image.")
      return

    self.logo_bytes = image_bytes
    self.logo_name = path.name
    preview = QPixmap.fromImage(image).scaled(
      160,
      72,
      Qt.AspectRatioMode.KeepAspectRatio,
      Qt.TransformationMode.SmoothTransformation,
    )
    self.logo_preview.setPixmap(preview)
    self.logo_preview.setToolTip(path.name)
    self.logo_drop_zone.title.setText(path.name)
    self.logo_drop_zone.detail.setText("Logo ready · click or drop another image to replace it")
    self.remove_logo_button.setEnabled(True)
    self._schedule_preview()

  def _remove_logo(self) -> None:
    self.logo_bytes = b""
    self.logo_name = ""
    self.logo_preview.clear()
    self.logo_preview.setText("No logo selected")
    self.logo_preview.setToolTip("")
    self.logo_drop_zone.title.setText("Drop a logo here or click to browse")
    self.logo_drop_zone.detail.setText("PNG, JPG, JPEG, or BMP · 5 MB maximum")
    self.remove_logo_button.setEnabled(False)
    self._schedule_preview()

  def _logo_size_changed(self, value: int) -> None:
    self.logo_size_value.setText(f"{value}%")
    self._schedule_preview()

  def _reset_design(self) -> None:
    self.foreground_color, self.background_color = COLOR_PRESETS["Classic"]
    self.module_style = "square"
    self.eye_style = "square"
    self.frame_style = "none"
    self.frame_text_input.setText("SCAN ME")
    self.frame_text_input.setEnabled(False)
    self.logo_size_slider.setValue(16)
    self._remove_logo()
    self._select_button(self.color_buttons, "Classic")
    self._select_button(self.module_buttons, "square")
    self._select_button(self.eye_buttons, "square")
    self._select_button(self.frame_buttons, "none")
    self._update_color_buttons()
    self._schedule_preview()

  def _surprise_me(self) -> None:
    color_name = random.choice(tuple(COLOR_PRESETS))
    self.foreground_color, self.background_color = COLOR_PRESETS[color_name]
    self.module_style = random.choice(MODULE_STYLES)
    self.eye_style = random.choice(EYE_STYLES)
    self.frame_style = random.choice(FRAME_STYLES)
    self._select_button(self.color_buttons, color_name)
    self._select_button(self.module_buttons, self.module_style)
    self._select_button(self.eye_buttons, self.eye_style)
    self._select_button(self.frame_buttons, self.frame_style)
    self.frame_text_input.setEnabled(self.frame_style != "none")
    self._update_color_buttons()
    self._schedule_preview()

  def _select_button(self, buttons: dict[str, QToolButton], key: str) -> None:
    button = buttons[key]
    button.setChecked(True)

  def _clear_button_group(self, group: QButtonGroup) -> None:
    group.setExclusive(False)
    for button in group.buttons():
      button.setChecked(False)
    group.setExclusive(True)

  def _format_changed(self, value: str) -> None:
    self.size_combo.setEnabled(value == "PNG")

  def _configure_combo_popup(self, combo: QComboBox) -> None:
    popup = combo.view()
    popup.setObjectName("qrComboPopup")
    palette = popup.palette()
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#dbeafe"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1d4ed8"))
    popup.setPalette(palette)

  def _save_qr_code(self) -> None:
    try:
      design = validate_design(self._current_design())
    except QrCodeError as exc:
      QMessageBox.warning(self, "QR Code Not Ready", str(exc))
      return

    extension = self.format_combo.currentText().lower()
    suggested = suggested_filename(design.url, extension)
    file_filter = "PNG Images (*.png)" if extension == "png" else "SVG Images (*.svg)"
    save_path, _ = get_save_file_name(self, "Save QR Code", suggested, file_filter)
    if not save_path:
      return
    if not save_path.lower().endswith(f".{extension}"):
      save_path += f".{extension}"

    try:
      if extension == "png":
        size = int(self.size_combo.currentText().split()[0])
        output = render_qr_png(design, size)
      else:
        output = render_qr_svg(design)
      Path(save_path).write_bytes(output)
    except (OSError, QrCodeError) as exc:
      QMessageBox.critical(self, "Save Failed", f"Could not save the QR code.\n\n{exc}")
      return

    QMessageBox.information(self, "QR Code Saved", f"QR code saved successfully:\n{save_path}")

  def resizeEvent(self, event) -> None:
    super().resizeEvent(event)
    if hasattr(self, "splitter"):
      orientation = Qt.Orientation.Vertical if self.width() < 990 else Qt.Orientation.Horizontal
      if self.splitter.orientation() != orientation:
        self.splitter.setOrientation(orientation)
      self._update_preview_pixmap()


def _readable_text(color_value: str) -> str:
  color = QColor(color_value)
  luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
  return "#111827" if luminance > 160 else "#ffffff"
