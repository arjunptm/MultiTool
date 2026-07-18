import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


class QrCodePageTests(unittest.TestCase):
  @classmethod
  def setUpClass(cls) -> None:
    cls.app = QApplication.instance() or QApplication([])
    cls.window = MainWindow()
    cls.page = cls.window._tool_pages["qr_code"]

  def setUp(self) -> None:
    self.page.url_input.clear()
    self.page._reset_design()
    self.app.processEvents()

  def test_valid_url_enables_export_and_normalizes_payload(self) -> None:
    self.page.url_input.setText("example.com")
    self.page._refresh_preview()
    self.assertTrue(self.page.save_button.isEnabled())
    self.assertEqual(self.page._validated_design.url, "https://example.com")

  def test_invalid_url_disables_export(self) -> None:
    self.page.url_input.setText("ftp://example.com")
    self.page._refresh_preview()
    self.assertFalse(self.page.save_button.isEnabled())
    self.assertFalse(self.page.url_error.isHidden())

  def test_svg_selection_disables_png_size(self) -> None:
    self.page.format_combo.setCurrentText("SVG")
    self.assertFalse(self.page.size_combo.isEnabled())
    self.page.format_combo.setCurrentText("PNG")
    self.assertTrue(self.page.size_combo.isEnabled())

  def test_surprise_me_preserves_url_and_logo(self) -> None:
    self.page.url_input.setText("https://example.com/path")
    logo = self._logo_bytes()
    self.page.logo_bytes = logo
    self.page._surprise_me()
    self.assertEqual(self.page.url_input.text(), "https://example.com/path")
    self.assertEqual(self.page.logo_bytes, logo)

  def test_reset_restores_defaults_and_clears_logo(self) -> None:
    self.page.logo_bytes = self._logo_bytes()
    self.page.frame_buttons["ticket"].click()
    self.page.module_buttons["dots"].click()
    self.page._reset_design()
    self.assertEqual(self.page.frame_style, "none")
    self.assertEqual(self.page.module_style, "square")
    self.assertEqual(self.page.logo_bytes, b"")

  def test_narrow_page_switches_splitter_to_vertical(self) -> None:
    self.window.open_tool("qr_code")
    self.window.resize(760, 900)
    self.window.show()
    self.app.processEvents()
    self.assertEqual(self.page.splitter.orientation(), Qt.Orientation.Vertical)
    self.window.hide()

  def _logo_bytes(self) -> bytes:
    image = QImage(24, 24, QImage.Format.Format_ARGB32)
    image.fill(QColor("#2563eb"))
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(byte_array)


if __name__ == "__main__":
  unittest.main()
