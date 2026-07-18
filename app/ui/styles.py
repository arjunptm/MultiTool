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

QFrame#qrSectionCard,
QFrame#previewCard {
  background: #ffffff;
  border: 1px solid #d7deea;
  border-radius: 10px;
}

QLabel#miniSectionTitle {
  color: #111827;
  font-size: 13px;
  font-weight: 700;
}

QLabel#inlineError {
  color: #b91c1c;
  font-size: 12px;
}

QLabel#safetyGood,
QLabel#safetyError,
QLabel#safetyNeutral {
  border-radius: 8px;
  padding: 8px;
  font-size: 12px;
  font-weight: 600;
}

QLabel#safetyGood {
  color: #166534;
  background: #dcfce7;
}

QLabel#safetyError {
  color: #991b1b;
  background: #fee2e2;
}

QLabel#safetyNeutral {
  color: #475569;
  background: #f1f5f9;
}

QLabel#qrPreview,
QLabel#logoPreview {
  color: #64748b;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

QFrame#uploadZone {
  background: #f8fafc;
  border: 2px dashed #94a3b8;
  border-radius: 10px;
}

QFrame#uploadZone:hover {
  background: #eff6ff;
  border-color: #2563eb;
}

QLabel#uploadTitle {
  color: #1d4ed8;
  font-weight: 600;
}

QLineEdit#qrInput,
QComboBox#qrCombo {
  color: #111827;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 9px 10px;
  selection-background-color: #2563eb;
}

QLineEdit#qrInput:focus,
QComboBox#qrCombo:focus {
  border: 2px solid #2563eb;
  padding: 8px 9px;
}

QAbstractItemView#qrComboPopup {
  color: #111827;
  background: #ffffff;
  border: 1px solid #94a3b8;
  outline: none;
  selection-color: #1d4ed8;
  selection-background-color: #dbeafe;
}

QAbstractItemView#qrComboPopup::item {
  min-height: 28px;
  padding: 4px 8px;
}

QAbstractItemView#qrComboPopup::item:hover,
QAbstractItemView#qrComboPopup::item:selected {
  color: #1d4ed8;
  background: #dbeafe;
}

QTabWidget#qrDesignTabs::pane {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

QTabWidget#qrDesignTabs QTabBar::tab {
  color: #64748b;
  background: transparent;
  padding: 9px 13px;
  font-weight: 600;
}

QTabWidget#qrDesignTabs QTabBar::tab:selected {
  color: #1d4ed8;
  border-bottom: 2px solid #2563eb;
}

QToolButton#presetTile {
  color: #334155;
  background: #ffffff;
  border: 1px solid #dbe2ea;
  border-radius: 8px;
  padding: 5px;
  font-size: 11px;
  font-weight: 600;
}

QToolButton#presetTile:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

QToolButton#presetTile:checked {
  color: #1d4ed8;
  background: #eff6ff;
  border: 2px solid #2563eb;
  padding: 4px;
}

QPushButton#saveQrButton {
  background: #16a34a;
}

QPushButton#saveQrButton:hover {
  background: #15803d;
}

QPushButton#saveQrButton:disabled {
  color: #94a3b8;
  background: #e2e8f0;
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

QMessageBox {
  background: #ffffff;
}

QMessageBox QLabel {
  color: #1f2937;
  font-size: 14px;
}

QMessageBox QPushButton {
  min-width: 72px;
}
"""
