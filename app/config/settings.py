import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = BASE_DIR / "app"

# Dynamic User AppData Directory (write permissions guaranteed)
if os.name == 'nt':
    APPDATA_DIR = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "AutoCuke"
else:
    APPDATA_DIR = Path.home() / ".autocuke"

LOG_DIR = APPDATA_DIR / "logs"
PROGRESS_DIR = APPDATA_DIR / "progress"

# Create directories if they don't exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

# URL constants
SIGN_IN_URL = "https://studio.cucumberstudio.com/users/sign_in"
PROJECTS_URL = "https://studio.cucumberstudio.com/projects"

# Browser settings
DEFAULT_TIMEOUT_MS = 15000  # 15 seconds
DEFAULT_RETRIES = 3
DEFAULT_TYPING_SPEED_MS = 50  # milliseconds delay between keystrokes

# Encryption configuration
ENCRYPTED_CREDS_FILE = PROGRESS_DIR / "credentials.enc"
ENCRYPTION_KEY_FILE = PROGRESS_DIR / "secret.key"

# Default progress tracking file
PROGRESS_FILE = PROGRESS_DIR / "progress.json"
