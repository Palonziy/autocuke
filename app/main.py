import sys
import logging
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow

# Ensure proper logs directory structure
from app.config import settings

def main():
    # Windows taskbar icon grouping hack
    import os
    if os.name == 'nt':
        import ctypes
        try:
            myappid = 'palosite.autocuke.importer.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # Initialize basic console logging in case setup_logger isn't called yet
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    app.setApplicationName("AutoCuke Scenario Importer")
    app.setApplicationVersion("1.0.0")

    # Launch GUI
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
