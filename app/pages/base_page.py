import asyncio
import logging
import datetime
from pathlib import Path
from playwright.async_api import Page, Locator, TimeoutError
from app.config import settings

logger = logging.getLogger("CucumberStudioImporter")

class BasePage:
    def __init__(self, page: Page, typing_delay_ms: int = settings.DEFAULT_TYPING_SPEED_MS):
        self.page = page
        self.typing_delay_ms = typing_delay_ms
        self.screenshot_dir = settings.LOG_DIR / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def capture_screenshot(self, context_name: str = "error"):
        """Captures a screenshot of the current page and stores it in logs/screenshots/."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_context = "".join([c if c.isalnum() else "_" for c in context_name])
        screenshot_path = self.screenshot_dir / f"{safe_context}_{timestamp}.png"
        try:
            await self.page.screenshot(path=str(screenshot_path), full_page=False)
            logger.info(f"Screenshot saved to: {screenshot_path}")
            return str(screenshot_path)
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None

    async def retry_action(self, action_func, description: str, retries: int = settings.DEFAULT_RETRIES):
        """
        Executes a browser action with retries and timeout error catching.
        Captures a screenshot on final failure.
        """
        for attempt in range(1, retries + 1):
            try:
                return await action_func()
            except TimeoutError as te:
                logger.warning(f"Timeout during action '{description}' (Attempt {attempt}/{retries}): {te}")
                if attempt == retries:
                    await self.capture_screenshot(f"{description}_timeout")
                    raise
            except Exception as e:
                logger.warning(f"Error during action '{description}' (Attempt {attempt}/{retries}): {e}")
                if attempt == retries:
                    await self.capture_screenshot(f"{description}_error")
                    raise
            # Wait briefly before retrying
            await asyncio.sleep(1)

    async def click(self, locator_or_selector: str | Locator, description: str, retries: int = settings.DEFAULT_RETRIES):
        """Clicks an element, resolving selector and using retry logic."""
        async def _click():
            loc = self._resolve_locator(locator_or_selector)
            await loc.scroll_into_view_if_needed()
            await loc.click()
            
        logger.info(f"Clicking: {description}")
        await self.retry_action(_click, f"click_{description}", retries)

    async def fill(self, locator_or_selector: str | Locator, value: str, description: str, retries: int = settings.DEFAULT_RETRIES):
        """Fills an input field, clearing existing text first."""
        async def _fill():
            loc = self._resolve_locator(locator_or_selector)
            await loc.scroll_into_view_if_needed()
            await loc.fill(value)
            
        logger.info(f"Filling '{description}' with value: {'***' if 'password' in description.lower() else value}")
        await self.retry_action(_fill, f"fill_{description}", retries)

    async def type_human(self, locator_or_selector: str | Locator, value: str, description: str, retries: int = settings.DEFAULT_RETRIES):
        """Types value into field with a human-like delay."""
        delay_sec = self.typing_delay_ms / 1000.0
        async def _type():
            loc = self._resolve_locator(locator_or_selector)
            await loc.scroll_into_view_if_needed()
            await loc.click()
            
            # Clear existing text by selecting all and deleting
            await loc.press("Control+A")
            await loc.press("Backspace")
            
            await loc.press_sequentially(value, delay=delay_sec)
            
        logger.info(f"Human typing '{description}' (delay={self.typing_delay_ms}ms) with value: {'***' if 'password' in description.lower() else value}")
        await self.retry_action(_type, f"type_{description}", retries)

    async def navigate(self, url: str, description: str, retries: int = settings.DEFAULT_RETRIES):
        """Navigates the browser to the specified URL."""
        async def _navigate():
            await self.page.goto(url, wait_until="domcontentloaded")
            
        logger.info(f"Navigating to {description} ({url})")
        await self.retry_action(_navigate, f"navigate_{description}", retries)

    def _resolve_locator(self, locator_or_selector: str | Locator) -> Locator:
        """Helper to return a Locator whether given a string selector or a Locator."""
        if isinstance(locator_or_selector, Locator):
            return locator_or_selector
        return self.page.locator(locator_or_selector)
