import asyncio
import logging
import time
import datetime
from pathlib import Path
from PySide6.QtCore import QThread, Signal

from app.config import settings
from app.parser.txt_parser import TXTParser
from app.progress.progress_manager import ProgressManager
from app.browser.driver import BrowserManager
from app.pages.login_page import LoginPage
from app.pages.project_page import ProjectPage
from app.pages.scenario_page import ScenarioPage

from playwright.async_api import Error as PlaywrightError, TargetClosedError

logger = logging.getLogger("CucumberStudioImporter")

class ImportWorker(QThread):
    # Signals to communicate with the GUI (run on main UI thread)
    log_signal = Signal(str)
    progress_signal = Signal(dict)
    finished_signal = Signal(bool, str) # success, message
    status_signal = Signal(str) # "Idle", "Running", "Paused", "Stopped"
    projects_loaded_signal = Signal(list) # list of projects for dropdown
    request_retry_signal = Signal(int) # request confirmation to retry failed scenarios

    def __init__(self, files_or_folder: list[Path] | Path, config_data: dict):
        """
        config_data dict keys:
          email: str
          password: str
          project_name: str
          headless: bool
          typing_speed_ms: int
          timeout_ms: int
          retries: int
        """
        super().__init__()
        self.files_or_folder = files_or_folder
        self.config_data = config_data
        
        self.email = config_data.get("email", "")
        self.password = config_data.get("password", "")
        self.project_name = config_data.get("project_name", "")
        self.headless = config_data.get("headless", True)
        self.typing_delay_ms = config_data.get("typing_speed_ms", settings.DEFAULT_TYPING_SPEED_MS)
        self.timeout_ms = config_data.get("timeout_ms", settings.DEFAULT_TIMEOUT_MS)
        self.retries = config_data.get("retries", settings.DEFAULT_RETRIES)
        self.import_mode = config_data.get("import_mode", "default")

        self.progress_mgr = ProgressManager()
        self.browser_mgr = None
        self.page = None
        
        # Page Objects
        self.login_page = None
        self.project_page = None
        self.scenario_page = None

        # Playwright run flags
        self.is_paused = False
        self.is_stopped = False
        self._pause_event = None  # asyncio.Event
        self._loop = None         # asyncio event loop
        self._only_load_projects = False  # Set to True when just loading project list

        # Retry logic state
        self.retry_decision = None
        self.retry_event = None

    def set_only_load_projects(self, val: bool):
        self._only_load_projects = val

    def confirm_retry(self, decision: bool):
        """Thread-safe setter for user retry decision."""
        self.retry_decision = decision
        if self.retry_event and self._loop:
            self._loop.call_soon_threadsafe(self.retry_event.set)

    def pause(self):
        """Pauses the worker."""
        if not self.is_paused and not self.is_stopped:
            self.is_paused = True
            if self._pause_event and self._loop:
                self._loop.call_soon_threadsafe(self._pause_event.clear)
            self.status_signal.emit("Paused")
            logger.info("Import process paused by user.")

    def resume(self):
        """Resumes the worker."""
        if self.is_paused and not self.is_stopped:
            self.is_paused = False
            if self._pause_event and self._loop:
                self._loop.call_soon_threadsafe(self._pause_event.set)
            self.status_signal.emit("Running")
            logger.info("Import process resumed by user.")

    def stop(self):
        """Stops the worker immediately and aborts active Playwright browser actions."""
        if self.is_stopped:
            return
        self.is_stopped = True
        logger.info("Import process stop requested by user. Terminating browser automation session...")
        self.status_signal.emit("Stopping...")
        
        # If paused, resume it so it can exit the wait and stop
        if self.is_paused:
            self.resume()
            
        # Force-release any active retry wait block
        self.confirm_retry(False)
        
        # Schedule immediate browser force close on event loop to interrupt in-flight Playwright await calls
        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self._force_close_browser(), self._loop)
            except Exception as e:
                logger.warning(f"Could not schedule browser force close: {e}")

    async def _force_close_browser(self):
        """Forcefully closes browser manager to instantly abort pending Playwright page actions."""
        if self.browser_mgr:
            try:
                logger.info("Closing Playwright context to abort active actions immediately...")
                await self.browser_mgr.close()
            except Exception as e:
                logger.warning(f"Error during forced browser close: {e}")

    def run(self):
        """Main QThread entry point. Starts the asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        def handle_asyncio_exception(loop, context):
            exception = context.get("exception")
            msg = str(context.get("message", ""))
            if (isinstance(exception, (TargetClosedError, PlaywrightError, asyncio.CancelledError)) or 
                "Target page, context or browser has been closed" in msg or 
                "Target closed" in msg):
                logger.debug(f"Silenced Playwright target closed exception during stop: {exception or msg}")
                return
            loop.default_exception_handler(context)

        self._loop.set_exception_handler(handle_asyncio_exception)
        
        try:
            self._loop.run_until_complete(self.async_run())
        except Exception as e:
            logger.critical(f"Unhandled exception in importer worker loop: {e}")
            self.finished_signal.emit(False, f"Critical error: {e}")
        finally:
            self._loop.close()

    async def async_run(self):
        """Main async loop."""
        self.is_stopped = False
        self.is_paused = False
        
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initial state: running

        # Custom logging setup to emit logs to the UI
        def ui_log_callback(msg):
            self.log_signal.emit(msg)

        # Attach UI log handler dynamically
        logger_root = logging.getLogger("CucumberStudioImporter")
        
        # Check if we are only loading projects
        if self._only_load_projects:
            await self._run_load_projects()
            return

        # Start execution
        self.status_signal.emit("Running")
        logger.info("Starting CucumberStudio Import session...")
        
        # 1. Resolve files
        files_to_process = []
        if isinstance(self.files_or_folder, Path):
            if self.files_or_folder.is_dir():
                files_to_process = sorted(list(self.files_or_folder.glob("*.txt")))
            else:
                files_to_process = [self.files_or_folder]
        else:
            files_to_process = self.files_or_folder

        if not files_to_process:
            logger.error("No TXT scenario files queued.")
            self.finished_signal.emit(False, "No files found to process.")
            return

        # 2. Parse all scenarios across queued files
        all_tasks = []  # list of tuples (file_path, scenario_model)
        for fp in files_to_process:
            scenarios = TXTParser.parse_file(fp)
            logger.info(f"Parsed {len(scenarios)} scenarios from {fp.name}")
            for sc in scenarios:
                all_tasks.append((fp, sc))

        total_scenarios = len(all_tasks)
        if total_scenarios == 0:
            logger.warning("No valid test scenarios parsed from input files.")
            self.finished_signal.emit(False, "No scenarios found in files.")
            return

        logger.info(f"Total scenarios queued for processing: {total_scenarios}")

        # 3. Start Browser
        try:
            self.browser_mgr = BrowserManager(headless=self.headless, timeout_ms=self.timeout_ms)
            self.page = await self.browser_mgr.start()
            self._init_pages()
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            self.finished_signal.emit(False, f"Browser launch failed: {e}")
            return

        # 4. Handle Login
        try:
            logged_in = await self.login_page.is_logged_in()
            if not logged_in:
                logged_in = await self.login_page.login(self.email, self.password)
                if not logged_in:
                    logger.error("Authentication failed. Check your email and password.")
                    self.finished_signal.emit(False, "Login failed. Invalid credentials.")
                    await self.browser_mgr.close()
                    return
        except Exception as e:
            logger.error(f"Login process failed: {e}")
            self.finished_signal.emit(False, f"Login error: {e}")
            await self.browser_mgr.close()
            return

        # 5. Select Project
        try:
            proj_selected = await self.project_page.select_project(self.project_name)
            if not proj_selected:
                self.finished_signal.emit(False, f"Failed to select project: '{self.project_name}'")
                await self.browser_mgr.close()
                return
        except Exception as e:
            logger.error(f"Error selecting project: {e}")
            self.finished_signal.emit(False, f"Project selection error: {e}")
            await self.browser_mgr.close()
            return

        # 6. Import scenarios loop
        start_time = time.time()
        completed_count = 0
        skipped_count = 0

        # Attempt to resume from last file/index in progress.json
        resume_file = self.progress_mgr.get_current_file()
        resume_idx = self.progress_mgr.get_current_scenario_idx()
        resuming = bool(resume_file)

        # Loop variables
        current_run_tasks = list(all_tasks)
        retry_round = 0
        failed_tasks = []

        while current_run_tasks and not self.is_stopped:
            failed_tasks = []
            logger.info(f"Starting import round. Queued scenarios: {len(current_run_tasks)}")

            for idx, (file_path, scenario) in enumerate(current_run_tasks):
                # Check pause & stop events
                if self.is_stopped:
                    break
                await self._check_pause()
                if self.is_stopped:
                    break

                file_name = file_path.name

                # Resume filtering (only applies to first round)
                if resuming and retry_round == 0:
                    if file_name != resume_file:
                        logger.info(f"Resuming: skipping file {file_name}...")
                        completed_count += 1
                        continue
                    if idx < resume_idx:
                        logger.info(f"Resuming: skipping scenario index {idx} in {file_name}...")
                        completed_count += 1
                        continue
                    resuming = False

                # UI Progress update
                elapsed_sec = int(time.time() - start_time)
                eta_str = self._calculate_eta(completed_count, total_scenarios, elapsed_sec)
                
                self.progress_signal.emit({
                    "current_file": file_name,
                    "current_scenario": scenario.name,
                    "completed": completed_count,
                    "total": total_scenarios,
                    "progress_percent": int((completed_count / total_scenarios) * 100) if total_scenarios > 0 else 0,
                    "elapsed": str(datetime.timedelta(seconds=elapsed_sec)),
                    "eta": eta_str
                })

                # Check progress history (only if not retrying)
                if retry_round == 0 and self.progress_mgr.is_scenario_completed(file_path, scenario.name):
                    logger.info(f"Scenario '{scenario.name}' already completed in progress history. Skipping.")
                    completed_count += 1
                    skipped_count += 1
                    continue

                # Import scenario
                success = False
                try:
                    # Traverse folder structure
                    folder_nav = await self.project_page.navigate_or_create_path(scenario.folders)
                    if not folder_nav:
                        raise Exception(f"Folder hierarchy creation/navigation failed for folders: {scenario.folders}")

                    # Check if scenario exists inside CucumberStudio folder
                    exists = await self.scenario_page.scenario_exists(scenario.name)
                    if exists:
                        logger.info(f"Scenario skipped: '{scenario.name}' already exists in CucumberStudio folder.")
                        if retry_round == 0:
                            self.progress_mgr.mark_scenario_completed(file_path, scenario.name)
                            self.progress_mgr.set_current_state(file_name, idx)
                        completed_count += 1
                        skipped_count += 1
                        continue

                    # Create the scenario
                    create_success = await self.scenario_page.create_scenario(scenario.name)
                    if not create_success:
                        raise Exception(f"Failed to create scenario: '{scenario.name}'")

                    # Type steps
                    steps_success = await self.scenario_page.enter_steps(scenario.steps, import_mode=self.import_mode, scenario_name=scenario.name)
                    if not steps_success:
                        raise Exception(f"Failed to enter steps in scenario: '{scenario.name}'")

                    # Save
                    save_success = await self.scenario_page.save_scenario()
                    if not save_success:
                         raise Exception(f"Failed to save scenario: '{scenario.name}'")

                    # Mark completed
                    if retry_round == 0:
                        self.progress_mgr.mark_scenario_completed(file_path, scenario.name)
                        self.progress_mgr.set_current_state(file_name, idx)
                    
                    # Navigate back to folder view
                    await self.scenario_page.go_back_to_folder(scenario.folders[-1])
                    
                    success = True
                    completed_count += 1
                    logger.info(f"Successfully imported scenario: '{scenario.name}' ({completed_count}/{total_scenarios})")
                except Exception as e:
                    if self.is_stopped:
                        logger.info("Import process stopped by user. Aborting remaining scenarios.")
                        break
                    logger.error(f"Error importing scenario '{scenario.name}' in {file_name}: {e}")
                    await self.scenario_page.capture_screenshot(f"error_{scenario.name}")
                    failed_tasks.append((file_path, scenario))
                    
                    # Browser Recovery Action
                    try:
                        await self._recover_session()
                    except Exception as rec_err:
                        if self.is_stopped:
                            logger.info("Import process stopped by user during recovery attempt.")
                            break
                        logger.critical(f"Critical: Failed to recover browser session: {rec_err}")
                        self.finished_signal.emit(False, f"Execution failed. Browser disconnected and recovery failed: {rec_err}")
                        await self.browser_mgr.close()
                        return

                # Wait briefly between scenarios
                await asyncio.sleep(1.0)

            # End of current round. If there are failed tasks, decide on retry!
            if failed_tasks and not self.is_stopped:
                # If we've already done a retry round, stop and output results
                if retry_round >= 1:
                    logger.warning(f"Failed scenarios still failed after retry round: {[t[1].name for t in failed_tasks]}")
                    break

                logger.info(f"Round completed. {len(failed_tasks)} scenarios failed. Asking user for retry confirmation...")
                self.retry_decision = None
                self.retry_event = asyncio.Event()

                # Emit signal to GUI
                self.request_retry_signal.emit(len(failed_tasks))

                # Wait for user decision
                await self.retry_event.wait()

                if self.retry_decision:
                    logger.info("User confirmed retry. Retrying failed scenarios...")
                    current_run_tasks = list(failed_tasks)
                    retry_round += 1
                else:
                    logger.info("User declined retry of failed scenarios.")
                    break
            else:
                # No failed tasks left or stopped
                break

        # Cleanup & Finish
        await self.browser_mgr.close()
        
        # Reset active progress file index state so next execution starts fresh
        self.progress_mgr.set_current_state("", 0)
        
        # Format final error report
        error_count = len(failed_tasks)
        if error_count == 0 and not self.is_stopped:
            elapsed_sec = int(time.time() - start_time)
            self.progress_signal.emit({
                "current_file": "-",
                "current_scenario": "-",
                "completed": total_scenarios,
                "total": total_scenarios,
                "progress_percent": 100,
                "elapsed": str(datetime.timedelta(seconds=elapsed_sec)),
                "eta": "00:00:00"
            })
            self.progress_mgr.clear()
            
        msg = f"Finished! Total: {total_scenarios}, Imported: {completed_count - skipped_count}, Skipped: {skipped_count}, Errors: {error_count}"
        if error_count > 0:
            error_names = [f"• [{t[0].name}] {t[1].name}" for t in failed_tasks]
            msg += "\n\nFailed Scenarios:\n" + "\n".join(error_names)

        logger.info(f"Import process finished. {msg}")
        self.finished_signal.emit(True, msg)

    async def _run_load_projects(self):
        """Helper to login and fetch projects, then shut down."""
        logger.info("Initializing connection to CucumberStudio to fetch projects...")
        try:
            self.browser_mgr = BrowserManager(headless=self.headless, timeout_ms=self.timeout_ms)
            self.page = await self.browser_mgr.start()
            self._init_pages()
            
            logged_in = await self.login_page.is_logged_in()
            if not logged_in:
                logged_in = await self.login_page.login(self.email, self.password)
                if not logged_in:
                    logger.error("Failed to connect: Invalid credentials.")
                    self.finished_signal.emit(False, "Test connection failed: Invalid credentials.")
                    await self.browser_mgr.close()
                    return
            
            projects = await self.project_page.list_projects()
            logger.info("Successfully fetched projects list.")
            self.projects_loaded_signal.emit(projects)
            self.finished_signal.emit(True, "Connected successfully.")
        except Exception as e:
            logger.error(f"Failed to fetch projects list: {e}")
            self.finished_signal.emit(False, f"Test connection/refresh failed: {e}")
        finally:
            if self.browser_mgr:
                await self.browser_mgr.close()

    def _init_pages(self):
        self.login_page = LoginPage(self.page, self.typing_delay_ms)
        self.project_page = ProjectPage(self.page, self.typing_delay_ms)
        self.scenario_page = ScenarioPage(self.page, self.typing_delay_ms)

    async def _recover_session(self):
        """Recovers browser session on failure."""
        if self.is_stopped:
            return
        logger.info("Recovering browser session...")
        if self.browser_mgr:
            try:
                await self.browser_mgr.close()
            except Exception:
                pass
        
        self.browser_mgr = BrowserManager(headless=self.headless, timeout_ms=self.timeout_ms)
        self.page = await self.browser_mgr.start()
        self._init_pages()
        
        logged_in = await self.login_page.is_logged_in()
        if not logged_in:
            logged_in = await self.login_page.login(self.email, self.password)
            if not logged_in:
                raise Exception("Login failed during recovery.")
                
        proj_selected = await self.project_page.select_project(self.project_name)
        if not proj_selected:
            raise Exception("Project selection failed during recovery.")
            
        logger.info("Recovery complete. Continuing import.")

    async def _check_pause(self):
        """Blocks until the pause event is set."""
        if self.is_paused:
            logger.info("Execution paused. Waiting for resume...")
            self.status_signal.emit("Paused")
            await self._pause_event.wait()
            logger.info("Execution resumed.")
            self.status_signal.emit("Running")

    def _calculate_eta(self, completed: int, total: int, elapsed_sec: int) -> str:
        if completed == 0:
            return "Calculating..."
        
        remaining = total - completed
        if remaining <= 0:
            return "00:00:00"
            
        sec_per_item = elapsed_sec / completed
        eta_sec = int(sec_per_item * remaining)
        return str(datetime.timedelta(seconds=eta_sec))
