import math
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
  QColor,
  QImage,
  QMouseEvent,
  QPainter,
  QPen,
  QPixmap,
)
from PySide6.QtWidgets import (
  QDialog,
  QDialogButtonBox,
  QFileDialog,
  QFrame,
  QHBoxLayout,
  QLabel,
  QMessageBox,
  QPushButton,
  QSizePolicy,
  QSplitter,
  QVBoxLayout,
  QWidget,
)

from app.tools.sign_pdf.service import (
  SignaturePlacement,
  add_signature_to_pdf,
  get_pdf_page_count,
  render_pdf_page,
)
from app.ui.tool_page_base import ToolPageBase
from app.utils.file_dialogs import get_last_directory, get_open_file_names, get_save_file_name


class SignaturePad(QWidget):
  """
  Simple transparent drawing pad for creating a visual signature.
  """

  drawing_changed = Signal()

  def __init__(self):
    super().__init__()
    self.setMinimumSize(420, 180)
    self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    self.setCursor(Qt.CursorShape.CrossCursor)

    self._image = QImage(900, 320, QImage.Format.Format_ARGB32)
    self._image.fill(Qt.GlobalColor.transparent)
    self._last_point: QPoint | None = None
    self._has_drawing = False

  def clear(self) -> None:
    self._image.fill(Qt.GlobalColor.transparent)
    self._has_drawing = False
    self.update()
    self.drawing_changed.emit()

  def has_drawing(self) -> bool:
    return self._has_drawing

  def to_png_bytes(self) -> bytes:
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice

    if not self._has_drawing:
      return b""

    cropped = self._cropped_image()
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    cropped.save(buffer, "PNG")
    return bytes(byte_array)

  def paintEvent(self, event) -> None:
    del event
    painter = QPainter(self)
    painter.fillRect(self.rect(), QColor("#ffffff"))
    painter.setPen(QPen(QColor("#d1d5db"), 1, Qt.PenStyle.SolidLine))
    painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

    scaled = QPixmap.fromImage(self._image).scaled(
      self.size(),
      Qt.AspectRatioMode.IgnoreAspectRatio,
      Qt.TransformationMode.SmoothTransformation,
    )
    painter.drawPixmap(0, 0, scaled)

  def mousePressEvent(self, event: QMouseEvent) -> None:
    if event.button() != Qt.MouseButton.LeftButton:
      return
    self._last_point = self._image_point(event.position().toPoint())
    self._has_drawing = True

  def mouseMoveEvent(self, event: QMouseEvent) -> None:
    if self._last_point is None:
      return

    current_point = self._image_point(event.position().toPoint())

    painter = QPainter(self._image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#111827"), 5, Qt.PenStyle.SolidLine)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(self._last_point, current_point)
    painter.end()

    self._last_point = current_point
    self.update()
    self.drawing_changed.emit()

  def mouseReleaseEvent(self, event: QMouseEvent) -> None:
    if event.button() == Qt.MouseButton.LeftButton:
      self._last_point = None

  def _image_point(self, widget_point: QPoint) -> QPoint:
    x = round(widget_point.x() * self._image.width() / max(1, self.width()))
    y = round(widget_point.y() * self._image.height() / max(1, self.height()))
    return QPoint(x, y)

  def _cropped_image(self) -> QImage:
    bounds = QRect()

    for y in range(self._image.height()):
      for x in range(self._image.width()):
        if self._image.pixelColor(x, y).alpha() > 0:
          point_rect = QRect(x, y, 1, 1)
          bounds = point_rect if bounds.isNull() else bounds.united(point_rect)

    if bounds.isNull():
      return self._image

    padding = 16
    bounds = bounds.adjusted(-padding, -padding, padding, padding)
    bounds = bounds.intersected(self._image.rect())
    return self._image.copy(bounds)


class DrawSignatureDialog(QDialog):
  """
  Dialog for drawing a signature with the mouse.
  """

  def __init__(self, parent: QWidget | None = None):
    super().__init__(parent)
    self.setWindowTitle("Draw Signature")

    layout = QVBoxLayout(self)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel("Draw your signature")
    title.setObjectName("sectionTitle")

    self.pad = SignaturePad()

    button_row = QHBoxLayout()
    self.clear_button = QPushButton("Clear")
    self.clear_button.setObjectName("secondaryButton")
    button_row.addWidget(self.clear_button)
    button_row.addStretch()

    self.button_box = QDialogButtonBox(
      QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Use Signature")
    self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    layout.addWidget(title)
    layout.addWidget(self.pad)
    layout.addLayout(button_row)
    layout.addWidget(self.button_box)

    self.clear_button.clicked.connect(self.pad.clear)
    self.pad.drawing_changed.connect(self._update_ok_state)
    self.button_box.accepted.connect(self.accept)
    self.button_box.rejected.connect(self.reject)

  def signature_png_bytes(self) -> bytes:
    return self.pad.to_png_bytes()

  def _update_ok_state(self) -> None:
    self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
      self.pad.has_drawing()
    )


class PdfSignaturePreview(QWidget):
  """
  Single-page PDF preview with one draggable/resizable signature overlay.
  """

  placement_changed = Signal()

  def __init__(self):
    super().__init__()
    self.setMinimumSize(520, 620)
    self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    self.setMouseTracking(True)

    self._page_pixmap: QPixmap | None = None
    self._page_size = QSizeF(0, 0)
    self._signature_pixmap: QPixmap | None = None
    self._signature_rect = QRectF()
    self._signature_rotation = 0.0

    self._drag_mode: str | None = None
    self._last_mouse_position = QPoint()
    self._drag_start_rect = QRectF()
    self._drag_start_rotation = 0.0
    self._drag_start_angle = 0.0
    self._handle_size = 14
    self._rotate_handle_distance = 34

  def set_page(self, pixmap: QPixmap, pdf_width: float, pdf_height: float) -> None:
    self._page_pixmap = pixmap
    self._page_size = QSizeF(pdf_width, pdf_height)
    self.update()

  def clear_page(self) -> None:
    self._page_pixmap = None
    self._page_size = QSizeF(0, 0)
    self.update()

  def set_signature(
    self,
    pixmap: QPixmap,
    signature_placement: SignaturePlacement | None = None,
  ) -> None:
    self._signature_pixmap = pixmap
    if signature_placement is None:
      self._signature_rect = self._default_signature_rect(pixmap)
      self._signature_rotation = 0.0
    else:
      self._signature_rect = QRectF(
        signature_placement.x,
        signature_placement.y,
        signature_placement.width,
        signature_placement.height,
      )
      self._signature_rotation = signature_placement.rotation_degrees
      self._clamp_signature_rect()
    self.update()
    self.placement_changed.emit()

  def clear_signature(self) -> None:
    self._signature_pixmap = None
    self._signature_rect = QRectF()
    self._signature_rotation = 0.0
    self.update()
    self.placement_changed.emit()

  def has_signature(self) -> bool:
    return self._signature_pixmap is not None and not self._signature_rect.isNull()

  def signature_placement(self) -> SignaturePlacement:
    return SignaturePlacement(
      x=self._signature_rect.x(),
      y=self._signature_rect.y(),
      width=self._signature_rect.width(),
      height=self._signature_rect.height(),
      rotation_degrees=self._signature_rotation,
    )

  def paintEvent(self, event) -> None:
    del event
    painter = QPainter(self)
    painter.fillRect(self.rect(), QColor("#eef2f7"))

    if self._page_pixmap is None:
      painter.setPen(QColor("#4b5563"))
      painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Open a PDF to preview it.")
      return

    page_rect = self._display_page_rect()
    painter.fillRect(page_rect, QColor("#ffffff"))
    painter.drawPixmap(page_rect, self._page_pixmap)
    painter.setPen(QPen(QColor("#cbd5e1"), 1))
    painter.drawRect(page_rect.adjusted(0, 0, -1, -1))

    if self._signature_pixmap is not None and not self._signature_rect.isNull():
      signature_rect = self._pdf_rect_to_widget_rect(self._signature_rect)
      center = QPointF(signature_rect.center())

      painter.save()
      painter.translate(center)
      painter.rotate(self._signature_rotation)
      local_rect = QRectF(
        -signature_rect.width() / 2,
        -signature_rect.height() / 2,
        signature_rect.width(),
        signature_rect.height(),
      )
      painter.drawPixmap(local_rect.toRect(), self._signature_pixmap)

      selection_pen = QPen(QColor("#2563eb"), 2, Qt.PenStyle.DashLine)
      painter.setPen(selection_pen)
      painter.drawRect(local_rect)
      painter.restore()

      painter.setPen(QPen(QColor("#2563eb"), 1))
      painter.setBrush(QColor("#2563eb"))
      for handle_rect in self._handle_rects(signature_rect).values():
        painter.drawRect(handle_rect)

      rotate_center = self._rotate_handle_center(signature_rect)
      top_center = self._rotated_point(
        QPointF(signature_rect.center()),
        QPointF(signature_rect.center().x(), signature_rect.top()),
      )
      painter.drawLine(top_center, rotate_center)
      painter.setBrush(QColor("#ffffff"))
      painter.drawEllipse(rotate_center, self._handle_size / 2, self._handle_size / 2)

  def mousePressEvent(self, event: QMouseEvent) -> None:
    if event.button() != Qt.MouseButton.LeftButton or not self.has_signature():
      return

    signature_rect = self._pdf_rect_to_widget_rect(self._signature_rect)
    position = event.position().toPoint()

    handle = self._hit_test_handle(position, signature_rect)
    if handle is not None:
      self._drag_mode = handle
    elif self._point_is_inside_signature(position, signature_rect):
      self._drag_mode = "move"
    else:
      self._drag_mode = None
      return

    self._last_mouse_position = position
    self._drag_start_rect = QRectF(self._signature_rect)
    self._drag_start_rotation = self._signature_rotation
    self._drag_start_angle = self._angle_from_center(position, signature_rect)

  def mouseMoveEvent(self, event: QMouseEvent) -> None:
    position = event.position().toPoint()

    if self._drag_mode is None:
      self._update_cursor(position)
      return

    delta = position - self._last_mouse_position
    self._last_mouse_position = position

    scale = self._page_scale()
    if scale <= 0:
      return

    local_delta = self._widget_delta_to_signature_delta(delta, self._drag_start_rotation)
    pdf_delta_x = local_delta.x() / scale
    pdf_delta_y = local_delta.y() / scale

    if self._drag_mode == "move":
      self._signature_rect.translate(delta.x() / scale, delta.y() / scale)
    elif self._drag_mode == "left":
      self._resize_from_left(pdf_delta_x)
    elif self._drag_mode == "right":
      self._resize_from_right(pdf_delta_x)
    elif self._drag_mode == "top":
      self._resize_from_top(pdf_delta_y)
    elif self._drag_mode == "bottom":
      self._resize_from_bottom(pdf_delta_y)
    elif self._drag_mode == "scale":
      self._scale_from_bottom_right(pdf_delta_x, pdf_delta_y)
    elif self._drag_mode == "rotate":
      current_angle = self._angle_from_center(position, self._pdf_rect_to_widget_rect(self._signature_rect))
      self._signature_rotation = self._normalize_rotation(
        self._drag_start_rotation + current_angle - self._drag_start_angle
      )

    self._clamp_signature_rect()
    self.update()
    self.placement_changed.emit()

  def mouseReleaseEvent(self, event: QMouseEvent) -> None:
    if event.button() == Qt.MouseButton.LeftButton:
      self._drag_mode = None

  def _default_signature_rect(self, pixmap: QPixmap) -> QRectF:
    if self._page_size.isEmpty():
      return QRectF()

    width = self._page_size.width() * 0.32
    aspect_ratio = pixmap.height() / max(1, pixmap.width())
    height = width * aspect_ratio

    max_height = self._page_size.height() * 0.16
    if height > max_height:
      height = max_height
      width = height / max(0.01, aspect_ratio)

    x = (self._page_size.width() - width) / 2
    y = self._page_size.height() * 0.72
    return QRectF(x, y, width, height)

  def _display_page_rect(self) -> QRect:
    if self._page_pixmap is None:
      return QRect()

    margin = 20
    available = self.rect().adjusted(margin, margin, -margin, -margin)
    page_ratio = self._page_size.width() / max(1, self._page_size.height())
    available_ratio = available.width() / max(1, available.height())

    if available_ratio > page_ratio:
      height = available.height()
      width = round(height * page_ratio)
    else:
      width = available.width()
      height = round(width / page_ratio)

    x = available.x() + (available.width() - width) // 2
    y = available.y() + (available.height() - height) // 2
    return QRect(x, y, width, height)

  def _page_scale(self) -> float:
    page_rect = self._display_page_rect()
    if self._page_size.width() <= 0:
      return 0
    return page_rect.width() / self._page_size.width()

  def _pdf_rect_to_widget_rect(self, pdf_rect: QRectF) -> QRect:
    page_rect = self._display_page_rect()
    scale = self._page_scale()
    return QRect(
      round(page_rect.x() + pdf_rect.x() * scale),
      round(page_rect.y() + pdf_rect.y() * scale),
      round(pdf_rect.width() * scale),
      round(pdf_rect.height() * scale),
    )

  def _resize_handle_rect(self, signature_rect: QRect) -> QRect:
    return self._handle_rects(signature_rect)["scale"]

  def _resize_signature(self, new_width: float, new_height: float) -> None:
    if self._signature_pixmap is None:
      return

    min_width = 36
    min_height = 18
    aspect_ratio = self._signature_pixmap.height() / max(1, self._signature_pixmap.width())

    width = max(min_width, new_width)
    height = max(min_height, new_height)

    if abs(new_width) >= abs(new_height):
      height = width * aspect_ratio
    else:
      width = height / max(0.01, aspect_ratio)

    self._signature_rect.setWidth(width)
    self._signature_rect.setHeight(height)

  def _resize_from_left(self, delta_x: float) -> None:
    new_x = self._signature_rect.x() + delta_x
    new_width = self._signature_rect.width() - delta_x
    if new_width < 36:
      return
    self._signature_rect.setX(new_x)
    self._signature_rect.setWidth(new_width)

  def _resize_from_right(self, delta_x: float) -> None:
    new_width = self._signature_rect.width() + delta_x
    if new_width < 36:
      return
    self._signature_rect.setWidth(new_width)

  def _resize_from_top(self, delta_y: float) -> None:
    new_y = self._signature_rect.y() + delta_y
    new_height = self._signature_rect.height() - delta_y
    if new_height < 18:
      return
    self._signature_rect.setY(new_y)
    self._signature_rect.setHeight(new_height)

  def _resize_from_bottom(self, delta_y: float) -> None:
    new_height = self._signature_rect.height() + delta_y
    if new_height < 18:
      return
    self._signature_rect.setHeight(new_height)

  def _scale_from_bottom_right(self, delta_x: float, delta_y: float) -> None:
    if self._drag_start_rect.isNull():
      return

    aspect_ratio = self._drag_start_rect.height() / max(1, self._drag_start_rect.width())
    width_change = delta_x
    height_change = delta_y / max(0.01, aspect_ratio)
    change = width_change if abs(width_change) >= abs(height_change) else height_change

    new_width = max(36, self._signature_rect.width() + change)
    new_height = max(18, new_width * aspect_ratio)
    self._signature_rect.setWidth(new_width)
    self._signature_rect.setHeight(new_height)

  def _clamp_signature_rect(self) -> None:
    if self._page_size.isEmpty() or self._signature_rect.isNull():
      return

    if self._signature_rect.width() > self._page_size.width():
      self._signature_rect.setWidth(self._page_size.width())
    if self._signature_rect.height() > self._page_size.height():
      self._signature_rect.setHeight(self._page_size.height())

    x = min(max(0, self._signature_rect.x()), self._page_size.width() - self._signature_rect.width())
    y = min(max(0, self._signature_rect.y()), self._page_size.height() - self._signature_rect.height())
    self._signature_rect.moveTo(x, y)

  def _update_cursor(self, position: QPoint) -> None:
    if not self.has_signature():
      self.unsetCursor()
      return

    signature_rect = self._pdf_rect_to_widget_rect(self._signature_rect)
    handle = self._hit_test_handle(position, signature_rect)
    if handle == "rotate":
      self.setCursor(Qt.CursorShape.CrossCursor)
    elif handle in {"left", "right"}:
      self.setCursor(Qt.CursorShape.SizeHorCursor)
    elif handle in {"top", "bottom"}:
      self.setCursor(Qt.CursorShape.SizeVerCursor)
    elif handle == "scale":
      self.setCursor(Qt.CursorShape.SizeFDiagCursor)
    elif self._point_is_inside_signature(position, signature_rect):
      self.setCursor(Qt.CursorShape.SizeAllCursor)
    else:
      self.unsetCursor()

  def _handle_rects(self, signature_rect: QRect) -> dict[str, QRect]:
    center = QPointF(signature_rect.center())
    handle_points = {
      "left": QPointF(signature_rect.left(), signature_rect.center().y()),
      "right": QPointF(signature_rect.right(), signature_rect.center().y()),
      "top": QPointF(signature_rect.center().x(), signature_rect.top()),
      "bottom": QPointF(signature_rect.center().x(), signature_rect.bottom()),
      "scale": QPointF(signature_rect.right(), signature_rect.bottom()),
    }

    handle_rects = {}
    for name, point in handle_points.items():
      rotated = self._rotated_point(center, point)
      handle_rects[name] = QRect(
        round(rotated.x() - self._handle_size / 2),
        round(rotated.y() - self._handle_size / 2),
        self._handle_size,
        self._handle_size,
      )
    return handle_rects

  def _hit_test_handle(self, position: QPoint, signature_rect: QRect) -> str | None:
    rotate_center = self._rotate_handle_center(signature_rect)
    rotate_rect = QRect(
      round(rotate_center.x() - self._handle_size / 2),
      round(rotate_center.y() - self._handle_size / 2),
      self._handle_size,
      self._handle_size,
    )
    if rotate_rect.contains(position):
      return "rotate"

    for name, handle_rect in self._handle_rects(signature_rect).items():
      if handle_rect.contains(position):
        return name

    return None

  def _point_is_inside_signature(self, position: QPoint, signature_rect: QRect) -> bool:
    center = QPointF(signature_rect.center())
    local = self._unrotated_point(center, QPointF(position.x(), position.y()))
    return QRectF(signature_rect).contains(local)

  def _rotate_handle_center(self, signature_rect: QRect) -> QPointF:
    center = QPointF(signature_rect.center())
    local_point = QPointF(
      signature_rect.center().x(),
      signature_rect.top() - self._rotate_handle_distance,
    )
    return self._rotated_point(center, local_point)

  def _rotated_point(self, center: QPointF, point: QPointF) -> QPointF:
    angle = math.radians(self._signature_rotation)
    dx = point.x() - center.x()
    dy = point.y() - center.y()
    return QPointF(
      center.x() + dx * math.cos(angle) - dy * math.sin(angle),
      center.y() + dx * math.sin(angle) + dy * math.cos(angle),
    )

  def _unrotated_point(self, center: QPointF, point: QPointF) -> QPointF:
    angle = math.radians(-self._signature_rotation)
    dx = point.x() - center.x()
    dy = point.y() - center.y()
    return QPointF(
      center.x() + dx * math.cos(angle) - dy * math.sin(angle),
      center.y() + dx * math.sin(angle) + dy * math.cos(angle),
    )

  def _widget_delta_to_signature_delta(self, delta: QPoint, rotation_degrees: float) -> QPointF:
    angle = math.radians(-rotation_degrees)
    return QPointF(
      delta.x() * math.cos(angle) - delta.y() * math.sin(angle),
      delta.x() * math.sin(angle) + delta.y() * math.cos(angle),
    )

  def _angle_from_center(self, position: QPoint, signature_rect: QRect) -> float:
    center = signature_rect.center()
    return math.degrees(math.atan2(position.y() - center.y(), position.x() - center.x()))

  def _normalize_rotation(self, rotation_degrees: float) -> float:
    rotation = rotation_degrees % 360
    if rotation > 180:
      rotation -= 360
    return rotation


class SignPdfPage(ToolPageBase):
  """
  Visual PDF signing tool.
  """

  def __init__(self, tool_definition, go_home_callback):
    super().__init__(tool_definition, go_home_callback)

    self.pdf_path: str | None = None
    self.page_count = 0
    self.current_page_index = 0
    self.signature_page_index: int | None = None
    self.signature_placement: SignaturePlacement | None = None
    self.signature_png_bytes = b""

    self._build_sign_ui()
    self._update_state()

  def _build_sign_ui(self) -> None:
    instructions = QLabel(
      "Open a PDF, choose a page, add a visual signature, drag or resize it on "
      "the page, then save a signed copy."
    )
    instructions.setWordWrap(True)
    self.content_layout.addWidget(instructions)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.setChildrenCollapsible(False)
    splitter.addWidget(self._build_controls_panel())
    splitter.addWidget(self._build_preview_panel())
    splitter.setSizes([320, 680])

    self.content_layout.addWidget(splitter)

  def _build_controls_panel(self) -> QWidget:
    panel = QFrame()
    panel.setObjectName("toolCard")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    file_title = QLabel("PDF")
    file_title.setObjectName("sectionTitle")
    self.pdf_name_label = QLabel("No PDF selected")
    self.pdf_name_label.setObjectName("pageSubtitle")
    self.pdf_name_label.setWordWrap(True)

    self.open_pdf_button = QPushButton("Open PDF")

    page_title = QLabel("Page")
    page_title.setObjectName("sectionTitle")
    page_row = QHBoxLayout()
    self.previous_button = QPushButton("Previous")
    self.previous_button.setObjectName("secondaryButton")
    self.next_button = QPushButton("Next")
    self.next_button.setObjectName("secondaryButton")
    page_row.addWidget(self.previous_button)
    page_row.addWidget(self.next_button)
    self.page_label = QLabel("Page 0 of 0")
    self.page_label.setObjectName("pageSubtitle")

    signature_title = QLabel("Signature")
    signature_title.setObjectName("sectionTitle")
    self.upload_signature_button = QPushButton("Upload Signature Image")
    self.draw_signature_button = QPushButton("Draw Signature")
    self.move_signature_button = QPushButton("Move to Current Page")
    self.move_signature_button.setObjectName("secondaryButton")
    self.clear_signature_button = QPushButton("Clear Signature")
    self.clear_signature_button.setObjectName("secondaryButton")
    self.signature_status_label = QLabel("No signature added")
    self.signature_status_label.setObjectName("pageSubtitle")
    self.signature_status_label.setWordWrap(True)

    self.save_button = QPushButton("Save Signed Copy")

    layout.addWidget(file_title)
    layout.addWidget(self.pdf_name_label)
    layout.addWidget(self.open_pdf_button)
    layout.addSpacing(10)
    layout.addWidget(page_title)
    layout.addLayout(page_row)
    layout.addWidget(self.page_label)
    layout.addSpacing(10)
    layout.addWidget(signature_title)
    layout.addWidget(self.upload_signature_button)
    layout.addWidget(self.draw_signature_button)
    layout.addWidget(self.move_signature_button)
    layout.addWidget(self.clear_signature_button)
    layout.addWidget(self.signature_status_label)
    layout.addStretch()
    layout.addWidget(self.save_button)

    self.open_pdf_button.clicked.connect(self._on_open_pdf_clicked)
    self.previous_button.clicked.connect(self._on_previous_page_clicked)
    self.next_button.clicked.connect(self._on_next_page_clicked)
    self.upload_signature_button.clicked.connect(self._on_upload_signature_clicked)
    self.draw_signature_button.clicked.connect(self._on_draw_signature_clicked)
    self.move_signature_button.clicked.connect(self._move_signature_to_current_page)
    self.clear_signature_button.clicked.connect(self._clear_signature)
    self.save_button.clicked.connect(self._on_save_clicked)

    return panel

  def _build_preview_panel(self) -> QWidget:
    panel = QFrame()
    panel.setObjectName("toolCard")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel("Preview")
    title.setObjectName("sectionTitle")
    self.preview_status_label = QLabel("Open a PDF to begin.")
    self.preview_status_label.setObjectName("pageSubtitle")
    self.preview_status_label.setWordWrap(True)

    self.preview = PdfSignaturePreview()
    self.preview.placement_changed.connect(self._on_preview_placement_changed)

    layout.addWidget(title)
    layout.addWidget(self.preview_status_label)
    layout.addWidget(self.preview, 1)
    return panel

  def _on_open_pdf_clicked(self) -> None:
    file_paths, _ = get_open_file_names(
      self,
      "Select PDF File",
      "PDF Files (*.pdf);;All Files (*.*)",
    )
    if not file_paths:
      return

    pdf_path = file_paths[0]

    try:
      page_count = get_pdf_page_count(pdf_path)
    except Exception as exc:
      QMessageBox.critical(
        self,
        "Could Not Open PDF",
        f"Failed to open the selected PDF.\n\n{exc}",
      )
      return

    if page_count <= 0:
      QMessageBox.warning(self, "Empty PDF", "The selected PDF has no pages.")
      return

    self.pdf_path = pdf_path
    self.page_count = page_count
    self.current_page_index = 0
    self.signature_page_index = None
    self.signature_placement = None
    self.signature_png_bytes = b""
    self.preview.clear_signature()

    self.pdf_name_label.setText(str(Path(pdf_path)))
    self._load_current_page()
    self._update_state()

  def _on_previous_page_clicked(self) -> None:
    if self.current_page_index <= 0:
      return
    self.current_page_index -= 1
    self._load_current_page()
    self._update_state()

  def _on_next_page_clicked(self) -> None:
    if self.current_page_index >= self.page_count - 1:
      return
    self.current_page_index += 1
    self._load_current_page()
    self._update_state()

  def _on_upload_signature_clicked(self) -> None:
    file_path, _ = QFileDialog.getOpenFileName(
      self,
      "Select Signature Image",
      get_last_directory(),
      "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)",
    )
    if not file_path:
      return

    pixmap = QPixmap(file_path)
    if pixmap.isNull():
      QMessageBox.warning(
        self,
        "Invalid Image",
        "The selected signature image could not be loaded.",
      )
      return

    self._set_signature(pixmap)

  def _on_draw_signature_clicked(self) -> None:
    dialog = DrawSignatureDialog(self)
    if dialog.exec() != QDialog.DialogCode.Accepted:
      return

    signature_bytes = dialog.signature_png_bytes()
    pixmap = QPixmap()
    pixmap.loadFromData(signature_bytes, "PNG")

    if pixmap.isNull():
      QMessageBox.warning(
        self,
        "Empty Signature",
        "No drawn signature was available to use.",
      )
      return

    self.signature_png_bytes = signature_bytes
    self.signature_page_index = self.current_page_index
    self.preview.set_signature(pixmap)
    self._update_state()

  def _move_signature_to_current_page(self) -> None:
    if not self.signature_png_bytes:
      return
    self.signature_page_index = self.current_page_index
    self.signature_placement = None
    self._show_or_hide_signature_for_current_page()
    self._update_state()

  def _clear_signature(self) -> None:
    self.signature_page_index = None
    self.signature_placement = None
    self.signature_png_bytes = b""
    self.preview.clear_signature()
    self._update_state()

  def _on_save_clicked(self) -> None:
    if self.pdf_path is None:
      QMessageBox.warning(self, "No PDF", "Open a PDF before saving.")
      return

    if not self.signature_png_bytes or self.signature_page_index is None:
      QMessageBox.warning(
        self,
        "No Signature",
        "Add a signature before saving.",
      )
      return

    if self.signature_placement is None:
      QMessageBox.warning(
        self,
        "No Signature Placement",
        "Place the signature on a page before saving.",
      )
      return

    suggested_name = f"{Path(self.pdf_path).stem}_signed.pdf"
    save_path, _ = get_save_file_name(
      self,
      "Save Signed PDF",
      suggested_name,
      "PDF Files (*.pdf)",
    )
    if not save_path:
      return

    if not save_path.lower().endswith(".pdf"):
      save_path += ".pdf"

    try:
      add_signature_to_pdf(
        input_pdf_path=self.pdf_path,
        output_pdf_path=save_path,
        page_index=self.signature_page_index,
        signature_png_bytes=self.signature_png_bytes,
        signature_placement=self.signature_placement,
      )
    except Exception as exc:
      QMessageBox.critical(
        self,
        "Save Failed",
        f"Failed to save the signed PDF.\n\n{exc}",
      )
      return

    QMessageBox.information(
      self,
      "Signed PDF Saved",
      f"Signed copy saved successfully:\n{save_path}",
    )

  def _set_signature(self, pixmap: QPixmap) -> None:
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.toImage().save(buffer, "PNG")

    self.signature_png_bytes = bytes(byte_array)
    self.signature_page_index = self.current_page_index
    self.signature_placement = None
    self.preview.set_signature(pixmap)
    self._update_state()

  def _load_current_page(self) -> None:
    if self.pdf_path is None:
      self.preview.clear_page()
      return

    try:
      rendered_page = render_pdf_page(self.pdf_path, self.current_page_index)
    except Exception as exc:
      self.preview.clear_page()
      QMessageBox.critical(
        self,
        "Preview Failed",
        f"Failed to render the selected page.\n\n{exc}",
      )
      return

    pixmap = QPixmap()
    pixmap.loadFromData(rendered_page.png_bytes, "PNG")
    self.preview.set_page(
      pixmap,
      rendered_page.pdf_width,
      rendered_page.pdf_height,
    )
    self._show_or_hide_signature_for_current_page()

  def _show_or_hide_signature_for_current_page(self) -> None:
    if not self.signature_png_bytes or self.signature_page_index != self.current_page_index:
      if self.signature_page_index != self.current_page_index:
        self.preview.clear_signature()
      return

    if not self.preview.has_signature():
      pixmap = QPixmap()
      pixmap.loadFromData(self.signature_png_bytes, "PNG")
      if not pixmap.isNull():
        self.preview.set_signature(pixmap, self.signature_placement)

  def _update_state(self) -> None:
    has_pdf = self.pdf_path is not None
    has_signature = bool(self.signature_png_bytes)

    self.previous_button.setEnabled(has_pdf and self.current_page_index > 0)
    self.next_button.setEnabled(has_pdf and self.current_page_index < self.page_count - 1)
    self.upload_signature_button.setEnabled(has_pdf)
    self.draw_signature_button.setEnabled(has_pdf)
    self.move_signature_button.setEnabled(has_pdf and has_signature)
    self.clear_signature_button.setEnabled(has_signature)
    self.save_button.setEnabled(has_pdf and has_signature)

    if has_pdf:
      self.page_label.setText(f"Page {self.current_page_index + 1} of {self.page_count}")
      self.preview_status_label.setText(
        "Drag the signature to move it. Use edge handles to stretch, the corner to scale, and the top handle to rotate."
      )
    else:
      self.page_label.setText("Page 0 of 0")
      self.preview_status_label.setText("Open a PDF to begin.")

    self._update_signature_status()

  def _on_preview_placement_changed(self) -> None:
    if (
      self.signature_png_bytes
      and self.signature_page_index == self.current_page_index
      and self.preview.has_signature()
    ):
      self.signature_placement = self.preview.signature_placement()

    self._update_signature_status()

  def _update_signature_status(self) -> None:
    if not self.signature_png_bytes or self.signature_page_index is None:
      self.signature_status_label.setText("No signature added")
      return

    page_number = self.signature_page_index + 1
    if self.signature_page_index == self.current_page_index:
      rotation = 0
      if self.signature_placement is not None:
        rotation = round(self.signature_placement.rotation_degrees)
      self.signature_status_label.setText(
        f"Signature placed on page {page_number}. Rotation: {rotation} degrees."
      )
    else:
      self.signature_status_label.setText(
        f"Signature is placed on page {page_number}. Navigate there to adjust it."
      )
