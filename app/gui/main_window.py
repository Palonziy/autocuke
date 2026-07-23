import logging
import os
import time
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot, QCoreApplication
from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, 
    QProgressBar, QGroupBox, QRadioButton, QSlider, QStatusBar, 
    QMessageBox, QFileDialog, QSplitter
)

from app.config import settings
from app.utils.crypto import save_credentials, load_credentials, clear_credentials
from app.utils.logger import setup_logger
from app.services.importer import ImportWorker
from app.gui.components import DragDropZone, LogViewer, QueueManager
from app.gui.styles import DARK_QSS, LIGHT_QSS

logger = logging.getLogger("AutoCuke")
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).resolve().parent.parent.parent
    return str(base_path / relative_path)

def generate_checkmark_png():
    try:
        from PySide6.QtGui import QPainter, QPen, QColor, QImage
        from PySide6.QtCore import Qt
        path = Path(resource_path("app/gui/checkmark.png"))
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            img = QImage(32, 32, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            pen = QPen(QColor("#ffffff"))
            pen.setWidth(4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            
            painter.drawLine(8, 16, 14, 22)
            painter.drawLine(14, 22, 25, 9)
            painter.end()
            
            img.save(str(path))
            logger.info("Generated checkmark icon PNG successfully.")
    except Exception as e:
        logger.error(f"Failed to generate checkmark PNG: {e}")

class MainWindow(QMainWindow):
    # Thread-safe Qt Signal to route logging entries from any thread into the UI
    ui_log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.worker = None
        self.is_light_theme = False
        generate_checkmark_png()
        
        # Resolve assets using PyInstaller-safe resource_path
        self.checkmark_path = resource_path("app/gui/checkmark.png").replace("\\", "/")
        self.formatted_dark_qss = DARK_QSS.replace("url(app/gui/checkmark.png)", f"url({self.checkmark_path})")
        self.formatted_light_qss = LIGHT_QSS.replace("url(app/gui/checkmark.png)", f"url({self.checkmark_path})")
        
        # Configure Main Window Properties
        self.setWindowTitle("AutoCuke - Scenario Importer")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)
        
        # Set Window Icon (Favicon)
        self.setWindowIcon(QIcon(resource_path("app/gui/favicon.png")))
        self.setStyleSheet(self.formatted_dark_qss)

        # Connect logging signal thread-safely
        self.ui_log_signal.connect(self.append_log_to_viewer)
        setup_logger(ui_callback=self.ui_log_signal.emit)

        # Initialize UI Components
        self.init_ui()
        self.log_viewer.update_theme_style(False)
        self.queue_manager.update_theme_style(False)

        # Load Saved Credentials or Env fallback
        self.load_initial_credentials()

        # Install Keyboard Shortcuts
        self.setup_shortcuts()

        logger.info("Application initialized. Ready.")

    def init_ui(self):
        # Main Central Widget and Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Splitter to allow resizing left panel (controls) and right panel (logs/queue)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # LEFT PANEL - Configuration & Control Group
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Brand Header (Logo, Title, and Theme Toggle)
        brand_widget = QWidget()
        brand_layout = QHBoxLayout(brand_widget)
        brand_layout.setContentsMargins(5, 5, 5, 5)
        brand_layout.setSpacing(10)
        
        # Logo Label
        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("app/gui/logo.png")).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        brand_layout.addWidget(logo_label)
        
        # Title Label
        title_label = QLabel("AutoCuke")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #10b981;")
        brand_layout.addWidget(title_label)
        
        brand_layout.addStretch()
        
        # Theme toggle button
        self.btn_theme = QPushButton("Light Mode")
        self.btn_theme.setFixedWidth(100)
        self.btn_theme.clicked.connect(self.toggle_theme)
        brand_layout.addWidget(self.btn_theme)
        
        left_layout.addWidget(brand_widget)
        
        # 1. Login Section
        login_group = QGroupBox("1. Authentication")
        login_grid = QGridLayout(login_group)
        login_grid.setSpacing(8)
        
        login_grid.addWidget(QLabel("Email:"), 0, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your-email@example.com")
        login_grid.addWidget(self.email_input, 0, 1)

        login_grid.addWidget(QLabel("Password:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password")
        login_grid.addWidget(self.password_input, 1, 1)

        self.remember_me_cb = QCheckBox("Remember Me")
        login_grid.addWidget(self.remember_me_cb, 2, 1)

        self.btn_test_conn = QPushButton("Test Connection")
        self.btn_test_conn.clicked.connect(self.test_connection)
        login_grid.addWidget(self.btn_test_conn, 3, 1)
        
        left_layout.addWidget(login_group)

        # 2. Project Selection
        project_group = QGroupBox("2. Target Project")
        project_hbox = QHBoxLayout(project_group)
        
        self.project_combo = QComboBox()
        self.project_combo.setPlaceholderText("Fetch projects...")
        project_hbox.addWidget(self.project_combo, 4)

        self.btn_refresh_projects = QPushButton("Refresh")
        self.btn_refresh_projects.clicked.connect(self.test_connection)
        project_hbox.addWidget(self.btn_refresh_projects, 1)
        
        left_layout.addWidget(project_group)

        # 3. Browser Preferences
        browser_group = QGroupBox("3. Browser Configuration")
        browser_layout = QGridLayout(browser_group)
        browser_layout.setSpacing(8)

        self.radio_headless = QRadioButton("Headless (Background)")
        self.radio_visible = QRadioButton("Visible (Interactive)")
        self.radio_headless.setChecked(True)
        
        browser_layout.addWidget(self.radio_headless, 0, 0)
        browser_layout.addWidget(self.radio_visible, 0, 1)

        # Speed slider
        browser_layout.addWidget(QLabel("Typing Speed Delay:"), 1, 0)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(20)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setValue(50)
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed_slider.setTickInterval(30)
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        browser_layout.addWidget(self.speed_slider, 1, 1)

        self.speed_lbl = QLabel("50 ms")
        browser_layout.addWidget(self.speed_lbl, 1, 2)
        
        left_layout.addWidget(browser_group)

        # 4. Execution Controls
        exec_group = QGroupBox("4. Automation Actions")
        exec_grid = QGridLayout(exec_group)
        exec_grid.setSpacing(10)

        self.btn_start = QPushButton("Start Import")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.start_import)
        exec_grid.addWidget(self.btn_start, 0, 0, 1, 2)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setObjectName("btn_pause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.pause_import)
        exec_grid.addWidget(self.btn_pause, 1, 0)

        self.btn_resume = QPushButton("Resume")
        self.btn_resume.setEnabled(False)
        self.btn_resume.clicked.connect(self.resume_import)
        exec_grid.addWidget(self.btn_resume, 1, 1)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_import)
        exec_grid.addWidget(self.btn_stop, 2, 0, 1, 2)
        
        left_layout.addWidget(exec_group)
        
        left_layout.addStretch()
        
        # Support / Contact Widget
        support_group = QGroupBox("Support & Help")
        support_layout = QVBoxLayout(support_group)
        support_layout.setContentsMargins(12, 10, 12, 10)
        support_layout.setSpacing(4)
        
        support_text = QLabel("If you encounter any issues, please contact:")
        support_text.setWordWrap(True)
        support_text.setStyleSheet("font-size: 11px; color: #64748b;")
        
        self.contact_link = QLabel("<a href='mailto:hello@palosite.com' style='color: inherit; text-decoration: none;'>hello@palosite.com</a>")
        self.contact_link.setOpenExternalLinks(True)
        self.contact_link.setObjectName("contact_link")
        self.contact_link.setStyleSheet("font-size: 12px; font-weight: bold;")
        
        support_layout.addWidget(support_text)
        support_layout.addWidget(self.contact_link)
        left_layout.addWidget(support_group)
        
        splitter.addWidget(left_widget)

        # RIGHT PANEL - Files Queue & Console log
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 1. Queue manager
        queue_group = QGroupBox("Queue Manager")
        queue_vbox = QVBoxLayout(queue_group)
        
        self.drag_drop_zone = DragDropZone(self)
        self.drag_drop_zone.filesDropped.connect(self.handle_files_dropped)
        queue_vbox.addWidget(self.drag_drop_zone, 1)

        # Buttons to manually browse files / folders / clear queue
        browse_layout = QHBoxLayout()
        self.btn_browse_files = QPushButton("Browse Files")
        self.btn_browse_files.clicked.connect(self.browse_files)
        browse_layout.addWidget(self.btn_browse_files)

        self.btn_browse_folder = QPushButton("Browse Folder")
        self.btn_browse_folder.clicked.connect(self.browse_folder)
        browse_layout.addWidget(self.btn_browse_folder)

        self.btn_clear_queue = QPushButton("Clear Queue")
        self.btn_clear_queue.clicked.connect(self.clear_queue)
        browse_layout.addWidget(self.btn_clear_queue)

        self.btn_info = QPushButton("ℹ️ Format Tips")
        self.btn_info.setObjectName("btn_info")
        self.btn_info.clicked.connect(self.show_format_help)
        browse_layout.addWidget(self.btn_info)
        
        queue_vbox.addLayout(browse_layout)

        self.queue_manager = QueueManager(self)
        queue_vbox.addWidget(self.queue_manager, 2)
        
        right_layout.addWidget(queue_group, 2)

        # 2. Progress Tracker
        progress_group = QGroupBox("Live Execution Progress")
        progress_layout = QGridLayout(progress_group)
        progress_layout.setSpacing(8)

        progress_layout.addWidget(QLabel("Current File:"), 0, 0)
        self.lbl_current_file = QLabel("-")
        self.lbl_current_file.setObjectName("lbl_current_file")
        progress_layout.addWidget(self.lbl_current_file, 0, 1)

        progress_layout.addWidget(QLabel("Current Scenario:"), 0, 2)
        self.lbl_current_scenario = QLabel("-")
        self.lbl_current_scenario.setObjectName("lbl_current_scenario")
        progress_layout.addWidget(self.lbl_current_scenario, 0, 3)

        progress_layout.addWidget(QLabel("Import Progress:"), 1, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar, 1, 1, 1, 3)

        progress_layout.addWidget(QLabel("Time Elapsed:"), 2, 0)
        self.lbl_elapsed = QLabel("00:00:00")
        progress_layout.addWidget(self.lbl_elapsed, 2, 1)

        progress_layout.addWidget(QLabel("Estimated ETA:"), 2, 2)
        self.lbl_eta = QLabel("-")
        progress_layout.addWidget(self.lbl_eta, 2, 3)
        
        right_layout.addWidget(progress_group)

        # 3. Live Log Viewer
        log_group = QGroupBox("Execution Console Logs")
        log_vbox = QVBoxLayout(log_group)
        self.log_viewer = LogViewer(self)
        log_vbox.addWidget(self.log_viewer)
        
        right_layout.addWidget(log_group, 2)

        splitter.addWidget(right_widget)

        # Restore reasonable sizing proportions for the splitter panels
        splitter.setSizes([320, 780])

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to import.")
        
        # Add partner link label on the right side of status bar
        self.partner_label = QLabel()
        self.partner_label.setOpenExternalLinks(True)
        self.partner_label.setObjectName("partner_label")
        self.partner_label.setContentsMargins(0, 0, 10, 0)
        self.status_bar.addPermanentWidget(self.partner_label)
        
        self.update_link_colors()

    def setup_shortcuts(self):
        """Keyboard Shortcuts for advanced controls."""
        QShortcut(QKeySequence("Ctrl+S"), self, self.start_import)
        QShortcut(QKeySequence("Ctrl+P"), self, self.pause_import)
        QShortcut(QKeySequence("Ctrl+R"), self, self.resume_import)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    def update_speed_label(self, val):
        self.speed_lbl.setText(f"{val} ms")

    def append_log_to_viewer(self, msg: str):
        """Callback connected to thread-safe ui_log_signal."""
        self.log_viewer.append_log(msg)

    def load_initial_credentials(self):
        """Loads saved encrypted credentials or fallbacks to env variables."""
        email, password = load_credentials()
        if email and password:
            self.email_input.setText(email)
            self.password_input.setText(password)
            self.remember_me_cb.setChecked(True)
            logger.info("Credentials loaded from secure encrypted vault.")
        else:
            # Fallback to .env values if set
            env_email = os.getenv("EMAIL", "")
            env_password = os.getenv("PASSWORD", "")
            if env_email:
                self.email_input.setText(env_email)
                logger.info("Credentials populated from environmental variables.")
            if env_password:
                self.password_input.setText(env_password)

    def handle_files_dropped(self, paths: list):
        """Processes files dropped or selected via browse dialog."""
        valid_paths = []
        for path in paths:
            if path.is_dir():
                # Add all txt files inside directory
                valid_paths.extend(sorted(list(path.glob("*.txt"))))
            elif path.suffix.lower() == ".txt":
                valid_paths.append(path)
                
        if valid_paths:
            self.queue_manager.set_queue(valid_paths)
            logger.info(f"Queued {len(valid_paths)} scenario file(s).")
            self.status_bar.showMessage(f"Queued {len(valid_paths)} files.")
        else:
            QMessageBox.warning(self, "Invalid Files", "No valid .txt files found in selection.")

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Scenario TXT Files", "", "Text Files (*.txt)")
        if files:
            self.handle_files_dropped([Path(f) for f in files])

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing TXT Files")
        if folder:
            self.handle_files_dropped([Path(folder)])

    def clear_queue(self):
        self.queue_manager.clear()
        from app.progress.progress_manager import ProgressManager
        try:
            ProgressManager().clear()
        except Exception as e:
            logger.warning(f"Could not clear progress history file: {e}")
        logger.info("Files queue cleared.")
        self.status_bar.showMessage("Queue cleared.")

    def show_format_help(self):
        """Displays a clean, styled dialog explaining the TXT file format guidelines."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Scenario File Format Guidelines")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        
        help_html = """
        <h3>Scenario File Syntax Guide</h3>
        <p>Your plain-text scenario <code>.txt</code> files should follow this format:</p>
        <pre style='background-color: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; font-family: Courier, monospace;'>
# Comments start with # or //
Folder: User Authentication
Subfolder: Sign In Flow

Scenario: Successful sign in
Action: Open login page and enter credentials
Result: Dashboard page is loaded
        </pre>
        <ul>
            <li><b>Folder / Subfolder:</b> Defines target paths in CucumberStudio.</li>
            <li><b>Scenario:</b> Marks the test case title.</li>
            <li><b>Action:</b> Step actions (supports multi-line text).</li>
            <li><b>Result:</b> Expected results (supports multi-line text).</li>
            <li><b>Comments:</b> Lines starting with <code>#</code> or <code>//</code> are skipped.</li>
        </ul>
        """
        msg_box.setText(help_html)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def test_connection(self):
        """Triggers worker in connection test / projects load mode."""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Validation Error", "Please provide both Email and Password.")
            return

        # Handle Remember Me Credential Caching
        if self.remember_me_cb.isChecked():
            save_credentials(email, password)
        else:
            clear_credentials()

        # Prepare config
        config_data = {
            "email": email,
            "password": password,
            "headless": self.radio_headless.isChecked(),
            "typing_speed_ms": self.speed_slider.value(),
            "timeout_ms": settings.DEFAULT_TIMEOUT_MS,
            "retries": settings.DEFAULT_RETRIES
        }

        # Toggle UI controls
        self.set_ui_enabled(False)
        self.status_bar.showMessage("Connecting to CucumberStudio...")
        
        # Start worker thread just to load projects
        self.worker = ImportWorker([], config_data)
        self.worker.set_only_load_projects(True)
        
        # Connections
        self.worker.projects_loaded_signal.connect(self.populate_projects)
        self.worker.finished_signal.connect(self.conn_finished)
        self.worker.log_signal.connect(self.ui_log_signal.emit)
        
        self.worker.start()

    @Slot(list)
    def populate_projects(self, projects: list):
        self.project_combo.clear()
        if projects:
            self.project_combo.addItems(projects)
            self.status_bar.showMessage(f"Loaded {len(projects)} projects.")
        else:
            self.project_combo.setPlaceholderText("No projects found.")
            self.status_bar.showMessage("No projects found.")

    def conn_finished(self, success: bool, msg: str):
        self.set_ui_enabled(True)
        if success:
            QMessageBox.information(self, "Connection Test", "Connected successfully and project list refreshed.")
        else:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to CucumberStudio:\n{msg}")
        self.status_bar.showMessage("Ready.")

    def start_import(self):
        """Starts the scenario import process."""
        # 1. Validate inputs
        email = self.email_input.text().strip()
        password = self.password_input.text()
        project_name = self.project_combo.currentText().strip()
        files = self.queue_manager.get_files()

        if not email or not password:
            QMessageBox.warning(self, "Validation Error", "Credentials cannot be empty.")
            return
        if not project_name or project_name == "Fetch projects...":
            QMessageBox.warning(self, "Validation Error", "Please select a target Project. Use Test Connection first if empty.")
            return
        if not files:
            QMessageBox.warning(self, "Validation Error", "Please add at least one scenario TXT file to the queue.")
            return

        # Prompt for Import Mode (Default vs Raw Version)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Choose Import Mode")
        msg_box.setText("Please select how scenarios should be imported:")
        default_btn = msg_box.addButton("Default (Step-by-Step)", QMessageBox.ButtonRole.YesRole)
        raw_btn = msg_box.addButton("Raw Version (Bulk)", QMessageBox.ButtonRole.NoRole)
        cancel_btn = msg_box.addButton(QMessageBox.StandardButton.Cancel)
        
        msg_box.setDefaultButton(default_btn)
        msg_box.exec()
        
        if msg_box.clickedButton() == default_btn:
            import_mode = "default"
        elif msg_box.clickedButton() == raw_btn:
            import_mode = "raw"
        else:
            return # User canceled

        # Handle Remember Me Credential Caching
        if self.remember_me_cb.isChecked():
            save_credentials(email, password)
        else:
            clear_credentials()

        # 2. Gather Configuration
        config_data = {
            "email": email,
            "password": password,
            "project_name": project_name,
            "headless": self.radio_headless.isChecked(),
            "typing_speed_ms": self.speed_slider.value(),
            "timeout_ms": settings.DEFAULT_TIMEOUT_MS,
            "retries": settings.DEFAULT_RETRIES,
            "import_mode": import_mode
        }

        # 3. Disable Controls
        self.set_ui_enabled(False)
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # 4. Initialize Background Thread
        self.worker = ImportWorker(files, config_data)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.import_finished)
        self.worker.status_signal.connect(self.update_status_label)
        self.worker.log_signal.connect(self.ui_log_signal.emit)
        self.worker.request_retry_signal.connect(self.prompt_retry_dialog)

        # Clear old stats
        self.progress_bar.setValue(0)
        self.lbl_current_file.setText("-")
        self.lbl_current_scenario.setText("-")
        
        # Start Worker Thread
        self.worker.start()

    @Slot(int)
    def prompt_retry_dialog(self, failed_count: int):
        """Prompt confirmation dialog to retry failed scenarios."""
        reply = QMessageBox.question(
            self,
            "Retry Failed Scenarios",
            f"{failed_count} scenarios failed to import.\nDo you want to retry importing them one more time?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        decision = (reply == QMessageBox.StandardButton.Yes)
        if self.worker:
            self.worker.confirm_retry(decision)

    def pause_import(self):
        if self.worker:
            self.worker.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)

    def resume_import(self):
        if self.worker:
            self.worker.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)

    def stop_import(self):
        if self.worker and self.worker.isRunning():
            self.status_bar.showMessage("Stopping active processes... Please wait")
            self.btn_stop.setEnabled(False)
            self.btn_stop.setText("Stopping...")
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(False)
            logger.info("Stop requested by user. Aborting active automation tasks...")
            self.worker.stop()

    def update_status_label(self, status: str):
        self.status_bar.showMessage(f"Status: {status}")

    @Slot(dict)
    def update_progress(self, data: dict):
        """Updates progress bars and labels on QThread progress emission."""
        file_name = data.get("current_file", "")
        scenario_name = data.get("current_scenario", "")
        completed = data.get("completed", 0)
        total = data.get("total", 0)
        percent = data.get("progress_percent", 0)
        elapsed = data.get("elapsed", "00:00:00")
        eta = data.get("eta", "-")

        self.lbl_current_file.setText(file_name)
        self.lbl_current_scenario.setText(scenario_name)
        self.progress_bar.setValue(percent)
        self.lbl_elapsed.setText(elapsed)
        self.lbl_eta.setText(eta)
        
        # Update file state color in Queue Table
        self.queue_manager.update_status(file_name, "Importing")
        
        self.status_bar.showMessage(f"Processing Scenarios: {completed}/{total}")

    def import_finished(self, success: bool, message: str):
        """Cleans up widgets and unlocks controls on QThread completion."""
        self.set_ui_enabled(True)
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setText("Stop")

        # Mark all files in Queue table as completed or failed
        files = self.queue_manager.get_files()
        for f in files:
            if success:
                self.queue_manager.update_status(f.name, "Completed")
            else:
                self.queue_manager.update_status(f.name, "Failed")

        if success:
            QMessageBox.information(self, "Import Complete", f"Scenario import successfully finished!\n\n{message}")
            self.status_bar.showMessage("Import completed successfully.")
        else:
            QMessageBox.critical(self, "Import Stopped / Failed", f"Scenario import failed or stopped:\n\n{message}")
            self.status_bar.showMessage("Import failed.")

    def set_ui_enabled(self, enabled: bool):
        """Utility to disable inputs when automated browser actions are running."""
        self.email_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.remember_me_cb.setEnabled(enabled)
        self.btn_test_conn.setEnabled(enabled)
        self.btn_refresh_projects.setEnabled(enabled)
        self.project_combo.setEnabled(enabled)
        self.radio_headless.setEnabled(enabled)
        self.radio_visible.setEnabled(enabled)
        self.speed_slider.setEnabled(enabled)
        self.btn_browse_files.setEnabled(enabled)
        self.btn_browse_folder.setEnabled(enabled)
        self.btn_clear_queue.setEnabled(enabled)
        self.btn_info.setEnabled(enabled)
        self.drag_drop_zone.setEnabled(enabled)

    def closeEvent(self, event):
        """Ensures background threads and browser sessions are fully cleaned up on window close without freezing UI."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Exit Application", "Import execution is currently running. Are you sure you want to stop and exit?", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.status_bar.showMessage("Stopping worker and exiting application...")
                self.worker.stop()
                
                # Non-blocking wait: pump GUI event loop while waiting for worker thread to exit
                start_t = time.time()
                while self.worker.isRunning():
                    QCoreApplication.processEvents()
                    self.worker.wait(50)  # 50ms polling slices
                    if time.time() - start_t > 3.5:
                        logger.warning("Worker thread did not exit within 3.5s. Force terminating...")
                        self.worker.terminate()
                        break
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def toggle_theme(self):
        """Toggles the stylesheet between DARK_QSS and LIGHT_QSS."""
        if self.btn_theme.text() == "Light Mode":
            self.is_light_theme = True
            self.setStyleSheet(LIGHT_QSS)
            self.btn_theme.setText("Dark Mode")
            self.status_bar.showMessage("Theme changed to Light Mode.")
            logger.info("UI theme toggled to Light Mode.")
        else:
            self.is_light_theme = False
            self.setStyleSheet(DARK_QSS)
            self.btn_theme.setText("Light Mode")
            self.status_bar.showMessage("Theme changed to Dark Mode.")
            logger.info("UI theme toggled to Dark Mode.")
        
        # Refresh dynamic component styles
        self.drag_drop_zone.update_style("normal")
        self.log_viewer.update_theme_style(self.is_light_theme)
        self.queue_manager.update_theme_style(self.is_light_theme)
        self.update_link_colors()

    def update_link_colors(self):
        """Updates link text colors programmatically to bypass QSS anchor inheritance limits."""
        color = "#198754" if self.is_light_theme else "#38bdf8"
        self.partner_label.setText(f"<a href='https://palosite.com' style='color: {color}; text-decoration: none; font-weight: bold;'>Partner: palosite.com</a>")
        self.contact_link.setText(f"<a href='mailto:hello@palosite.com' style='color: {color}; text-decoration: none; font-weight: bold;'>hello@palosite.com</a>")
