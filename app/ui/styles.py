APP_STYLESHEET = """
QMainWindow {
  background: #f5f7fb;
}

QLabel {
  color: #1f2937;
  font-size: 14px;
}

QLabel#appHeader {
  font-size: 26px;
  font-weight: 700;
  color: #111827;
}

QLabel#sectionTitle {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

QLabel#pageTitle {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}

QLabel#pageSubtitle {
  font-size: 13px;
  color: #4b5563;
}

QFrame#toolCard {
  background: white;
  border: 1px solid #d7deea;
  border-radius: 10px;
}

QPushButton {
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 600;
}

QPushButton:hover {
  background: #1d4ed8;
}

QPushButton:pressed {
  background: #1e40af;
}

QPushButton#secondaryButton {
  background: #e5e7eb;
  color: #111827;
}

QPushButton#secondaryButton:hover {
  background: #d1d5db;
}

QToolButton {
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 600;
}

QToolButton:hover {
  background: #1d4ed8;
}

QToolButton:pressed {
  background: #1e40af;
}

QToolButton::menu-indicator {
  subcontrol-origin: padding;
  subcontrol-position: right center;
  padding-right: 8px;
}

QScrollArea {
  border: none;
  background: transparent;
}
"""