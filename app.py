import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.ui.styles import APP_STYLESHEET


def main() -> int:
  app = QApplication(sys.argv)
  app.setApplicationName("MultiTool")
  app.setStyleSheet(APP_STYLESHEET)

  window = MainWindow()
  window.show()

  return app.exec()


if __name__ == "__main__":
  raise SystemExit(main())