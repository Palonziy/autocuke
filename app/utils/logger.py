import logging
import datetime
from pathlib import Path
from app.config import settings

def setup_logger(ui_callback=None) -> logging.Logger:
    """
    Sets up the root logger to write logs to both a file (named by date) and stderr.
    If a ui_callback is provided, logs are also forwarded to that callback (e.g. for GUI log console).
    """
    logger = logging.getLogger("CucumberStudioImporter")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            
    # Formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # 1. File Handler (daily file log e.g., 2026-07-20.log)
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    log_file = settings.LOG_DIR / f"{today_str}.log"
    
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to create file handler for logging: {e}")
        
    # 2. Console Handler (stderr)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 3. UI Handler (if callback provided)
    if ui_callback:
        class UICallbackHandler(logging.Handler):
            def __init__(self, callback):
                super().__init__()
                self.callback = callback
                
            def emit(self, record):
                try:
                    formatted_msg = self.format(record)
                    self.callback(formatted_msg)
                except Exception:
                    pass
                    
        ui_handler = UICallbackHandler(ui_callback)
        ui_handler.setLevel(logging.INFO)
        ui_handler.setFormatter(formatter)
        logger.addHandler(ui_handler)
        
    return logger

def get_logger() -> logging.Logger:
    """Returns the logger instance."""
    return logging.getLogger("CucumberStudioImporter")
