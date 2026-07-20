DARK_QSS = """
/* Global Styles */
QMainWindow, QDialog, QMessageBox {
    background-color: #0f1016;
}

QWidget {
    color: #e2e8f0;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, sans-serif;
    font-size: 13px;
}

/* Header & Panels */
QGroupBox {
    background-color: #161925;
    border: 1px solid #283046;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #38bdf8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 8px;
    background-color: #161925;
    border-radius: 4px;
}

/* Labels */
QLabel {
    color: #94a3b8;
    font-weight: 500;
}

QLabel#lbl_current_file, QLabel#lbl_current_scenario {
    color: #ffffff;
    font-weight: bold;
}

QLabel#partner_label, QLabel#contact_link {
    color: #38bdf8;
    font-weight: bold;
}

/* Input Fields */
QLineEdit {
    background-color: #0f111a;
    border: 1px solid #2e384d;
    border-radius: 5px;
    padding: 6px 10px;
    color: #ffffff;
    selection-background-color: #0ea5e9;
}

QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #131722;
}

QComboBox {
    background-color: #0f111a;
    border: 1px solid #2e384d;
    border-radius: 5px;
    padding: 6px 10px;
    color: #ffffff;
}

QComboBox:focus {
    border: 1px solid #38bdf8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 0px;
}

QComboBox QAbstractItemView {
    background-color: #0f111a;
    border: 1px solid #2e384d;
    selection-background-color: #38bdf8;
    selection-color: #0f1016;
}

QComboBox QAbstractItemView::item {
    padding: 8px 10px;
    border-bottom: 1px solid #283046;
    color: #e2e8f0;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #38bdf8;
    color: #0f1016;
}

/* Buttons */
QPushButton {
    background-color: #1d2438;
    border: 1px solid #3b82f6;
    color: #3b82f6;
    border-radius: 5px;
    padding: 6px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #3b82f6;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #2563eb;
}

QPushButton:disabled {
    background-color: #181c26;
    border: 1px solid #2d313d;
    color: #64748b;
}

/* Primary Accent Buttons (Start) */
QPushButton#btn_start {
    background-color: #1c322b;
    border: 1px solid #10b981;
    color: #10b981;
}

QPushButton#btn_start:hover {
    background-color: #10b981;
    color: #ffffff;
}

QPushButton#btn_start:pressed {
    background-color: #059669;
}

/* Pause Buttons */
QPushButton#btn_pause {
    background-color: #332616;
    border: 1px solid #f59e0b;
    color: #f59e0b;
}

QPushButton#btn_pause:hover {
    background-color: #f59e0b;
    color: #ffffff;
}

QPushButton#btn_pause:pressed {
    background-color: #d97706;
}

/* Stop/Danger Buttons */
QPushButton#btn_stop {
    background-color: #321c21;
    border: 1px solid #ef4444;
    color: #ef4444;
}

QPushButton#btn_stop:hover {
    background-color: #ef4444;
    color: #ffffff;
}

QPushButton#btn_stop:pressed {
    background-color: #dc2626;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #0f111a;
    border: 1px solid #2e384d;
    border-radius: 4px;
}

QCheckBox::indicator:checked {
    background-color: #38bdf8;
    border: 1px solid #38bdf8;
    image: url(app/gui/checkmark.png);
}

/* Slider */
QSlider::groove:horizontal {
    border: 1px solid #2e384d;
    height: 6px;
    background: #0f111a;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #38bdf8;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #38bdf8;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #2e384d;
    border-radius: 5px;
    text-align: center;
    background-color: #0f111a;
    color: #ffffff;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
    border-radius: 4px;
}

/* Log Console & General Text Edits */
QTextEdit, QPlainTextEdit {
    background-color: #0c0d12;
    border: 1px solid #1e293b;
    border-radius: 6px;
    color: #38bdf8;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 8px;
}

/* Table Widget */
QTableWidget {
    background-color: #0f111a;
    border: 1px solid #2e384d;
    gridline-color: #1e293b;
    border-radius: 6px;
    color: #ffffff;
}

QTableWidget::item {
    background-color: #0f111a;
    color: #ffffff;
    padding: 6px;
}

QTableWidget::item:selected {
    background-color: #1d4ed8;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #cbd5e1;
    padding: 6px;
    border: 1px solid #2e384d;
    font-weight: bold;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #0f111a;
    width: 10px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:vertical {
    background: #1e293b;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #334155;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #0f111a;
    height: 10px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background: #1e293b;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #0a0b0f;
    color: #64748b;
    border-top: 1px solid #1e293b;
}

/* Modal Dialogs / QMessageBox Styling */
QMessageBox {
    background-color: #161925;
}

QMessageBox QLabel {
    color: #e2e8f0;
    font-size: 13px;
}

QMessageBox QPushButton {
    background-color: #1d2438;
    border: 1px solid #3b82f6;
    color: #3b82f6;
    border-radius: 4px;
    padding: 5px 15px;
    font-weight: bold;
}

QMessageBox QPushButton:hover {
    background-color: #3b82f6;
    color: #ffffff;
}
"""

LIGHT_QSS = """
/* Global Styles */
QMainWindow, QDialog, QMessageBox {
    background-color: #f0f7f4;
}

QWidget {
    color: #1e352f;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, sans-serif;
    font-size: 13px;
}

/* Header & Panels */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #c7dfd3;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #198754;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 8px;
    background-color: #ffffff;
    border-radius: 4px;
}

/* Labels */
QLabel {
    color: #386b52;
    font-weight: 500;
}

QLabel#lbl_current_file, QLabel#lbl_current_scenario, QLabel#partner_label, QLabel#contact_link {
    color: #198754;
    font-weight: bold;
}

/* Input Fields */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #badbcc;
    border-radius: 5px;
    padding: 6px 10px;
    color: #1e352f;
    selection-background-color: #198754;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #198754;
    background-color: #fcfdfd;
}

QComboBox {
    background-color: #ffffff;
    border: 1px solid #badbcc;
    border-radius: 5px;
    padding: 6px 10px;
    color: #1e352f;
}

QComboBox:focus {
    border: 1px solid #198754;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 0px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #badbcc;
    selection-background-color: #198754;
    selection-color: #ffffff;
}

QComboBox QAbstractItemView::item {
    padding: 8px 10px;
    border-bottom: 1px solid #e8f5ed;
    color: #1e352f;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #198754;
    color: #ffffff;
}

/* Buttons */
QPushButton {
    background-color: #e8f5ed;
    border: 1px solid #198754;
    color: #198754;
    border-radius: 5px;
    padding: 6px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #198754;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #115c36;
}

QPushButton:disabled {
    background-color: #f2f2f2;
    border: 1px solid #dcdcdc;
    color: #a0a0a0;
}

/* Primary Accent Buttons (Start) */
QPushButton#btn_start {
    background-color: #d1e7dd;
    border: 1px solid #198754;
    color: #0f5132;
}

QPushButton#btn_start:hover {
    background-color: #198754;
    color: #ffffff;
}

QPushButton#btn_start:pressed {
    background-color: #0f5132;
}

/* Pause Buttons */
QPushButton#btn_pause {
    background-color: #fff3cd;
    border: 1px solid #ffc107;
    color: #664d03;
}

QPushButton#btn_pause:hover {
    background-color: #ffc107;
    color: #ffffff;
}

QPushButton#btn_pause:pressed {
    background-color: #b38600;
}

/* Stop/Danger Buttons */
QPushButton#btn_stop {
    background-color: #f8d7da;
    border: 1px solid #dc3545;
    color: #842029;
}

QPushButton#btn_stop:hover {
    background-color: #dc3545;
    color: #ffffff;
}

QPushButton#btn_stop:pressed {
    background-color: #842029;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #1e352f;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #ffffff;
    border: 1px solid #198754;
    border-radius: 4px;
}

QCheckBox::indicator:checked {
    background-color: #198754;
    border: 1px solid #198754;
    image: url(app/gui/checkmark.png);
}

/* Slider */
QSlider::groove:horizontal {
    border: 1px solid #badbcc;
    height: 6px;
    background: #ffffff;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #198754;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #198754;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #badbcc;
    border-radius: 5px;
    text-align: center;
    background-color: #ffffff;
    color: #1e352f;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #198754, stop:1 #0f5132);
    border-radius: 4px;
}

/* Log Console & General Text Edits */
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #badbcc;
    border-radius: 6px;
    color: #0f5132;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 8px;
}

/* Table Widget */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #badbcc;
    gridline-color: #c7dfd3;
    border-radius: 6px;
    color: #1e352f;
}

QTableWidget::item {
    background-color: #ffffff;
    color: #1e352f;
    padding: 6px;
}

QTableWidget::item:selected {
    background-color: #d1e7dd;
    color: #0f5132;
}

QHeaderView::section {
    background-color: #e8f5ed;
    color: #1e352f;
    padding: 6px;
    border: 1px solid #badbcc;
    font-weight: bold;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #f0f7f4;
    width: 10px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:vertical {
    background: #badbcc;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #a3cfbb;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #f0f7f4;
    height: 10px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background: #badbcc;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #e8f5ed;
    color: #386b52;
    border-top: 1px solid #c7dfd3;
}

/* Modal Dialogs / QMessageBox Styling */
QMessageBox {
    background-color: #f0f7f4;
}

QMessageBox QLabel {
    color: #1e352f;
    font-size: 13px;
}

QMessageBox QPushButton {
    background-color: #e8f5ed;
    border: 1px solid #198754;
    color: #198754;
    border-radius: 4px;
    padding: 5px 15px;
    font-weight: bold;
}

QMessageBox QPushButton:hover {
    background-color: #198754;
    color: #ffffff;
}
"""

MODERN_QSS = DARK_QSS
