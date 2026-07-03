import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import fitz
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QImage, QPainter


@dataclass(frozen=True)
class RenderedPdfPage:
  """
  Rendered page data for the Sign PDF preview.

  pdf_width and pdf_height are in PDF points. image_width and image_height are
  pixels from the rendered preview image.
  """
  png_bytes: bytes
  pdf_width: float
  pdf_height: float
  image_width: int
  image_height: int


@dataclass(frozen=True)
class SignaturePlacement:
  """
  Visual signature placement in PDF page coordinates.
  """
  x: float
  y: float
  width: float
  height: float
  rotation_degrees: float = 0


@dataclass(frozen=True)
class SignatureStamp:
  """
  One visual signature image to place on one PDF page.
  """
  page_index: int
  signature_png_bytes: bytes
  signature_placement: SignaturePlacement


@dataclass(frozen=True)
class TextStamp:
  """
  One visual text value to place on one PDF page.
  """
  page_index: int
  text: str
  placement: SignaturePlacement
  font_size: float = 12


def render_pdf_page(
  pdf_path: str,
  page_index: int,
  dpi: int = 144,
) -> RenderedPdfPage:
  """
  Render a single PDF page to PNG bytes for visual placement.
  """
  path = Path(pdf_path)
  if not path.exists():
    raise FileNotFoundError(f"File not found: {pdf_path}")

  if dpi < 72:
    raise ValueError("dpi must be at least 72.")

  document = fitz.open(str(path))
  try:
    if page_index < 0 or page_index >= document.page_count:
      raise IndexError("Page index is out of range.")

    page = document.load_page(page_index)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)

    return RenderedPdfPage(
      png_bytes=pixmap.tobytes("png"),
      pdf_width=page.rect.width,
      pdf_height=page.rect.height,
      image_width=pixmap.width,
      image_height=pixmap.height,
    )
  finally:
    document.close()


def get_pdf_page_count(pdf_path: str) -> int:
  """
  Return the number of pages in a PDF.
  """
  path = Path(pdf_path)
  if not path.exists():
    raise FileNotFoundError(f"File not found: {pdf_path}")

  document = fitz.open(str(path))
  try:
    return document.page_count
  finally:
    document.close()


def add_signature_to_pdf(
  input_pdf_path: str,
  output_pdf_path: str,
  page_index: int,
  signature_png_bytes: bytes,
  signature_placement: SignaturePlacement,
) -> None:
  """
  Insert a visual signature image into a PDF page.
  """
  input_path = Path(input_pdf_path)
  if not input_path.exists():
    raise FileNotFoundError(f"File not found: {input_pdf_path}")

  if not signature_png_bytes:
    raise ValueError("No signature image was provided.")

  output_path = Path(output_pdf_path)
  output_path.parent.mkdir(parents=True, exist_ok=True)

  if signature_placement.width <= 0 or signature_placement.height <= 0:
    raise ValueError("Signature placement must have a positive size.")

  image_bytes, image_rect = _render_signature_for_pdf(
    signature_png_bytes,
    signature_placement,
  )

  document = fitz.open(str(input_path))
  try:
    if page_index < 0 or page_index >= document.page_count:
      raise IndexError("Page index is out of range.")

    page = document.load_page(page_index)
    rect = fitz.Rect(
      image_rect.x(),
      image_rect.y(),
      image_rect.x() + image_rect.width(),
      image_rect.y() + image_rect.height(),
    )

    if not page.rect.intersects(rect):
      raise ValueError("Signature placement is outside the selected page.")

    rect = rect & page.rect
    page.insert_image(rect, stream=image_bytes, keep_proportion=False)
    document.save(str(output_path), garbage=4, deflate=True)
  finally:
    document.close()


def add_signatures_to_pdf(
  input_pdf_path: str,
  output_pdf_path: str,
  signature_stamps: Sequence[SignatureStamp],
  text_stamps: Sequence[TextStamp] | None = None,
) -> None:
  """
  Insert multiple visual signature images and text values into a PDF.
  """
  input_path = Path(input_pdf_path)
  if not input_path.exists():
    raise FileNotFoundError(f"File not found: {input_pdf_path}")

  text_stamps = text_stamps or []

  if not signature_stamps and not text_stamps:
    raise ValueError("No signatures or text fields were provided.")

  output_path = Path(output_pdf_path)
  output_path.parent.mkdir(parents=True, exist_ok=True)

  document = fitz.open(str(input_path))
  try:
    for stamp in signature_stamps:
      if not stamp.signature_png_bytes:
        raise ValueError("A signature image was empty.")

      placement = stamp.signature_placement
      if placement.width <= 0 or placement.height <= 0:
        raise ValueError("Signature placement must have a positive size.")

      if stamp.page_index < 0 or stamp.page_index >= document.page_count:
        raise IndexError("Page index is out of range.")

      image_bytes, image_rect = _render_signature_for_pdf(
        stamp.signature_png_bytes,
        placement,
      )

      page = document.load_page(stamp.page_index)
      rect = fitz.Rect(
        image_rect.x(),
        image_rect.y(),
        image_rect.x() + image_rect.width(),
        image_rect.y() + image_rect.height(),
      )

      if not page.rect.intersects(rect):
        raise ValueError("Signature placement is outside the selected page.")

      rect = rect & page.rect
      page.insert_image(rect, stream=image_bytes, keep_proportion=False)

    for stamp in text_stamps:
      if not stamp.text.strip():
        raise ValueError("A text field was empty.")

      placement = stamp.placement
      if placement.width <= 0 or placement.height <= 0:
        raise ValueError("Text field placement must have a positive size.")

      if stamp.page_index < 0 or stamp.page_index >= document.page_count:
        raise IndexError("Page index is out of range.")

      page = document.load_page(stamp.page_index)
      rect = fitz.Rect(
        placement.x,
        placement.y,
        placement.x + placement.width,
        placement.y + placement.height,
      )

      if not page.rect.intersects(rect):
        raise ValueError("Text field placement is outside the selected page.")

      rect = rect & page.rect
      page.insert_text(
        fitz.Point(rect.x0 + 2, rect.y0 + max(1, stamp.font_size)),
        stamp.text,
        fontsize=stamp.font_size,
        fontname="helv",
        color=(0, 0, 0),
      )

    document.save(str(output_path), garbage=4, deflate=True)
  finally:
    document.close()


def _render_signature_for_pdf(
  signature_png_bytes: bytes,
  placement: SignaturePlacement,
  dpi: int = 144,
) -> tuple[bytes, QRectF]:
  """
  Render the signature at its selected size and rotation.

  The returned QRectF is the transparent image's bounding box in PDF points.
  """
  image = QImage()
  if not image.loadFromData(signature_png_bytes, "PNG"):
    raise ValueError("Signature image could not be loaded.")

  scale = dpi / 72.0
  target_width = max(1, round(placement.width * scale))
  target_height = max(1, round(placement.height * scale))
  scaled_image = image.scaled(
    target_width,
    target_height,
    Qt.AspectRatioMode.IgnoreAspectRatio,
    Qt.TransformationMode.SmoothTransformation,
  )

  angle = math.radians(placement.rotation_degrees)
  rotated_width = max(
    1,
    math.ceil(abs(target_width * math.cos(angle)) + abs(target_height * math.sin(angle))),
  )
  rotated_height = max(
    1,
    math.ceil(abs(target_width * math.sin(angle)) + abs(target_height * math.cos(angle))),
  )

  output = QImage(rotated_width, rotated_height, QImage.Format.Format_ARGB32)
  output.fill(Qt.GlobalColor.transparent)

  painter = QPainter(output)
  painter.setRenderHint(QPainter.RenderHint.Antialiasing)
  painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
  painter.translate(rotated_width / 2, rotated_height / 2)
  painter.rotate(placement.rotation_degrees)
  painter.drawImage(
    round(-target_width / 2),
    round(-target_height / 2),
    scaled_image,
  )
  painter.end()

  byte_array = QByteArray()
  buffer = QBuffer(byte_array)
  buffer.open(QIODevice.OpenModeFlag.WriteOnly)
  output.save(buffer, "PNG")

  center_x = placement.x + placement.width / 2
  center_y = placement.y + placement.height / 2
  output_width = rotated_width / scale
  output_height = rotated_height / scale
  rect = QRectF(
    center_x - output_width / 2,
    center_y - output_height / 2,
    output_width,
    output_height,
  )

  return bytes(byte_array), rect
