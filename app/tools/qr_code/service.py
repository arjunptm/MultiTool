import math
from dataclasses import dataclass, replace
from urllib.parse import urlsplit, urlunsplit

import qrcode
from qrcode.exceptions import DataOverflowError
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtSvg import QSvgGenerator


MODULE_STYLES = ("square", "rounded", "dots", "gapped", "vertical")
EYE_STYLES = ("square", "rounded", "circle", "soft")
FRAME_STYLES = (
  "none",
  "rounded_label",
  "badge",
  "speech_bubble",
  "ticket",
  "hanging_tag",
  "poster",
)

MAX_LOGO_BYTES = 5 * 1024 * 1024
MIN_LOGO_SCALE = 0.10
MAX_LOGO_SCALE = 0.18
MIN_CONTRAST_RATIO = 4.5


class QrCodeError(ValueError):
  """Raised when QR input or rendering settings are invalid."""


@dataclass(frozen=True)
class QrCodeDesign:
  url: str
  foreground_color: str = "#111827"
  background_color: str = "#ffffff"
  module_style: str = "square"
  eye_style: str = "square"
  frame_style: str = "none"
  frame_text: str = "SCAN ME"
  logo_bytes: bytes = b""
  logo_scale: float = 0.16


def normalize_url(value: str) -> str:
  candidate = value.strip()
  if not candidate:
    raise QrCodeError("Enter a website URL to create a QR code.")

  if any(character.isspace() for character in candidate):
    raise QrCodeError("The website URL cannot contain spaces.")

  if "://" not in candidate:
    candidate = f"https://{candidate}"

  try:
    parsed = urlsplit(candidate)
    _ = parsed.port
  except ValueError as exc:
    raise QrCodeError("Enter a valid website URL.") from exc

  scheme = parsed.scheme.lower()
  if scheme not in {"http", "https"}:
    raise QrCodeError("Only http:// and https:// website URLs are supported.")
  if not parsed.hostname:
    raise QrCodeError("Enter a website URL with a hostname.")

  hostname = parsed.hostname.lower()
  if "." not in hostname and hostname != "localhost":
    raise QrCodeError("Enter a complete website hostname, such as example.com.")

  user_info = ""
  if parsed.username:
    user_info = parsed.username
    if parsed.password:
      user_info += f":{parsed.password}"
    user_info += "@"

  port = f":{parsed.port}" if parsed.port is not None else ""
  netloc = f"{user_info}{hostname}{port}"
  return urlunsplit((scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def contrast_ratio(foreground: str, background: str) -> float:
  foreground_color = _opaque_color(foreground, "foreground")
  background_color = _opaque_color(background, "background")
  lighter = max(_relative_luminance(foreground_color), _relative_luminance(background_color))
  darker = min(_relative_luminance(foreground_color), _relative_luminance(background_color))
  return (lighter + 0.05) / (darker + 0.05)


def validate_design(design: QrCodeDesign) -> QrCodeDesign:
  normalized = normalize_url(design.url)
  foreground = _opaque_color(design.foreground_color, "foreground")
  background = _opaque_color(design.background_color, "background")

  if _relative_luminance(foreground) >= _relative_luminance(background):
    raise QrCodeError("Choose a foreground color darker than the background.")
  ratio = contrast_ratio(foreground.name(), background.name())
  if ratio < MIN_CONTRAST_RATIO:
    raise QrCodeError(
      f"Increase the color contrast to at least {MIN_CONTRAST_RATIO:.1f}:1. "
      f"The current contrast is {ratio:.1f}:1."
    )
  if design.module_style not in MODULE_STYLES:
    raise QrCodeError("The selected QR pattern is not supported.")
  if design.eye_style not in EYE_STYLES:
    raise QrCodeError("The selected finder-eye style is not supported.")
  if design.frame_style not in FRAME_STYLES:
    raise QrCodeError("The selected frame is not supported.")
  if len(design.logo_bytes) > MAX_LOGO_BYTES:
    raise QrCodeError("Logo images must be 5 MB or smaller.")
  if not MIN_LOGO_SCALE <= design.logo_scale <= MAX_LOGO_SCALE:
    raise QrCodeError("Logo size must stay between 10% and 18% of the QR area.")
  if design.logo_bytes:
    logo = QImage.fromData(design.logo_bytes)
    if logo.isNull():
      raise QrCodeError("The uploaded logo is not a readable image.")

  return replace(
    design,
    url=normalized,
    foreground_color=foreground.name(),
    background_color=background.name(),
    frame_text=(design.frame_text.strip() or "SCAN ME")[:40],
  )


def build_matrix(url: str) -> list[list[bool]]:
  normalized = normalize_url(url)
  qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
  )
  qr.add_data(normalized)
  try:
    qr.make(fit=True)
  except (DataOverflowError, ValueError) as exc:
    raise QrCodeError("This URL is too long to fit in a QR code.") from exc
  return qr.get_matrix()


def render_qr_image(design: QrCodeDesign, size: int) -> QImage:
  _validate_size(size)
  validated = validate_design(design)
  matrix = build_matrix(validated.url)
  image = QImage(size, size, QImage.Format.Format_ARGB32)
  image.fill(QColor(validated.background_color))
  painter = QPainter(image)
  try:
    _paint_design(painter, QRectF(0, 0, size, size), validated, matrix)
  finally:
    painter.end()
  return image


def render_qr_png(design: QrCodeDesign, size: int) -> bytes:
  image = render_qr_image(design, size)
  byte_array = QByteArray()
  buffer = QBuffer(byte_array)
  if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
    raise QrCodeError("Could not prepare the PNG output.")
  if not image.save(buffer, "PNG"):
    raise QrCodeError("Could not encode the QR code as PNG.")
  return bytes(byte_array)


def render_qr_svg(design: QrCodeDesign, size: int = 1024) -> bytes:
  _validate_size(size)
  validated = validate_design(design)
  matrix = build_matrix(validated.url)
  byte_array = QByteArray()
  buffer = QBuffer(byte_array)
  if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
    raise QrCodeError("Could not prepare the SVG output.")

  generator = QSvgGenerator()
  generator.setOutputDevice(buffer)
  generator.setSize(QSize(size, size))
  generator.setViewBox(QRect(0, 0, size, size))
  generator.setTitle("QR Code generated by MultiTool")
  generator.setDescription(f"Website QR code for {validated.url}")

  painter = QPainter(generator)
  try:
    _paint_design(painter, QRectF(0, 0, size, size), validated, matrix)
  finally:
    painter.end()
  return bytes(byte_array)


def suggested_filename(url: str, extension: str) -> str:
  normalized = normalize_url(url)
  hostname = urlsplit(normalized).hostname or "website"
  safe_hostname = "".join(
    character if character.isalnum() else "-"
    for character in hostname
  ).strip("-")
  while "--" in safe_hostname:
    safe_hostname = safe_hostname.replace("--", "-")
  return f"{safe_hostname or 'website'}-qr.{extension.lower().lstrip('.')}"


def _paint_design(
  painter: QPainter,
  canvas: QRectF,
  design: QrCodeDesign,
  matrix: list[list[bool]],
) -> None:
  painter.setRenderHint(QPainter.RenderHint.Antialiasing)
  background = QColor(design.background_color)
  foreground = QColor(design.foreground_color)
  painter.fillRect(canvas, background)

  qr_rect = _paint_frame(painter, canvas, design.frame_style, design.frame_text, foreground, background)
  _paint_matrix(painter, qr_rect, matrix, design.module_style, design.eye_style, foreground, background)
  if design.logo_bytes:
    _paint_logo(painter, qr_rect, matrix, design.logo_bytes, design.logo_scale, background)


def _paint_frame(
  painter: QPainter,
  canvas: QRectF,
  frame_style: str,
  text: str,
  foreground: QColor,
  background: QColor,
) -> QRectF:
  width = canvas.width()
  height = canvas.height()
  unit = min(width, height)
  painter.setPen(Qt.PenStyle.NoPen)

  if frame_style == "none":
    margin = unit * 0.04
    return QRectF(canvas.left() + margin, canvas.top() + margin, width - 2 * margin, height - 2 * margin)

  outer = QRectF(canvas.left() + unit * 0.035, canvas.top() + unit * 0.035, width - unit * 0.07, height - unit * 0.07)
  painter.setBrush(foreground)

  if frame_style == "badge":
    painter.drawEllipse(outer)
  elif frame_style == "speech_bubble":
    bubble = outer.adjusted(0, 0, 0, -unit * 0.07)
    painter.drawRoundedRect(bubble, unit * 0.06, unit * 0.06)
    tail = QPainterPath()
    tail.moveTo(canvas.center().x() - unit * 0.06, bubble.bottom() - 1)
    tail.lineTo(canvas.center().x() + unit * 0.10, bubble.bottom() - 1)
    tail.lineTo(canvas.center().x() + unit * 0.02, outer.bottom())
    tail.closeSubpath()
    painter.drawPath(tail)
  elif frame_style == "ticket":
    painter.drawRoundedRect(outer, unit * 0.035, unit * 0.035)
    painter.setBrush(background)
    notch_radius = unit * 0.035
    painter.drawEllipse(QRectF(outer.left() - notch_radius, outer.center().y() - notch_radius, notch_radius * 2, notch_radius * 2))
    painter.drawEllipse(QRectF(outer.right() - notch_radius, outer.center().y() - notch_radius, notch_radius * 2, notch_radius * 2))
  elif frame_style == "hanging_tag":
    tag = QPainterPath()
    tag.moveTo(outer.left() + unit * 0.13, outer.top())
    tag.lineTo(outer.right() - unit * 0.13, outer.top())
    tag.lineTo(outer.right(), outer.top() + unit * 0.14)
    tag.lineTo(outer.right(), outer.bottom())
    tag.lineTo(outer.left(), outer.bottom())
    tag.lineTo(outer.left(), outer.top() + unit * 0.14)
    tag.closeSubpath()
    painter.drawPath(tag)
    painter.setBrush(background)
    painter.drawEllipse(QRectF(canvas.center().x() - unit * 0.025, outer.top() + unit * 0.025, unit * 0.05, unit * 0.05))
  elif frame_style == "poster":
    painter.drawRoundedRect(outer, unit * 0.02, unit * 0.02)
    painter.setPen(QPen(background, max(1.0, unit * 0.006)))
    painter.drawLine(
      outer.left() + unit * 0.08,
      outer.top() + unit * 0.13,
      outer.right() - unit * 0.08,
      outer.top() + unit * 0.13,
    )
    painter.setPen(Qt.PenStyle.NoPen)
  else:
    painter.drawRoundedRect(outer, unit * 0.055, unit * 0.055)

  if frame_style == "poster":
    qr_size = unit * 0.70
    qr_top = canvas.top() + unit * 0.19
    text_rect = QRectF(outer.left(), outer.top() + unit * 0.025, outer.width(), unit * 0.085)
  elif frame_style == "hanging_tag":
    qr_size = unit * 0.67
    qr_top = canvas.top() + unit * 0.13
    text_rect = QRectF(outer.left(), canvas.top() + unit * 0.82, outer.width(), unit * 0.08)
  else:
    qr_size = unit * 0.70
    qr_top = canvas.top() + unit * 0.075
    text_rect = QRectF(outer.left(), canvas.top() + unit * 0.80, outer.width(), unit * 0.09)

  qr_rect = QRectF(canvas.center().x() - qr_size / 2, qr_top, qr_size, qr_size)
  painter.setBrush(background)
  painter.drawRoundedRect(qr_rect, unit * 0.025, unit * 0.025)
  _draw_frame_text(painter, text_rect, text, background, unit)
  return qr_rect


def _draw_frame_text(painter: QPainter, rect: QRectF, text: str, color: QColor, unit: float) -> None:
  painter.save()
  painter.setPen(color)
  font = QFont()
  font.setBold(True)
  font.setPixelSize(max(9, round(unit * 0.038)))
  painter.setFont(font)
  painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
  painter.restore()


def _paint_matrix(
  painter: QPainter,
  qr_rect: QRectF,
  matrix: list[list[bool]],
  module_style: str,
  eye_style: str,
  foreground: QColor,
  background: QColor,
) -> None:
  count = len(matrix)
  cell = min(qr_rect.width(), qr_rect.height()) / count
  actual_size = cell * count
  left = qr_rect.center().x() - actual_size / 2
  top = qr_rect.center().y() - actual_size / 2
  finder_origins = ((4, 4), (count - 11, 4), (4, count - 11))

  painter.setPen(Qt.PenStyle.NoPen)
  painter.setBrush(foreground)
  for row, values in enumerate(matrix):
    for column, active in enumerate(values):
      if not active or _inside_finder(column, row, finder_origins):
        continue
      module_rect = QRectF(left + column * cell, top + row * cell, cell, cell)
      _draw_module(painter, module_rect, module_style)

  for column, row in finder_origins:
    eye_rect = QRectF(left + column * cell, top + row * cell, cell * 7, cell * 7)
    _draw_eye(painter, eye_rect, eye_style, foreground, background, cell)


def _inside_finder(column: int, row: int, origins: tuple[tuple[int, int], ...]) -> bool:
  return any(
    origin_column <= column < origin_column + 7 and origin_row <= row < origin_row + 7
    for origin_column, origin_row in origins
  )


def _draw_module(painter: QPainter, rect: QRectF, style: str) -> None:
  if style == "rounded":
    painter.drawRoundedRect(rect.adjusted(rect.width() * 0.04, rect.height() * 0.04, -rect.width() * 0.04, -rect.height() * 0.04), rect.width() * 0.28, rect.height() * 0.28)
  elif style == "dots":
    painter.drawEllipse(rect.adjusted(rect.width() * 0.08, rect.height() * 0.08, -rect.width() * 0.08, -rect.height() * 0.08))
  elif style == "gapped":
    painter.drawRect(rect.adjusted(rect.width() * 0.10, rect.height() * 0.10, -rect.width() * 0.10, -rect.height() * 0.10))
  elif style == "vertical":
    painter.drawRoundedRect(rect.adjusted(rect.width() * 0.15, 0, -rect.width() * 0.15, 0), rect.width() * 0.22, rect.width() * 0.22)
  else:
    painter.drawRect(rect)


def _draw_eye(
  painter: QPainter,
  rect: QRectF,
  style: str,
  foreground: QColor,
  background: QColor,
  cell: float,
) -> None:
  middle = rect.adjusted(cell, cell, -cell, -cell)
  center = rect.adjusted(cell * 2, cell * 2, -cell * 2, -cell * 2)
  painter.setPen(Qt.PenStyle.NoPen)

  if style == "circle":
    painter.setBrush(foreground)
    painter.drawEllipse(rect)
    painter.setBrush(background)
    painter.drawEllipse(middle)
    painter.setBrush(foreground)
    painter.drawEllipse(center)
    return

  if style == "rounded":
    outer_radius = cell * 1.3
    middle_radius = cell * 0.9
    center_radius = cell * 0.7
  elif style == "soft":
    outer_radius = cell * 2.0
    middle_radius = cell * 1.4
    center_radius = cell * 1.0
  else:
    outer_radius = middle_radius = center_radius = 0

  painter.setBrush(foreground)
  painter.drawRoundedRect(rect, outer_radius, outer_radius)
  painter.setBrush(background)
  painter.drawRoundedRect(middle, middle_radius, middle_radius)
  painter.setBrush(foreground)
  painter.drawRoundedRect(center, center_radius, center_radius)


def _paint_logo(
  painter: QPainter,
  qr_rect: QRectF,
  matrix: list[list[bool]],
  logo_bytes: bytes,
  logo_scale: float,
  background: QColor,
) -> None:
  logo = QImage.fromData(logo_bytes)
  if logo.isNull():
    raise QrCodeError("The uploaded logo is not a readable image.")

  matrix_size = len(matrix)
  content_ratio = max(0.1, (matrix_size - 8) / matrix_size)
  content_size = min(qr_rect.width(), qr_rect.height()) * content_ratio
  logo_size = content_size * logo_scale
  plate_padding = logo_size * 0.13
  plate = QRectF(
    qr_rect.center().x() - logo_size / 2 - plate_padding,
    qr_rect.center().y() - logo_size / 2 - plate_padding,
    logo_size + plate_padding * 2,
    logo_size + plate_padding * 2,
  )
  painter.setPen(Qt.PenStyle.NoPen)
  painter.setBrush(background)
  painter.drawRoundedRect(plate, plate.width() * 0.15, plate.height() * 0.15)

  scaled = logo.scaled(
    max(1, round(logo_size)),
    max(1, round(logo_size)),
    Qt.AspectRatioMode.KeepAspectRatio,
    Qt.TransformationMode.SmoothTransformation,
  )
  target = QRectF(
    qr_rect.center().x() - scaled.width() / 2,
    qr_rect.center().y() - scaled.height() / 2,
    scaled.width(),
    scaled.height(),
  )
  painter.drawImage(target, scaled)


def _opaque_color(value: str, name: str) -> QColor:
  color = QColor(value)
  if not color.isValid():
    raise QrCodeError(f"Choose a valid {name} color.")
  color.setAlpha(255)
  return color


def _relative_luminance(color: QColor) -> float:
  channels = []
  for channel in (color.redF(), color.greenF(), color.blueF()):
    if channel <= 0.04045:
      channels.append(channel / 12.92)
    else:
      channels.append(math.pow((channel + 0.055) / 1.055, 2.4))
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _validate_size(size: int) -> None:
  if size < 128 or size > 4096:
    raise QrCodeError("Output size must be between 128 and 4096 pixels.")
