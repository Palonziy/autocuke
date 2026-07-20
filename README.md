# SmartBear CucumberStudio Scenario Importer

A professional Windows desktop application built with **Python 3.12+**, **PySide6**, and **Playwright (Chromium)**. It automates importing action/result test scenarios from structured TXT files into SmartBear CucumberStudio.

---

## Features

- **Automated Hierarchy Creation**: Seamlessly navigates, matches, or recursively creates Folder -> Subfolder trees inside CucumberStudio.
- **Robust Automation Engine**: Page Object Model architecture built on top of Playwright Chromium, with custom delays to simulate human typing.
- **Resilient Execution Loop**: Includes automatic browser crash recovery, network reconnect handling, and a 3-attempt action retry system.
- **Smart Duplicate Detection**: Scans the active folder in CucumberStudio to skip duplicate scenarios.
- **Resume Support**: Maintains `progress.json` to seamlessly resume from where it stopped.
- **Secure Credentials Storage**: Protects password inputs using Windows Data Protection API (DPAPI) and Fernet cryptography.
- **Live GUI Console**: Live console logging with interactive text search and export options.
- **Drag & Drop Queue**: Queue multiple TXT files or entire folders instantly.

---

## Folder Structure

```
cucumber/
├── app/
│   ├── main.py                     # Entry point
│   ├── browser/
│   │   └── driver.py               # Playwright browser lifecycle manager
│   ├── config/
│   │   └── settings.py             # Global constants & directories configuration
│   ├── gui/
│   │   ├── components.py           # Custom PySide6 widgets (DragDrop, LogViewer, Queue)
│   │   ├── main_window.py          # Main PySide6 Window layout & signal hooks
│   │   └── styles.py               # Modern Dark QSS Theme definitions
│   ├── models/
│   │   └── scenario.py             # Scenario and ScenarioStep data structures
│   ├── pages/
│   │   ├── base_page.py            # Base actions with retry wrappers & screenshots
│   │   ├── login_page.py           # Login page actions & session checkers
│   │   ├── project_page.py         # Project navigation and folder creation
│   │   └── scenario_page.py        # Scenario creation & step-by-step inputs
│   ├── parser/
│   │   └── txt_parser.py           # UTF-8 state-machine parser for scenario text
│   └── progress/
│       └── progress_manager.py     # JSON progress state tracker (progress.json)
├── logs/                           # Auto-created directory for daily .log files and screenshots
├── progress/                       # Auto-created directory for progress.json and encrypted credentials
├── tests/
│   ├── test_parser.py              # Unit tests for text parsing logic
│   └── test_integration.py         # Playwright automation integration tests against a mock server
├── .env.example                    # Environmental configuration template
├── requirements.txt                # Project dependency list
└── README.md                       # Documentation
```

---

## Installation Guide

### Prerequisites
- Python 3.12 or newer (Tested up to Python 3.14)
- Google Chrome / Chromium dependencies (managed by Playwright)

### Step 1: Clone or Copy the Codebase
Make sure all application directories match the folder structure shown above.

### Step 2: Set Up Virtual Environment
Open PowerShell inside the project root:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3: Install Package Dependencies
Install the required packages listed in `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### Step 4: Install Playwright Chromium Drivers
Download the required Chromium binaries:
```powershell
python -m playwright install chromium
```

---

## Configuration

1. Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Fill in your CucumberStudio credentials:
   ```ini
   EMAIL=your-email@example.com
   PASSWORD=your-secret-password
   ```
*Note: Credentials can also be typed and saved directly within the application GUI. If "Remember Me" is checked, the credentials are encrypted and stored inside `progress/credentials.enc`.*

---

## Running the Application

Launch the desktop interface by executing:
```powershell
python app/main.py
```

### How to Import Scenarios:
1. **Login**: Type your Email and Password, then click **Test Connection**. This fetches your active project list.
2. **Select Project**: Choose the target CucumberStudio project from the dropdown.
3. **Queue Files**: Drag and drop your scenario `.txt` files or folders into the dashed Drag & Drop box, or use the **Browse Files / Folder** buttons.
4. **Configure Browser**: Choose whether to run the browser in the background (**Headless**) or view its actions (**Visible**). Adjust typing speed if needed.
5. **Start**: Click **Start Import**. The automation will handle everything from there. You can **Pause**, **Resume**, or **Stop** at any time.

---

## Scenario File Syntax (.txt)

Scenario files are parsed line-by-line using a UTF-8 parser. Comments (lines starting with `#` or `//`) and blank lines are ignored. Folder paths are set at the top, and scenarios are closed with `END_SCENARIO`.

### Syntax Example:
```txt
# Folder Tree Hierarchy
Folder: Mobile
Subfolder: Authentication
Subfolder: Register

// First Scenario
Scenario: Register with valid phone
Action:
Open Registration screen
Result:
Registration screen is displayed

Action:
Enter valid phone number
Result:
Phone number is accepted

Action:
Tap Continue
Result:
OTP page is displayed
END_SCENARIO

// Second Scenario (under the same Mobile > Authentication > Register folders)
Scenario: Register with existing phone
Action:
Open Registration screen
Result:
Registration screen is displayed
Action:
Enter existing phone number
Result:
Error message 'Phone number already registered' is displayed
END_SCENARIO
```

---

## Verification and Testing

You can run the suite of unit and integration tests using Python's built-in `unittest` runner.

### 1. Run Parser Unit Tests:
```powershell
$env:PYTHONPATH="."; python tests/test_parser.py
```

### 2. Run Automation End-to-End Integration Tests:
Spins up a local HTTP server inside a Python background thread and executes the page actions against it to verify element selection:
```powershell
$env:PYTHONPATH="."; python tests/test_integration.py
```

---

## Building a Standalone Executable (.exe)

You can compile the application into a single executable using **PyInstaller**.

### Step 1: Install PyInstaller
Ensure PyInstaller is installed inside your virtual environment:
```powershell
pip install pyinstaller
```

### Step 2: Generate Executable
Run the PyInstaller command with the `--collect-all` flag to bundle Playwright assets alongside PySide6 libraries:
```powershell
pyinstaller --name "CucumberStudioImporter" --windowed --noconsole --clean --collect-all playwright app/main.py
```

### Step 3: Launch Executable
Upon compilation, the final build artifacts will reside in the `dist/` directory. Navigate there and open the executable:
```powershell
.\dist\CucumberStudioImporter\CucumberStudioImporter.exe
```
*(The executable will automatically look for its configuration folders relative to the location where it is executed).*
