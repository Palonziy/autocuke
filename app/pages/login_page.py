import logging
from playwright.async_api import Page, expect
from app.pages.base_page import BasePage
from app.config import settings

logger = logging.getLogger("CucumberStudioImporter")

class LoginPage(BasePage):
    def __init__(self, page: Page, typing_delay_ms: int = settings.DEFAULT_TYPING_SPEED_MS):
        super().__init__(page, typing_delay_ms)
        self.email_input = self.page.locator("#user_email")
        self.password_input = self.page.locator("#user_password")
        self.submit_button = self.page.locator("input[type='submit']")

    async def is_logged_in(self) -> bool:
        """Checks if the user is already logged in by attempting to go to the projects URL."""
        try:
            logger.info("Checking if already logged in...")
            await self.page.goto(settings.PROJECTS_URL, wait_until="domcontentloaded")
            current_url = self.page.url
            if "/projects" in current_url and "/users/sign_in" not in current_url:
                logger.info("Session is active (already logged in).")
                return True
        except Exception as e:
            logger.warning(f"Error checking login session: {e}")
        
        logger.info("No active session found.")
        return False

    async def login(self, email: str, password: str) -> bool:
        """
        Performs the login action. 
        Returns True if login succeeds, False otherwise.
        """
        try:
            await self.navigate(settings.SIGN_IN_URL, "Login Page")
            
            # Type email
            await self.type_human(self.email_input, email, "Email Field")
            
            # Type password
            await self.type_human(self.password_input, password, "Password Field")
            
            # Click sign in
            await self.click(self.submit_button, "Sign In Button")
            
            # Wait for navigation to projects or error message
            logger.info("Waiting for login response...")
            await self.page.wait_for_load_state("domcontentloaded")
            
            # Check if login was successful
            current_url = self.page.url
            if "/projects" in current_url and "/users/sign_in" not in current_url:
                logger.info("Login successful!")
                return True
                
            # Check if there is an alert error message
            error_locator = self.page.locator(".alert, .alert-danger, .error-message, [role='alert']")
            if await error_locator.count() > 0:
                error_text = await error_locator.first.inner_text()
                logger.error(f"Login failed: {error_text.strip()}")
            else:
                logger.error("Login failed (unknown error, still on sign-in page).")
                
            return False
        except Exception as e:
            logger.error(f"Exception during login: {e}")
            await self.capture_screenshot("login_exception")
            return False
