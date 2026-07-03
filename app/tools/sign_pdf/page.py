import math
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
  QFont,
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
  QHBoxLayout,
  QInputDialog,
  QLabel,
  QListWidget,
  QListWidgetItem,
  QMessageBox,
  QPushButton,
  QScrollArea,
  QSizePolicy,
  QSplitter,
  QVBoxLayout,
  QWidget,
)

from app.tools.sign_pdf.service import (
  SignaturePlacement,
  SignatureStamp,
  TextStamp,
  add_signatures_to_pdf,
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
    self._strokes: list[list[QPoint]] = []
    self._current_stroke: list[QPoint] = []

  def clear(self) -> None:
    self._strokes = []
    self._current_stroke = []
    self._redraw_image()
    self.update()
    self.drawing_changed.emit()

  def undo_last_stroke(self) -> None:
    if not self._strokes:
      return

    self._strokes.pop()
    self._redraw_image()
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
    self._current_stroke = [self._last_point]
    self._has_drawing = True

  def mouseMoveEvent(self, event: QMouseEvent) -> None:
    if self._last_point is None:
      return

    current_point = self._image_point(event.position().toPoint())
    self._current_stroke.append(current_point)
    self._draw_line(self._last_point, current_point)

    self._last_point = current_point
    self.update()
    self.drawing_changed.emit()

  def mouseReleaseEvent(self, event: QMouseEvent) -> None:
    if event.button() == Qt.MouseButton.LeftButton:
      if self._current_stroke:
        self._strokes.append(self._current_stroke)
        self._current_stroke = []
      self._last_point = None

  def _image_point(self, widget_point: QPoint) -> QPoint:
    x = round(widget_point.x() * self._image.width() / max(1, self.width()))
    y = round(widget_point.y() * self._image.height() / max(1, self.height()))
    return QPoint(x, y)

  def _draw_line(self, start: QPoint, end: QPoint) -> None:
    painter = QPainter(self._image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#111827"), 5, Qt.PenStyle.SolidLine)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(start, end)
    painter.end()

  def _redraw_image(self) -> None:
    self._image.fill(Qt.GlobalColor.transparent)
    for stroke in self._strokes:
      for index in range(1, len(stroke)):
        self._draw_line(stroke[index - 1], stroke[index])
    self._has_drawing = bool(self._strokes)

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
    self.undo_button = QPushButton("Undo Stroke")
    self.undo_button.setObjectName("secondaryButton")
    self.clear_button = QPushButton("Clear")
    self.clear_button.setObjectName("secondaryButton")
    button_row.addWidget(self.undo_button)
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

    self.undo_button.clicked.connect(self.pad.undo_last_stroke)
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


@dataclass
class Signer:
  """
  A person who can provide and place their own visual signature.
  """
  signer_id: str
  name: str
  signature_png_bytes: bytes = b""
  signature_pixmap: QPixmap | None = None


@dataclass
class SignatureInstance:
  """
  One placed signature belonging to one signer.
  """
  instance_id: str
  signer_id: str
  page_index: int
  placement: SignaturePlacement


@dataclass
class TextInstance:
  """
  One placed text value, such as a date next to a signature line.
  """
  instance_id: str
  page_index: int
  text: str
  placement: SignaturePlacement
  font_size: float = 12


class PdfSignaturePreview(QWidget):
  """
  Single-page PDF preview with draggable/resizable signature and text overlays.
  """

  placement_changed = Signal()
  selected_instance_changed = Signal(str)

  def __init__(self):
    super().__init__()
    self.setMinimumSize(360, 280)
    self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    self.setMouseTracking(True)

    self._page_pixmap: QPixmap | None = None
    self._page_size = QSizeF(0, 0)
    self._placements: list[SignatureInstance] = []
    self._text_fields: list[TextInstance] = []
    self._signature_pixmaps: dict[str, QPixmap] = {}
    self._selected_instance_id: str | None = None
    self._active_instance: SignatureInstance | TextInstance | None = None

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

  def set_signatures(
    self,
    placements: list[SignatureInstance],
    text_fields: list[TextInstance],
    signature_pixmaps: dict[str, QPixmap],
    selected_instance_id: str | None,
  ) -> None:
    self._placements = placements
    self._text_fields = text_fields
    self._signature_pixmaps = signature_pixmaps
    self._selected_instance_id = selected_instance_id
    self._active_instance = self._selected_instance()
    self.update()

  def default_placement_for(self, pixmap: QPixmap) -> SignaturePlacement:
    rect = self._default_signature_rect(pixmap)
    return SignaturePlacement(
      x=rect.x(),
      y=rect.y(),
      width=rect.width(),
      height=rect.height(),
      rotation_degrees=0,
    )

  def default_text_placement(self) -> SignaturePlacement:
    if self._page_size.isEmpty():
      return SignaturePlacement(0, 0, 140, 24)

    width = min(160, self._page_size.width() * 0.32)
    height = 24
    x = (self._page_size.width() - width) / 2
    y = self._page_size.height() * 0.66
    return SignaturePlacement(x=x, y=y, width=width, height=height)

  def default_text_font_size(self) -> float:
    return self._font_size_for_text_height(self.default_text_placement().height)

  def selected_instance_id(self) -> str | None:
    return self._selected_instance_id

  def clear_signatures(self) -> None:
    self._placements = []
    self._text_fields = []
    self._signature_pixmaps = {}
    self._selected_instance_id = None
    self._active_instance = None
    self.update()

  def has_signatures(self) -> bool:
    return bool(self._placements or self._text_fields)

  def _selected_instance(self) -> SignatureInstance | TextInstance | None:
    for instance in self._placements:
      if instance.instance_id == self._selected_instance_id:
        return instance
    for instance in self._text_fields:
      if instance.instance_id == self._selected_instance_id:
        return instance
    return None

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
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(page_rect.adjusted(0, 0, -1, -1))

    for instance in self._placements:
      pixmap = self._signature_pixmaps.get(instance.signer_id)
      if pixmap is None:
        continue

      signature_rect = self._pdf_rect_to_widget_rect(self._placement_rect(instance))
      center = QPointF(signature_rect.center())
      is_selected = instance.instance_id == self._selected_instance_id

      painter.save()
      painter.translate(center)
      painter.rotate(instance.placement.rotation_degrees)
      local_rect = QRectF(
        -signature_rect.width() / 2,
        -signature_rect.height() / 2,
        signature_rect.width(),
        signature_rect.height(),
      )
      painter.drawPixmap(local_rect.toRect(), pixmap)

      border_color = QColor("#2563eb") if is_selected else QColor("#64748b")
      painter.setPen(QPen(border_color, 2, Qt.PenStyle.DashLine))
      painter.setBrush(Qt.BrushStyle.NoBrush)
      painter.drawRect(local_rect)
      painter.restore()

      if is_selected:
        painter.setPen(QPen(QColor("#2563eb"), 1))
        painter.setBrush(QColor("#2563eb"))
        for handle_rect in self._handle_rects(signature_rect, instance).values():
          painter.drawRect(handle_rect)

        rotate_center = self._rotate_handle_center(signature_rect, instance)
        top_center = self._rotated_point(
          QPointF(signature_rect.center()),
          QPointF(signature_rect.center().x(), signature_rect.top()),
          instance,
        )
        painter.drawLine(top_center, rotate_center)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(rotate_center, self._handle_size / 2, self._handle_size / 2)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    for instance in self._text_fields:
      text_rect = self._pdf_rect_to_widget_rect(self._placement_rect(instance))
      is_selected = instance.instance_id == self._selected_instance_id

      painter.save()
      painter.setPen(QColor("#111827"))
      font = QFont()
      font.setPixelSize(max(8, round(text_rect.height() * 0.68)))
      painter.setFont(font)
      painter.drawText(
        text_rect.adjusted(4, 0, -4, 0),
        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        instance.text,
      )
      border_color = QColor("#0891b2") if is_selected else QColor("#64748b")
      painter.setPen(QPen(border_color, 2, Qt.PenStyle.DashLine))
      painter.setBrush(Qt.BrushStyle.NoBrush)
      painter.drawRect(text_rect)
      painter.restore()

      if is_selected:
        painter.setPen(QPen(QColor("#0891b2"), 1))
        painter.setBrush(QColor("#0891b2"))
        for handle_rect in self._handle_rects(text_rect, instance).values():
          painter.drawRect(handle_rect)
        painter.setBrush(Qt.BrushStyle.NoBrush)

  def mousePressEvent(self, event: QMouseEvent) -> None:
    if event.button() != Qt.MouseButton.LeftButton or not self.has_signatures():
      return

    position = event.position().toPoint()

    selected = self._selected_instance()
    if selected is not None:
      signature_rect = self._pdf_rect_to_widget_rect(self._placement_rect(selected))
      handle = self._hit_test_handle(position, signature_rect, selected)
    else:
      handle = None

    if selected is not None and handle is not None:
      self._active_instance = selected
      self._drag_mode = handle
    else:
      self._active_instance = None
      self._drag_mode = None
      for instance in reversed(self._text_fields + self._placements):
        signature_rect = self._pdf_rect_to_widget_rect(self._placement_rect(instance))
        if self._point_is_inside_signature(position, signature_rect, instance):
          self._selected_instance_id = instance.instance_id
          self._active_instance = instance
          self._drag_mode = "move"
          self.selected_instance_changed.emit(instance.instance_id)
          break

      if self._active_instance is None or self._drag_mode is None:
        return

      signature_rect = self._pdf_rect_to_widget_rect(self._placement_rect(self._active_instance))

    self._last_mouse_position = position
    self._drag_start_rect = self._placement_rect(self._active_instance)
    self._drag_start_rotation = self._active_instance.placement.rotation_degrees
    self._drag_start_angle = self._angle_from_center(position, signature_rect)
    self.update()

  def mouseMoveEvent(self, event: QMouseEvent) -> None:
    position = event.position().toPoint()

    if self._drag_mode is None or self._active_instance is None:
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
    rect = self._placement_rect(self._active_instance)

    if self._drag_mode == "move":
      rect.translate(delta.x() / scale, delta.y() / scale)
    elif self._drag_mode == "left":
      rect = self._resize_from_left(rect, pdf_delta_x)
    elif self._drag_mode == "right":
      rect = self._resize_from_right(rect, pdf_delta_x)
    elif self._drag_mode == "top":
      rect = self._resize_from_top(rect, pdf_delta_y)
    elif self._drag_mode == "bottom":
      rect = self._resize_from_bottom(rect, pdf_delta_y)
    elif self._drag_mode == "scale":
      rect = self._scale_from_bottom_right(rect, pdf_delta_x, pdf_delta_y)
    elif self._drag_mode == "rotate":
      current_angle = self._angle_from_center(position, self._pdf_rect_to_widget_rect(rect))
      rotation = self._normalize_rotation(
        self._drag_start_rotation + current_angle - self._drag_start_angle
      )
      self._set_instance_placement(self._active_instance, rect, rotation)
      self.update()
      self.placement_changed.emit()
      return

    rect = self._clamped_rect(rect)
    self._set_instance_placement(
      self._active_instance,
      rect,
      self._active_instance.placement.rotation_degrees,
    )
    self.update()
    self.placement_changed.emit()

  def mouseReleaseEvent(self, event: QMouseEvent) -> None:
    if event.button() == Qt.MouseButton.LeftButton:
      self._drag_mode = None
      self._active_instance = None

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

  def _placement_rect(self, instance: SignatureInstance | TextInstance) -> QRectF:
    return QRectF(
      instance.placement.x,
      instance.placement.y,
      instance.placement.width,
      instance.placement.height,
    )

  def _set_instance_placement(
    self,
    instance: SignatureInstance | TextInstance,
    rect: QRectF,
    rotation_degrees: float,
  ) -> None:
    instance.placement = SignaturePlacement(
      x=rect.x(),
      y=rect.y(),
      width=rect.width(),
      height=rect.height(),
      rotation_degrees=rotation_degrees,
    )
    if isinstance(instance, TextInstance):
      instance.font_size = self._font_size_for_text_height(rect.height())

  def _font_size_for_text_height(self, height: float) -> float:
    return max(7, min(72, height * 0.68))

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

  def _resize_from_left(self, rect: QRectF, delta_x: float) -> QRectF:
    new_x = rect.x() + delta_x
    new_width = rect.width() - delta_x
    if new_width < 36:
      return rect
    rect.setX(new_x)
    rect.setWidth(new_width)
    return rect

  def _resize_from_right(self, rect: QRectF, delta_x: float) -> QRectF:
    new_width = rect.width() + delta_x
    if new_width < 36:
      return rect
    rect.setWidth(new_width)
    return rect

  def _resize_from_top(self, rect: QRectF, delta_y: float) -> QRectF:
    new_y = rect.y() + delta_y
    new_height = rect.height() - delta_y
    if new_height < 18:
      return rect
    rect.setY(new_y)
    rect.setHeight(new_height)
    return rect

  def _resize_from_bottom(self, rect: QRectF, delta_y: float) -> QRectF:
    new_height = rect.height() + delta_y
    if new_height < 18:
      return rect
    rect.setHeight(new_height)
    return rect

  def _scale_from_bottom_right(self, rect: QRectF, delta_x: float, delta_y: float) -> QRectF:
    if self._drag_start_rect.isNull():
      return rect

    aspect_ratio = self._drag_start_rect.height() / max(1, self._drag_start_rect.width())
    width_change = delta_x
    height_change = delta_y / max(0.01, aspect_ratio)
    change = width_change if abs(width_change) >= abs(height_change) else height_change

    new_width = max(36, rect.width() + change)
    new_height = max(18, new_width * aspect_ratio)
    rect.setWidth(new_width)
    rect.setHeight(new_height)
    return rect

  def _clamped_rect(self, rect: QRectF) -> QRectF:
    if self._page_size.isEmpty() or rect.isNull():
      return rect

    if rect.width() > self._page_size.width():
      rect.setWidth(self._page_size.width())
    if rect.height() > self._page_size.height():
      rect.setHeight(self._page_size.height())

    x = min(max(0, rect.x()), self._page_size.width() - rect.width())
    y = min(max(0, rect.y()), self._page_size.height() - rect.height())
    rect.moveTo(x, y)
    return rect

  def _update_cursor(self, position: QPoint) -> None:
    if not self.has_signatures():
      self.unsetCursor()
      return

    selected = self._selected_instance()
    if selected is None:
      self.unsetCursor()
      return

    signature_rect = self._pdf_rect_to_widget_rect(self._placement_rect(selected))
    handle = self._hit_test_handle(position, signature_rect, selected)
    if handle == "rotate":
      self.setCursor(Qt.CursorShape.CrossCursor)
    elif handle in {"left", "right"}:
      self.setCursor(Qt.CursorShape.SizeHorCursor)
    elif handle in {"top", "bottom"}:
      self.setCursor(Qt.CursorShape.SizeVerCursor)
    elif handle == "scale":
      self.setCursor(Qt.CursorShape.SizeFDiagCursor)
    elif self._point_is_inside_signature(position, signature_rect, selected):
      self.setCursor(Qt.CursorShape.SizeAllCursor)
    else:
      self.unsetCursor()

  def _handle_rects(
    self,
    signature_rect: QRect,
    instance: SignatureInstance | TextInstance,
  ) -> dict[str, QRect]:
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
      rotated = self._rotated_point(center, point, instance)
      handle_rects[name] = QRect(
        round(rotated.x() - self._handle_size / 2),
        round(rotated.y() - self._handle_size / 2),
        self._handle_size,
        self._handle_size,
      )
    return handle_rects

  def _hit_test_handle(
    self,
    position: QPoint,
    signature_rect: QRect,
    instance: SignatureInstance | TextInstance,
  ) -> str | None:
    if isinstance(instance, SignatureInstance):
      rotate_center = self._rotate_handle_center(signature_rect, instance)
      rotate_rect = QRect(
        round(rotate_center.x() - self._handle_size / 2),
        round(rotate_center.y() - self._handle_size / 2),
        self._handle_size,
        self._handle_size,
      )
      if rotate_rect.contains(position):
        return "rotate"

    for name, handle_rect in self._handle_rects(signature_rect, instance).items():
      if handle_rect.contains(position):
        return name

    return None

  def _point_is_inside_signature(
    self,
    position: QPoint,
    signature_rect: QRect,
    instance: SignatureInstance | TextInstance,
  ) -> bool:
    center = QPointF(signature_rect.center())
    local = self._unrotated_point(center, QPointF(position.x(), position.y()), instance)
    return QRectF(signature_rect).contains(local)

  def _rotate_handle_center(
    self,
    signature_rect: QRect,
    instance: SignatureInstance | TextInstance,
  ) -> QPointF:
    center = QPointF(signature_rect.center())
    local_point = QPointF(
      signature_rect.center().x(),
      signature_rect.top() - self._rotate_handle_distance,
    )
    return self._rotated_point(center, local_point, instance)

  def _rotated_point(
    self,
    center: QPointF,
    point: QPointF,
    instance: SignatureInstance | TextInstance,
  ) -> QPointF:
    angle = math.radians(instance.placement.rotation_degrees)
    dx = point.x() - center.x()
    dy = point.y() - center.y()
    return QPointF(
      center.x() + dx * math.cos(angle) - dy * math.sin(angle),
      center.y() + dx * math.sin(angle) + dy * math.cos(angle),
    )

  def _unrotated_point(
    self,
    center: QPointF,
    point: QPointF,
    instance: SignatureInstance | TextInstance,
  ) -> QPointF:
    angle = math.radians(-instance.placement.rotation_degrees)
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
    self.signers: list[Signer] = []
    self.signature_instances: list[SignatureInstance] = []
    self.text_instances: list[TextInstance] = []
    self.selected_signer_id: str | None = None
    self.selected_instance_id: str | None = None
    self._next_signer_number = 1
    self._next_instance_number = 1

    self._build_sign_ui()
    self._update_state()

  def _build_sign_ui(self) -> None:
    instructions = QLabel(
      "Open a PDF, add signers, upload or draw each signature, place them wherever "
      "they belong, then save a signed copy."
    )
    instructions.setWordWrap(True)
    self.content_layout.addWidget(instructions)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.setChildrenCollapsible(False)
    splitter.addWidget(self._build_controls_panel())
    splitter.addWidget(self._build_preview_panel())
    splitter.setSizes([330, 760])
    splitter.setStretchFactor(0, 0)
    splitter.setStretchFactor(1, 1)

    self.content_layout.addWidget(splitter, 1)

  def _build_controls_panel(self) -> QWidget:
    scroll_area = QScrollArea()
    scroll_area.setObjectName("signControlsScroll")
    scroll_area.setWidgetResizable(True)
    scroll_area.setMinimumWidth(300)
    scroll_area.setMaximumWidth(390)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    panel = QWidget()
    panel.setObjectName("signControlsPanel")
    panel.setMinimumWidth(280)
    panel.setStyleSheet("""
      QWidget#signControlsPanel {
        background: #ffffff;
      }
      QWidget#signControlsPanel QLabel {
        color: #111827;
      }
      QWidget#signControlsPanel QLabel#pageSubtitle {
        color: #4b5563;
      }
      QWidget#signControlsPanel QListWidget {
        background: #ffffff;
        color: #111827;
        border: 1px solid #d7deea;
        border-radius: 6px;
      }
      QWidget#signControlsPanel QListWidget::item:selected {
        background: #dbeafe;
        color: #111827;
      }
    """)

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(4, 4, 8, 4)
    layout.setSpacing(8)

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

    signer_title = QLabel("Signers")
    signer_title.setObjectName("sectionTitle")
    self.signer_list = QListWidget()
    self.signer_list.setMinimumHeight(76)
    self.signer_list.setMaximumHeight(120)
    self.add_signer_button = QPushButton("Add Signer")
    self.rename_signer_button = QPushButton("Rename Signer")
    self.rename_signer_button.setObjectName("secondaryButton")
    self.remove_signer_button = QPushButton("Remove Signer")
    self.remove_signer_button.setObjectName("secondaryButton")

    signature_title = QLabel("Selected Signer Signature")
    signature_title.setObjectName("sectionTitle")
    self.upload_signature_button = QPushButton("Upload Signature Image")
    self.draw_signature_button = QPushButton("Draw Signature")
    self.clear_signature_button = QPushButton("Clear Signer Signature")
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
    layout.addWidget(signer_title)
    layout.addWidget(self.signer_list)
    layout.addWidget(self.add_signer_button)
    layout.addWidget(self.rename_signer_button)
    layout.addWidget(self.remove_signer_button)
    layout.addSpacing(10)
    layout.addWidget(signature_title)
    layout.addWidget(self.upload_signature_button)
    layout.addWidget(self.draw_signature_button)
    layout.addWidget(self.clear_signature_button)
    layout.addWidget(self.signature_status_label)
    layout.addStretch()
    layout.addWidget(self.save_button)

    self.open_pdf_button.clicked.connect(self._on_open_pdf_clicked)
    self.previous_button.clicked.connect(self._on_previous_page_clicked)
    self.next_button.clicked.connect(self._on_next_page_clicked)
    self.signer_list.currentItemChanged.connect(self._on_signer_selection_changed)
    self.add_signer_button.clicked.connect(self._add_signer)
    self.rename_signer_button.clicked.connect(self._rename_selected_signer)
    self.remove_signer_button.clicked.connect(self._remove_selected_signer)
    self.upload_signature_button.clicked.connect(self._on_upload_signature_clicked)
    self.draw_signature_button.clicked.connect(self._on_draw_signature_clicked)
    self.clear_signature_button.clicked.connect(self._clear_signature)
    self.save_button.clicked.connect(self._on_save_clicked)

    scroll_area.setWidget(panel)
    return scroll_area

  def _build_preview_panel(self) -> QWidget:
    panel = QWidget()
    panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(8)

    title = QLabel("Preview")
    title.setObjectName("sectionTitle")
    self.preview_status_label = QLabel("Open a PDF to begin.")
    self.preview_status_label.setObjectName("pageSubtitle")
    self.preview_status_label.setWordWrap(True)

    self.preview = PdfSignaturePreview()
    self.preview.placement_changed.connect(self._on_preview_placement_changed)
    self.preview.selected_instance_changed.connect(self._on_preview_selection_changed)

    layout.addWidget(title)
    layout.addWidget(self.preview_status_label)

    body = QHBoxLayout()
    body.setSpacing(10)
    body.addWidget(self.preview, 1)
    body.addWidget(self._build_placements_panel())
    layout.addLayout(body, 1)
    return panel

  def _build_placements_panel(self) -> QWidget:
    panel = QWidget()
    panel.setObjectName("placementsPanel")
    panel.setMinimumWidth(240)
    panel.setMaximumWidth(320)
    panel.setStyleSheet("""
      QWidget#placementsPanel {
        background: #ffffff;
      }
      QWidget#placementsPanel QLabel {
        color: #111827;
      }
      QWidget#placementsPanel QListWidget {
        background: #ffffff;
        color: #111827;
        border: 1px solid #d7deea;
        border-radius: 6px;
      }
      QWidget#placementsPanel QListWidget::item:selected {
        background: #dbeafe;
        color: #111827;
      }
    """)

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(8)

    placement_title = QLabel("Placements")
    placement_title.setObjectName("sectionTitle")
    self.placement_list = QListWidget()
    self.placement_list.setMinimumHeight(180)
    self.add_placement_button = QPushButton("Add Signature")
    self.add_text_button = QPushButton("Add Text")
    self.duplicate_placement_button = QPushButton("Duplicate Selected")
    self.duplicate_placement_button.setObjectName("secondaryButton")
    self.edit_text_button = QPushButton("Edit Text")
    self.edit_text_button.setObjectName("secondaryButton")
    self.remove_placement_button = QPushButton("Remove Selected")
    self.remove_placement_button.setObjectName("secondaryButton")

    layout.addWidget(placement_title)
    layout.addWidget(self.placement_list, 1)
    layout.addWidget(self.add_placement_button)
    layout.addWidget(self.add_text_button)
    layout.addWidget(self.duplicate_placement_button)
    layout.addWidget(self.edit_text_button)
    layout.addWidget(self.remove_placement_button)

    self.placement_list.currentItemChanged.connect(self._on_placement_selection_changed)
    self.add_placement_button.clicked.connect(self._add_placement_on_current_page)
    self.add_text_button.clicked.connect(self._add_text_on_current_page)
    self.duplicate_placement_button.clicked.connect(self._duplicate_selected_placement)
    self.edit_text_button.clicked.connect(self._edit_selected_text)
    self.remove_placement_button.clicked.connect(self._remove_selected_placement)
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
    self.selected_instance_id = None
    self.signature_instances = []
    self.text_instances = []
    self.preview.clear_signatures()

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
    signer = self._selected_signer()
    if signer is None:
      QMessageBox.warning(self, "No Signer", "Select or add a signer first.")
      return

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

    self._set_signature_for_signer(signer, pixmap)

  def _on_draw_signature_clicked(self) -> None:
    signer = self._selected_signer()
    if signer is None:
      QMessageBox.warning(self, "No Signer", "Select or add a signer first.")
      return

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

    signer.signature_png_bytes = signature_bytes
    signer.signature_pixmap = pixmap
    self._refresh_signer_list()
    self._refresh_preview_signatures()
    self._update_state()

  def _clear_signature(self) -> None:
    signer = self._selected_signer()
    if signer is None:
      return

    signer.signature_png_bytes = b""
    signer.signature_pixmap = None
    self.signature_instances = [
      instance
      for instance in self.signature_instances
      if instance.signer_id != signer.signer_id
    ]
    if self.selected_instance_id and self._selected_instance() is None:
      self.selected_instance_id = None
    self._refresh_signer_list()
    self._refresh_placement_list()
    self._refresh_preview_signatures()
    self._update_state()

  def _on_save_clicked(self) -> None:
    if self.pdf_path is None:
      QMessageBox.warning(self, "No PDF", "Open a PDF before saving.")
      return

    if not self.signature_instances and not self.text_instances:
      QMessageBox.warning(
        self,
        "No Placements",
        "Add at least one signature or text placement before saving.",
      )
      return

    signature_stamps = self._signature_stamps()
    text_stamps = self._text_stamps()
    if self.signature_instances and not signature_stamps:
      QMessageBox.warning(
        self,
        "No Complete Signatures",
        "Every saved placement needs a signer with a signature image.",
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
      add_signatures_to_pdf(
        input_pdf_path=self.pdf_path,
        output_pdf_path=save_path,
        signature_stamps=signature_stamps,
        text_stamps=text_stamps,
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

  def _set_signature_for_signer(self, signer: Signer, pixmap: QPixmap) -> None:
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.toImage().save(buffer, "PNG")

    signer.signature_png_bytes = bytes(byte_array)
    signer.signature_pixmap = pixmap
    self._refresh_signer_list()
    self._refresh_preview_signatures()
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
    self._refresh_preview_signatures()

  def _update_state(self) -> None:
    has_pdf = self.pdf_path is not None
    selected_signer = self._selected_signer()
    has_signer = selected_signer is not None
    selected_signer_has_signature = bool(
      selected_signer and selected_signer.signature_png_bytes
    )
    selected_instance = self._selected_instance()
    has_selected_placement = selected_instance is not None
    has_selected_text = isinstance(selected_instance, TextInstance)

    self.previous_button.setEnabled(has_pdf and self.current_page_index > 0)
    self.next_button.setEnabled(has_pdf and self.current_page_index < self.page_count - 1)
    self.add_signer_button.setEnabled(has_pdf)
    self.rename_signer_button.setEnabled(has_pdf and has_signer)
    self.remove_signer_button.setEnabled(has_pdf and has_signer)
    self.upload_signature_button.setEnabled(has_pdf and has_signer)
    self.draw_signature_button.setEnabled(has_pdf and has_signer)
    self.clear_signature_button.setEnabled(selected_signer_has_signature)
    self.add_placement_button.setEnabled(has_pdf and selected_signer_has_signature)
    self.add_text_button.setEnabled(has_pdf)
    self.duplicate_placement_button.setEnabled(has_selected_placement)
    self.edit_text_button.setEnabled(has_selected_text)
    self.remove_placement_button.setEnabled(has_selected_placement)
    self.save_button.setEnabled(has_pdf and bool(self.signature_instances or self.text_instances))

    if has_pdf:
      self.page_label.setText(f"Page {self.current_page_index + 1} of {self.page_count}")
      self.preview_status_label.setText(
        "Select a placed signature or text field to move it. Use edge handles to resize; signatures also have a top rotation handle."
      )
    else:
      self.page_label.setText("Page 0 of 0")
      self.preview_status_label.setText("Open a PDF to begin.")

    self._update_signature_status()

  def _on_preview_placement_changed(self) -> None:
    self._refresh_placement_list()
    self._update_signature_status()

  def _update_signature_status(self) -> None:
    signer = self._selected_signer()
    if signer is None:
      self.signature_status_label.setText("No signer selected")
      return

    count = len([
      instance
      for instance in self.signature_instances
      if instance.signer_id == signer.signer_id
    ])
    if not signer.signature_png_bytes:
      self.signature_status_label.setText(f"{signer.name} has no signature image")
      return

    self.signature_status_label.setText(
      f"{signer.name} has {count} placement{'s' if count != 1 else ''}."
    )

  def _add_signer(self) -> None:
    if self.pdf_path is None:
      return

    default_name = f"Signer {self._next_signer_number}"
    name, accepted = QInputDialog.getText(
      self,
      "Add Signer",
      "Signer name:",
      text=default_name,
    )
    if not accepted:
      return

    name = name.strip() or default_name
    signer = Signer(
      signer_id=f"signer-{self._next_signer_number}",
      name=name,
    )
    self._next_signer_number += 1
    self.signers.append(signer)
    self.selected_signer_id = signer.signer_id
    self._refresh_signer_list()
    self._update_state()

  def _rename_selected_signer(self) -> None:
    signer = self._selected_signer()
    if signer is None:
      return

    name, accepted = QInputDialog.getText(
      self,
      "Rename Signer",
      "Signer name:",
      text=signer.name,
    )
    if not accepted:
      return

    signer.name = name.strip() or signer.name
    self._refresh_signer_list()
    self._refresh_placement_list()
    self._update_state()

  def _remove_selected_signer(self) -> None:
    signer = self._selected_signer()
    if signer is None:
      return

    self.signers = [
      existing
      for existing in self.signers
      if existing.signer_id != signer.signer_id
    ]
    self.signature_instances = [
      instance
      for instance in self.signature_instances
      if instance.signer_id != signer.signer_id
    ]
    self.selected_signer_id = self.signers[0].signer_id if self.signers else None
    if self.selected_instance_id and self._selected_instance() is None:
      self.selected_instance_id = None
    self._refresh_signer_list()
    self._refresh_placement_list()
    self._refresh_preview_signatures()
    self._update_state()

  def _add_placement_on_current_page(self) -> None:
    signer = self._selected_signer()
    if signer is None or signer.signature_pixmap is None:
      return

    placement = self.preview.default_placement_for(signer.signature_pixmap)
    instance = SignatureInstance(
      instance_id=f"placement-{self._next_instance_number}",
      signer_id=signer.signer_id,
      page_index=self.current_page_index,
      placement=placement,
    )
    self._next_instance_number += 1
    self.signature_instances.append(instance)
    self.selected_instance_id = instance.instance_id
    self._refresh_placement_list()
    self._refresh_preview_signatures()
    self._update_state()

  def _add_text_on_current_page(self) -> None:
    if self.pdf_path is None:
      return

    text, accepted = QInputDialog.getText(
      self,
      "Add Text Field",
      "Text:",
    )
    if not accepted:
      return

    text = text.strip()
    if not text:
      return

    placement = self.preview.default_text_placement()
    instance = TextInstance(
      instance_id=f"text-{self._next_instance_number}",
      page_index=self.current_page_index,
      text=text,
      placement=placement,
      font_size=self.preview.default_text_font_size(),
    )
    self._next_instance_number += 1
    self.text_instances.append(instance)
    self.selected_instance_id = instance.instance_id
    self._refresh_placement_list()
    self._refresh_preview_signatures()
    self._update_state()

  def _edit_selected_text(self) -> None:
    instance = self._selected_instance()
    if not isinstance(instance, TextInstance):
      return

    text, accepted = QInputDialog.getText(
      self,
      "Edit Text Field",
      "Text:",
      text=instance.text,
    )
    if not accepted:
      return

    text = text.strip()
    if not text:
      return

    instance.text = text
    self._refresh_placement_list()
    self._refresh_preview_signatures()
    self._update_state()

  def _duplicate_selected_placement(self) -> None:
    instance = self._selected_instance()
    if instance is None:
      return

    placement = self._offset_duplicate_placement(instance.placement)
    if isinstance(instance, SignatureInstance):
      duplicate = SignatureInstance(
        instance_id=f"placement-{self._next_instance_number}",
        signer_id=instance.signer_id,
        page_index=self.current_page_index,
        placement=placement,
      )
      self.signature_instances.append(duplicate)
    else:
      duplicate = TextInstance(
        instance_id=f"text-{self._next_instance_number}",
        page_index=self.current_page_index,
        text=instance.text,
        placement=placement,
        font_size=instance.font_size,
      )
      self.text_instances.append(duplicate)

    self._next_instance_number += 1
    self.selected_instance_id = duplicate.instance_id
    self._refresh_placement_list()
    self._refresh_preview_signatures()
    self._update_state()

  def _offset_duplicate_placement(self, placement: SignaturePlacement) -> SignaturePlacement:
    offset = 18
    x = placement.x + offset
    y = placement.y + offset
    return SignaturePlacement(
      x=x,
      y=y,
      width=placement.width,
      height=placement.height,
      rotation_degrees=placement.rotation_degrees,
    )

  def _remove_selected_placement(self) -> None:
    instance = self._selected_instance()
    if instance is None:
      return

    if isinstance(instance, SignatureInstance):
      self.signature_instances = [
        existing
        for existing in self.signature_instances
        if existing.instance_id != instance.instance_id
      ]
    else:
      self.text_instances = [
        existing
        for existing in self.text_instances
        if existing.instance_id != instance.instance_id
      ]
    self.selected_instance_id = None
    self._refresh_placement_list()
    self._refresh_preview_signatures()
    self._update_state()

  def _on_signer_selection_changed(
    self,
    current: QListWidgetItem | None,
    previous: QListWidgetItem | None,
  ) -> None:
    del previous
    if current is None:
      self.selected_signer_id = None
    else:
      self.selected_signer_id = current.data(Qt.ItemDataRole.UserRole)
    self._update_state()

  def _on_placement_selection_changed(
    self,
    current: QListWidgetItem | None,
    previous: QListWidgetItem | None,
  ) -> None:
    del previous
    if current is None:
      self.selected_instance_id = None
    else:
      self.selected_instance_id = current.data(Qt.ItemDataRole.UserRole)
      instance = self._selected_instance()
      if instance is not None and instance.page_index != self.current_page_index:
        self.current_page_index = instance.page_index
        self._load_current_page()

    self._refresh_preview_signatures()
    self._update_state()

  def _on_preview_selection_changed(self, instance_id: str) -> None:
    self.selected_instance_id = instance_id
    instance = self._selected_instance()
    if isinstance(instance, SignatureInstance):
      self.selected_signer_id = instance.signer_id
    self._refresh_signer_list()
    self._refresh_placement_list()
    self._update_state()

  def _refresh_signer_list(self) -> None:
    self.signer_list.blockSignals(True)
    self.signer_list.clear()
    for signer in self.signers:
      suffix = " ready" if signer.signature_png_bytes else " needs signature"
      item = QListWidgetItem(f"{signer.name} - {suffix}")
      item.setData(Qt.ItemDataRole.UserRole, signer.signer_id)
      self.signer_list.addItem(item)
      if signer.signer_id == self.selected_signer_id:
        self.signer_list.setCurrentItem(item)
    self.signer_list.blockSignals(False)

  def _refresh_placement_list(self) -> None:
    self.placement_list.blockSignals(True)
    self.placement_list.clear()
    all_instances = self._all_instances()
    for index, instance in enumerate(all_instances, start=1):
      if isinstance(instance, SignatureInstance):
        signer = self._signer_by_id(instance.signer_id)
        signer_name = signer.name if signer is not None else "Unknown signer"
        rotation = round(instance.placement.rotation_degrees)
        label = f"{index}. Signature: {signer_name} - page {instance.page_index + 1} - {rotation} deg"
      else:
        text = instance.text
        if len(text) > 24:
          text = f"{text[:21]}..."
        label = f"{index}. Text: {text} - page {instance.page_index + 1}"
      item = QListWidgetItem(label)
      item.setData(Qt.ItemDataRole.UserRole, instance.instance_id)
      self.placement_list.addItem(item)
      if instance.instance_id == self.selected_instance_id:
        self.placement_list.setCurrentItem(item)
    self.placement_list.blockSignals(False)

  def _refresh_preview_signatures(self) -> None:
    current_page_instances = [
      instance
      for instance in self.signature_instances
      if instance.page_index == self.current_page_index
    ]
    current_page_text = [
      instance
      for instance in self.text_instances
      if instance.page_index == self.current_page_index
    ]
    signature_pixmaps = {
      signer.signer_id: signer.signature_pixmap
      for signer in self.signers
      if signer.signature_pixmap is not None
    }
    self.preview.set_signatures(
      current_page_instances,
      current_page_text,
      signature_pixmaps,
      self.selected_instance_id,
    )

  def _signature_stamps(self) -> list[SignatureStamp]:
    stamps = []
    for instance in self.signature_instances:
      signer = self._signer_by_id(instance.signer_id)
      if signer is None or not signer.signature_png_bytes:
        continue
      stamps.append(
        SignatureStamp(
          page_index=instance.page_index,
          signature_png_bytes=signer.signature_png_bytes,
          signature_placement=instance.placement,
        )
      )
    return stamps

  def _text_stamps(self) -> list[TextStamp]:
    stamps = []
    for instance in self.text_instances:
      if not instance.text.strip():
        continue
      stamps.append(
        TextStamp(
          page_index=instance.page_index,
          text=instance.text,
          placement=instance.placement,
          font_size=instance.font_size,
        )
      )
    return stamps

  def _selected_signer(self) -> Signer | None:
    if self.selected_signer_id is None:
      return None
    return self._signer_by_id(self.selected_signer_id)

  def _signer_by_id(self, signer_id: str) -> Signer | None:
    for signer in self.signers:
      if signer.signer_id == signer_id:
        return signer
    return None

  def _selected_instance(self) -> SignatureInstance | TextInstance | None:
    if self.selected_instance_id is None:
      return None
    for instance in self._all_instances():
      if instance.instance_id == self.selected_instance_id:
        return instance
    return None

  def _all_instances(self) -> list[SignatureInstance | TextInstance]:
    return sorted(
      [*self.signature_instances, *self.text_instances],
      key=lambda instance: (instance.page_index, instance.instance_id),
    )
