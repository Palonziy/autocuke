import os
import sys
import logging
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from app.config import settings

# Force Playwright to always store/look for browsers inside LOCALAPPDATA/AutoCuke/ms-playwright
# This prevents write-permission errors on C:/Program Files and packages cleanly.
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(settings.BASE_DIR / "ms-playwright")

logger = logging.getLogger("CucumberStudioImporter")

class BrowserManager:
    def __init__(self, headless: bool = False, timeout_ms: int = settings.DEFAULT_TIMEOUT_MS):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> Page:
        """Starts Playwright, launches Chromium, and returns a new page."""
        logger.info(f"Starting browser (headless={self.headless})...")
        self._playwright = await async_playwright().start()
        
        # Launch Chromium
        try:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "executable doesn't exist" in err_msg or "playwright install" in err_msg or "not installed" in err_msg:
                logger.info("Chromium browser binary not found. Installing Chromium automatically (this might take a minute)...")
                
                # Import playwright main entrypoint to execute installation programmatically
                from playwright.__main__ import main as playwright_cli_main
                
                old_args = sys.argv
                sys.argv = ["playwright", "install", "chromium"]
                try:
                    # Run the playwright installation CLI directly in this process
                    # (This prevents launching a second copy of the AutoCuke.exe GUI)
                    playwright_cli_main()
                except SystemExit as sys_exit:
                    if sys_exit.code != 0:
                        logger.error(f"Playwright installation CLI exited with code {sys_exit.code}")
                        raise RuntimeError(f"Playwright installation failed with code {sys_exit.code}")
                except Exception as install_err:
                    logger.error(f"Failed to automatically install Chromium: {install_err}")
                    raise install_err
                finally:
                    # Restore original command-line arguments
                    sys.argv = old_args
                
                logger.info("Chromium browser binary installed successfully. Retrying browser launch...")
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
                )
            else:
                raise e
        
        # Create Context
        self._context = await self._browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Set default timeouts
        self._context.set_default_timeout(self.timeout_ms)
        self._context.set_default_navigation_timeout(self.timeout_ms)
        
        page = await self._context.new_page()
        logger.info("Browser session started successfully.")
        return page

    async def close(self):
        """Closes browser session and stops Playwright."""
        logger.info("Closing browser session...")
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error during browser cleanup: {e}")
        finally:
            self._context = None
            self._browser = None
            self._playwright = None
            logger.info("Browser session closed.")
