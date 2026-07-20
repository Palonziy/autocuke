import logging
import asyncio
from playwright.async_api import Page, Locator
from app.pages.base_page import BasePage
from app.config import settings

logger = logging.getLogger("CucumberStudioImporter")

class ProjectPage(BasePage):
    def __init__(self, page: Page, typing_delay_ms: int = settings.DEFAULT_TYPING_SPEED_MS):
        super().__init__(page, typing_delay_ms)

    async def list_projects(self) -> list[str]:
        """Lists all projects available on the CucumberStudio dashboard."""
        logger.info("Listing available projects...")
        try:
            await self.navigate(settings.PROJECTS_URL, "Projects Page")
            await self.page.wait_for_load_state("networkidle")
            
            # Find all links that represent projects
            links = await self.page.locator("a").all()
            projects = []
            for link in links:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if not text:
                    continue
                
                # Split by newline and take the first non-empty line as the clean project name
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if not lines:
                    continue
                proj_name = lines[0]
                
                # Filter for project dashboard links
                if href and ("/projects/" in href or href.endswith("/projects")):
                    # Skip common control links
                    if proj_name and not any(x in proj_name.lower() for x in ["new project", "all projects", "documentation", "help", "support", "sign out"]):
                        if proj_name not in projects:
                            projects.append(proj_name)
            
            logger.info(f"Found projects: {projects}")
            return projects
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []

    async def select_project(self, project_name: str) -> bool:
        """Selects a project by clicking its link on the dashboard."""
        try:
            logger.info(f"Selecting project: {project_name}")
            await self.navigate(settings.PROJECTS_URL, "Projects Page")
            await self.page.wait_for_load_state("networkidle")

            # Look for exact text match first
            link = self.page.get_by_role("link", name=project_name, exact=True)
            if await link.count() == 0:
                # Case-insensitive or partial match
                link = self.page.locator(f"a:has-text('{project_name}')")

            if await link.count() > 0:
                href = await link.first.get_attribute("href")
                if href:
                    from urllib.parse import urljoin
                    scenarios_url = urljoin(self.page.url, href).rstrip("/") + "/test-plan"
                    logger.info(f"Navigating directly to project scenarios: {scenarios_url}")
                    await self.page.goto(scenarios_url, wait_until="domcontentloaded")
                    await self.page.wait_for_load_state("networkidle")
                    logger.info(f"Successfully entered project and navigated to scenarios: {project_name}")
                    return True
                else:
                    await self.click(link.first, f"Project '{project_name}' link")
                    await self.page.wait_for_load_state("networkidle")
                    logger.info(f"Successfully entered project: {project_name}")
                    return True
            else:
                logger.error(f"Project '{project_name}' not found on dashboard.")
                return False
        except Exception as e:
            logger.error(f"Error selecting project: {e}")
            await self.capture_screenshot("select_project_failed")
            return False

    async def find_folder_element(self, name: str, parent_el: Locator | None = None, retries: int = 5) -> Locator | None:
        """Locates a folder in the folder tree sidebar by its name (case-insensitive), optionally scoped under a parent folder element's branch, with retries for UI lag."""
        for attempt in range(retries):
            root_locator = self.page
            if parent_el:
                # Scope search to parent element's branch container
                root_locator = parent_el.locator("xpath=ancestor::ul[contains(@class, 'tree__branch')][1]")

            try:
                # Target test-automation class first inside scoped container
                folder_spans = root_locator.locator(".t-folder-name")
                count = await folder_spans.count()
                for idx in range(count):
                    item = folder_spans.nth(idx)
                    text = await item.inner_text()
                    if text.strip().lower() == name.lower():
                        return item
            except Exception as e:
                logger.warning(f"Error resolving .t-folder-name (attempt {attempt + 1}): {e}")

            # Fallback to general selectors inside scoped container
            selectors = [
                f".folder-name:has-text('{name}')",
                f".tree-item:has-text('{name}')",
                f"a:has-text('{name}')",
                f"span:has-text('{name}')",
                f"[data-action='select-folder']:has-text('{name}')"
            ]
            for sel in selectors:
                try:
                    locator = root_locator.locator(sel)
                    count = await locator.count()
                    for idx in range(count):
                        item = locator.nth(idx)
                        text = await item.inner_text()
                        if name.lower() in text.strip().lower():
                            return item
                except Exception:
                    continue
            
            # Wait a brief moment before retrying (gives Ember.js API requests time to render folders)
            await asyncio.sleep(0.5)

        return None

    async def create_folder(self, name: str, parent_el: Locator | None = None) -> bool:
        """Creates a folder (or subfolder if parent_el is specified)."""
        logger.info(f"Creating folder: '{name}' (parent_el={parent_el})")
        try:
            # If parent is specified, hover and select it first to ensure subfolder nesting/buttons reveal
            if parent_el:
                try:
                    await parent_el.hover()
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.warning(f"Could not hover over parent folder element: {e}")
                await self.click(parent_el, "Parent folder element")
                await asyncio.sleep(0.5)
            
            # Wait up to 3 seconds for the dynamic create button to render
            try:
                await self.page.wait_for_selector("[title='Create new subfolder'], [title='Create new folder'], [title='Create folder']", state="visible", timeout=3000)
            except Exception:
                pass

            # Find and click folder creation trigger
            create_buttons = [
                self.page.locator("[title='Create new subfolder']"),
                self.page.locator("[title='Create new folder']"),
                self.page.locator("[title='Create folder']"),
                self.page.get_by_role("button", name="Folder", exact=False),
                self.page.get_by_role("button", name="Create folder", exact=False),
                self.page.locator(".create-folder-btn"),
                self.page.locator("[aria-label='Create folder']"),
                self.page.locator(".btn:has-text('Folder')"),
                self.page.locator(".btn:has-text('Create folder')"),
                self.page.locator("a:has-text('Create folder')")
            ]
            
            clicked = False
            for btn in create_buttons:
                if await btn.count() > 0 and await btn.is_visible():
                    await self.click(btn, "Create Folder Trigger")
                    clicked = True
                    break
            
            if not clicked and parent_el:
                logger.info("Standard Create Folder button not found. Attempting parent folder context menu...")
                await parent_el.click(button="right")
                await asyncio.sleep(0.5)
                # Context menu options
                ctx_options = self.page.locator("a:has-text('Create subfolder'), a:has-text('Add sub-folder'), a:has-text('New folder')")
                if await ctx_options.count() > 0:
                    await self.click(ctx_options.first, "Context Menu Subfolder option")
                    clicked = True
            
            if not clicked:
                logger.error("Failed to find folder creation button or menu option.")
                return False

            # Type folder name in input dialog
            name_inputs = [
                self.page.locator("#folder_name"),
                self.page.locator("input[name='folder[name]']"),
                self.page.get_by_placeholder("Folder name"),
                self.page.locator("input.folder-name-input"),
                self.page.locator("input[type='text']:visible"),
                self.page.locator("input[placeholder*='name']:visible").first
            ]
            
            input_field = None
            for inp in name_inputs:
                if await inp.count() > 0 and await inp.is_visible():
                    input_field = inp
                    break
            
            if not input_field:
                logger.error("Folder name input field not visible.")
                return False
                
            await self.type_human(input_field, name, "Folder Name Field")
            
            # Submit creation via Enter
            await input_field.press("Enter")
            await asyncio.sleep(1.0)  # Wait for API response or potential error modal to render
            
            # Check if there is an error message "already exists" in the modal
            error_el = self.page.get_by_text("already exists").first
            if await error_el.count() > 0 and await error_el.is_visible():
                logger.warning(f"Folder '{name}' already exists according to modal error. Closing modal.")
                cancel_btn = self.page.locator("button:has-text('Cancel'), a:has-text('Cancel'), .btn:has-text('Cancel')").first
                if await cancel_btn.count() > 0 and await cancel_btn.is_visible():
                    await cancel_btn.click()
                    await asyncio.sleep(0.5)
                return True  # Treat as success since the folder exists!

            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(0.5)  # Wait for folder creation animation
            
            logger.info(f"Folder '{name}' created successfully.")
            return True
        except Exception as e:
            logger.error(f"Error creating folder '{name}': {e}")
            await self.capture_screenshot(f"create_folder_{name}_failed")
            # Dismiss modal dialog if it got left open
            try:
                cancel_btn = self.page.locator(".modal button:has-text('Cancel'), .modal a:has-text('Cancel'), button:has-text('Cancel')").first
                if await cancel_btn.count() > 0 and await cancel_btn.is_visible():
                    await cancel_btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass
            return False

    async def navigate_or_create_path(self, folders: list[str]) -> bool:
        """
        Navigates through the folder path hierarchy.
        Creates any folders/subfolders that do not exist.
        """
        # Automatically resolve and select the project root folder (the first folder in the tree sidebar)
        # to ensure it is expanded and its children are loaded in the DOM.
        try:
            await self.page.locator(".t-folder-name").first.wait_for(state="visible", timeout=5000)
            parent_el = self.page.locator(".t-folder-name").first
            logger.info("Selecting project root folder in tree sidebar to expand hierarchy.")
            await self.click(parent_el, "Project root folder")
            await asyncio.sleep(1.5)  # Allow time for child folders to load/render
        except Exception as e:
            logger.warning(f"Could not resolve project root folder element in sidebar: {e}")
            parent_el = None

        for i, folder_name in enumerate(folders):
            logger.info(f"Navigating to hierarchy step [{i}]: '{folder_name}' (parent_el={parent_el})")
            el = await self.find_folder_element(folder_name, parent_el)
            
            if el:
                logger.info(f"Folder '{folder_name}' exists. Opening it.")
                await self.click(el, f"Folder '{folder_name}'")
                await asyncio.sleep(0.5)
            else:
                logger.info(f"Folder '{folder_name}' does not exist. Creating it.")
                success = await self.create_folder(folder_name, parent_el)
                if not success:
                    return False
                
                # Double-check it was created and select it
                el = await self.find_folder_element(folder_name, parent_el)
                if el:
                    await self.click(el, f"Folder '{folder_name}'")
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f"Failed to find folder '{folder_name}' after creation.")
                    return False
            
            parent_el = el
            
        return True
