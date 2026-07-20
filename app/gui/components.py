import logging
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QLineEdit, QFileDialog, QFrame, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox
)

logger = logging.getLogger("CucumberStudioImporter")

class DragDropZone(QFrame):
    """
    A stylish dashed-border frame that accepts drag-and-drop files or folders.
    Emits a signal containing the list of resolved file paths.
    """
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DragDropZone")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel("Drag & Drop TXT files or Folders here\n- or -\nClick to Browse", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # Initial style setup
        self.update_style("normal")

    def _get_theme_colors(self) -> dict:
        main_win = self.window()
        is_light = getattr(main_win, "is_light_theme", False)
        if is_light:
            return {
                "border": "#198754",
                "bg": "#e8f5ed",
                "drag_border": "#0f5132",
                "drag_bg": "#badbcc",
                "text": "#1e352f"
            }
        else:
            return {
                "border": "#3b82f6",
                "bg": "#111827",
                "drag_border": "#10b981",
                "drag_bg": "#064e3b",
                "text": "#94a3b8"
            }

    def update_style(self, state: str = "normal"):
        colors = self._get_theme_colors()
        self.label.setStyleSheet(f"color: {colors['text']}; font-weight: 600; font-size: 14px;")
        
        border_color = colors["drag_border"] if state == "drag" else colors["border"]
        bg_color = colors["drag_bg"] if state == "drag" else colors["bg"]
        
        self.setStyleSheet(f"""
            QFrame#DragDropZone {{
                border: 2px dashed {border_color};
                border-radius: 8px;
                background-color: {bg_color};
            }}
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.update_style("drag")

    def dragLeaveEvent(self, event):
        self.update_style("normal")

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        self.update_style("normal")
        urls = event.mimeData().urls()
        dropped_paths = []
        for url in urls:
            local_path = Path(url.toLocalFile())
            if local_path.exists():
                dropped_paths.append(local_path)
        
        if dropped_paths:
            self.filesDropped.emit(dropped_paths)
            event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Trigger folder/file selection dialogue
            dialog = QFileDialog(self)
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dialog.setNameFilter("Text Files (*.txt)")
            if dialog.exec():
                selected_files = [Path(f) for f in dialog.selectedFiles()]
                if selected_files:
                    self.filesDropped.emit(selected_files)


class LogViewer(QWidget):
    """
    Live console logging display with filtering/searching and log export capabilities.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_logs = []  # Maintain all log strings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Search bar and Action Buttons layout
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)
        
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search / filter logs...")
        self.search_bar.textChanged.connect(self.filter_logs)
        top_layout.addWidget(self.search_bar)

        self.btn_export = QPushButton("Export Log", self)
        self.btn_export.clicked.connect(self.export_logs)
        top_layout.addWidget(self.btn_export)

        self.btn_clear = QPushButton("Clear", self)
        self.btn_clear.clicked.connect(self.clear_logs)
        top_layout.addWidget(self.btn_clear)

        layout.addLayout(top_layout)

        # Log textbox
        self.console = QTextEdit(self)
        self.console.setObjectName("console_view")
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.console)

    def update_theme_style(self, is_light: bool):
        if is_light:
            self.console.setStyleSheet("background-color: #ffffff; color: #0f5132; border: 1px solid #badbcc;")
            self.search_bar.setStyleSheet("background-color: #ffffff; color: #1e352f; border: 1px solid #badbcc;")
        else:
            self.console.setStyleSheet("background-color: #0c0d12; color: #38bdf8; border: 1px solid #1e293b;")
            self.search_bar.setStyleSheet("background-color: #0f111a; color: #ffffff; border: 1px solid #2e384d;")

    def append_log(self, text: str):
        cleaned_text = text.strip()
        if not cleaned_text:
            return
            
        self.raw_logs.append(cleaned_text)
        
        # Check if matches current filter
        filter_text = self.search_bar.text().strip().lower()
        if not filter_text or filter_text in cleaned_text.lower():
            self.console.append(cleaned_text)
            
            # Auto scroll to bottom
            scrollbar = self.console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def filter_logs(self):
        filter_text = self.search_bar.text().strip().lower()
        self.console.clear()
        
        # Filter raw logs array
        filtered_lines = [line for line in self.raw_logs if not filter_text or filter_text in line.lower()]
        self.console.setPlainText("\n".join(filtered_lines))
        
        # Scroll to bottom
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        self.raw_logs.clear()
        self.console.clear()

    def export_logs(self):
        if not self.raw_logs:
            QMessageBox.information(self, "Export Log", "No logs available to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log File", str(Path.home() / "cucumber_import.log"), "Log Files (*.log);;Text Files (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(self.raw_logs))
                QMessageBox.information(self, "Export Log", "Logs successfully exported.")
            except Exception as e:
                QMessageBox.critical(self, "Export Log Failed", f"Could not write log file: {e}")


class QueueManager(QWidget):
    """
    Queue list manager showing queued scenario files, their size, and execution status.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Table Setup
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["File Name", "Size (bytes)", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 120)
        layout.addWidget(self.table)
        
        self.file_paths = []

    def update_theme_style(self, is_light: bool):
        if is_light:
            self.table.setStyleSheet("background-color: #ffffff; color: #1e352f; border: 1px solid #badbcc; gridline-color: #c7dfd3;")
            self.table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #e8f5ed; color: #1e352f; border: 1px solid #badbcc; font-weight: bold; }")
        else:
            self.table.setStyleSheet("background-color: #0f111a; color: #ffffff; border: 1px solid #2e384d; gridline-color: #1e293b;")
            self.table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #1e293b; color: #cbd5e1; border: 1px solid #2e384d; font-weight: bold; }")

    def set_queue(self, paths: list[Path]):
        """Sets the files queue table."""
        self.table.setRowCount(0)
        self.file_paths = []
        
        for idx, path in enumerate(paths):
            if path.suffix.lower() == ".txt":
                self.file_paths.append(path)
                
                # Rows insertion
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # File Name item
                name_item = QTableWidgetItem(path.name)
                name_item.setToolTip(str(path))
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Size item
                size = path.stat().st_size if path.exists() else 0
                size_item = QTableWidgetItem(f"{size:,}")
                size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                # Status item
                status_item = QTableWidgetItem("Pending")
                status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, size_item)
                self.table.setItem(row, 2, status_item)

    def update_status(self, file_name: str, status: str):
        """Updates the status of a specific file in the queue."""
        from PySide6.QtGui import QColor
        main_win = self.window()
        is_light = getattr(main_win, "is_light_theme", False)

        if is_light:
            color_map = {
                "Importing": QColor("#b38600"),  # Dark Amber
                "Completed": QColor("#198754"),  # Emerald Green
                "Failed": QColor("#dc3545")      # Dark Red
            }
        else:
            color_map = {
                "Importing": QColor("#ffc107"),  # Gold
                "Completed": QColor("#10b981"),  # Bright Emerald
                "Failed": QColor("#ef4444")      # Bright Red
            }

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == file_name:
                status_item = self.table.item(row, 2)
                if status_item:
                    status_item.setText(status)
                    if status in color_map:
                        status_item.setForeground(color_map[status])
                    break

    def get_files(self) -> list[Path]:
        return self.file_paths

    def clear(self):
        self.table.setRowCount(0)
        self.file_paths.clear()
