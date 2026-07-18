import os
import unittest
import xml.etree.ElementTree as ElementTree

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.tools.qr_code.service import (
  EYE_STYLES,
  FRAME_STYLES,
  MODULE_STYLES,
  QrCodeDesign,
  QrCodeError,
  build_matrix,
  contrast_ratio,
  normalize_url,
  render_qr_image,
  render_qr_png,
  render_qr_svg,
  suggested_filename,
  validate_design,
)


class QrCodeServiceTests(unittest.TestCase):
  @classmethod
  def setUpClass(cls) -> None:
    cls.app = QApplication.instance() or QApplication([])

  def test_normalize_url_adds_https_and_normalizes_host(self) -> None:
    self.assertEqual(
      normalize_url(" Example.COM/path?q=1 "),
      "https://example.com/path?q=1",
    )

  def test_normalize_url_rejects_blank_and_unsupported_values(self) -> None:
    invalid_values = ("", "ftp://example.com", "https://", "not-a-host", "https://bad host.com")
    for value in invalid_values:
      with self.subTest(value=value), self.assertRaises(QrCodeError):
        normalize_url(value)

  def test_matrix_is_deterministic_and_keeps_four_module_quiet_zone(self) -> None:
    first = build_matrix("example.com")
    second = build_matrix("https://example.com")
    self.assertEqual(first, second)
    self.assertTrue(all(not value for row in first[:4] for value in row))
    self.assertTrue(all(not value for row in first[-4:] for value in row))
    self.assertTrue(all(not row[column] for row in first for column in range(4)))
    self.assertTrue(all(not row[column] for row in first for column in range(len(first) - 4, len(first))))

  def test_long_url_reports_capacity_error(self) -> None:
    with self.assertRaisesRegex(QrCodeError, "too long"):
      build_matrix("https://example.com/" + "x" * 5000)

  def test_design_rejects_low_contrast_and_light_foreground(self) -> None:
    with self.assertRaisesRegex(QrCodeError, "contrast"):
      validate_design(QrCodeDesign("example.com", "#777777", "#888888"))
    with self.assertRaisesRegex(QrCodeError, "darker"):
      validate_design(QrCodeDesign("example.com", "#ffffff", "#111827"))

  def test_contrast_ratio_matches_black_and_white(self) -> None:
    self.assertAlmostEqual(contrast_ratio("#000000", "#ffffff"), 21.0, places=1)

  def test_every_curated_style_renders(self) -> None:
    for style in MODULE_STYLES:
      with self.subTest(module_style=style):
        image = render_qr_image(QrCodeDesign("example.com", module_style=style), 256)
        self.assertEqual((image.width(), image.height()), (256, 256))
    for style in EYE_STYLES:
      with self.subTest(eye_style=style):
        image = render_qr_image(QrCodeDesign("example.com", eye_style=style), 256)
        self.assertFalse(image.isNull())
    for style in FRAME_STYLES:
      with self.subTest(frame_style=style):
        image = render_qr_image(QrCodeDesign("example.com", frame_style=style), 256)
        self.assertFalse(image.isNull())

  def test_png_output_has_signature_and_requested_dimensions(self) -> None:
    output = render_qr_png(QrCodeDesign("example.com", frame_style="ticket"), 512)
    self.assertTrue(output.startswith(b"\x89PNG\r\n\x1a\n"))
    image = QImage.fromData(output, "PNG")
    self.assertEqual((image.width(), image.height()), (512, 512))

  def test_svg_is_valid_xml_and_escapes_frame_text(self) -> None:
    output = render_qr_svg(
      QrCodeDesign("example.com", frame_style="rounded_label", frame_text="Scan A&B <now>"),
      512,
    )
    self.assertIn(b"<svg", output)
    ElementTree.fromstring(output)
    self.assertIn(b"A&amp;B", output)

  def test_svg_embeds_uploaded_raster_logo(self) -> None:
    output = render_qr_svg(QrCodeDesign("example.com", logo_bytes=self._logo_bytes()), 512)
    ElementTree.fromstring(output)
    self.assertIn(b"<image", output)

  def test_invalid_logo_and_logo_scale_are_rejected(self) -> None:
    with self.assertRaisesRegex(QrCodeError, "readable image"):
      validate_design(QrCodeDesign("example.com", logo_bytes=b"not-an-image"))
    with self.assertRaisesRegex(QrCodeError, "between 10% and 18%"):
      validate_design(QrCodeDesign("example.com", logo_scale=0.25))

  def test_suggested_filename_uses_safe_hostname(self) -> None:
    self.assertEqual(suggested_filename("https://www.example.com/path", "PNG"), "www-example-com-qr.png")

  def _logo_bytes(self) -> bytes:
    image = QImage(48, 48, QImage.Format.Format_ARGB32)
    image.fill(QColor("#2563eb"))
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(byte_array)


if __name__ == "__main__":
  unittest.main()
