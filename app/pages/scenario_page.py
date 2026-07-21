import logging
import asyncio
from playwright.async_api import Page, Locator
from app.pages.base_page import BasePage
from app.config import settings
from app.models.scenario import ScenarioStep

logger = logging.getLogger("CucumberStudioImporter")

class ScenarioPage(BasePage):
    def __init__(self, page: Page, typing_delay_ms: int = settings.DEFAULT_TYPING_SPEED_MS):
        super().__init__(page, typing_delay_ms)

    async def scenario_exists(self, name: str) -> bool:
        """Checks if a scenario with the given name already exists in the current folder view."""
        logger.info(f"Checking if scenario '{name}' exists...")
        try:
            # CucumberStudio lists scenarios as links or items in the folder view
            selectors = [
                f".scenario-name:has-text('{name}')",
                f".scenario-list-item:has-text('{name}')",
                f"a:has-text('{name}')",
                f"tr:has-text('{name}')"
            ]
            for sel in selectors:
                locator = self.page.locator(sel)
                count = await locator.count()
                for idx in range(count):
                    text = await locator.nth(idx).inner_text()
                    if text.strip() == name:
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error checking duplicate scenario: {e}")
            return False

    async def create_scenario(self, name: str) -> bool:
        """Clicks the create scenario button and enters the name."""
        logger.info(f"Creating scenario: '{name}'")
        try:
            # Wait up to 3 seconds for scenario creation buttons to render
            try:
                await self.page.wait_for_selector("[title='Create new scenario'], [title='Create scenario']", state="visible", timeout=3000)
            except Exception:
                pass

            # Triggers to create a scenario
            create_buttons = [
                self.page.locator("[title='Create new scenario']"),
                self.page.locator("[title='Create scenario']"),
                self.page.get_by_role("button", name="Scenario", exact=False),
                self.page.get_by_role("button", name="Create scenario", exact=False),
                self.page.locator(".create-scenario-btn"),
                self.page.locator("[aria-label='Create scenario']"),
                self.page.locator(".btn:has-text('Scenario')"),
                self.page.locator(".btn:has-text('Create scenario')"),
                self.page.locator("a:has-text('Create scenario')")
            ]
            
            clicked = False
            for btn in create_buttons:
                if await btn.count() > 0 and await btn.is_visible():
                    await self.click(btn, "Create Scenario Button")
                    clicked = True
                    break
            
            if not clicked:
                logger.error("Failed to find 'Create scenario' button.")
                return False

            # Fill name
            name_inputs = [
                self.page.locator(".t-name-input"),
                self.page.get_by_placeholder("New scenario name"),
                self.page.locator("input.t-name-input"),
                self.page.locator("#scenario_name"),
                self.page.locator("input[name='scenario[name]']"),
                self.page.get_by_placeholder("Scenario name"),
                self.page.locator("input[type='text']:not([placeholder*='Search']):visible"),
                self.page.locator("input[placeholder*='name']:visible").first
            ]
            
            input_field = None
            for inp in name_inputs:
                if await inp.count() > 0 and await inp.is_visible():
                    input_field = inp
                    break
            
            if not input_field:
                logger.error("Scenario name input field not found.")
                return False

            await self.type_human(input_field, name, "Scenario Name Input")
            await input_field.press("Enter")
            await asyncio.sleep(1.5)  # Wait for inline creation to complete
            
            # Click the newly created scenario link to open its details view
            import re
            scenario_link = self.page.get_by_text(name, exact=True).first
            try:
                if await scenario_link.count() == 0:
                    scenario_link = self.page.locator("a").filter(has_text=name).first
                
                await scenario_link.wait_for(state="visible", timeout=10000)
                logger.info(f"Navigating to scenario page by clicking link: '{name}'")
                await scenario_link.click()
                await self.page.wait_for_url(re.compile(r"/scenarios/\d+"), timeout=5000)
                await asyncio.sleep(2.0)  # Wait for SPA render
            except Exception as e:
                logger.error(f"Failed to navigate to scenario details page for '{name}': {e}")
                await self.capture_screenshot(f"scenario_nav_failed_{name}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error creating scenario '{name}': {e}")
            await self.capture_screenshot(f"create_scenario_{name}_failed")
            return False

    async def enter_steps(self, steps: list[ScenarioStep], import_mode: str = "default", scenario_name: str = "") -> bool:
        """Enters actions and results into the scenario editor."""
        logger.info(f"Entering {len(steps)} steps into scenario (mode={import_mode})...")
        try:
            if import_mode == "raw":
                return await self.enter_steps_raw(scenario_name, steps)

            # Detect editor type: Gherkin Textarea vs BDD Step Editor vs Classic Manual Step Editor
            is_gherkin = await self.page.locator(".gherkin-editor, .ace_editor, textarea#scenario_gherkin, textarea.gherkin-textarea").count() > 0
            is_bdd = await self.page.locator(".t-add-step-input").count() > 0
            
            if is_gherkin:
                logger.info("Gherkin editor detected. Formatting steps as Gherkin text.")
                return await self._enter_steps_gherkin(steps)
            elif is_bdd:
                logger.info("BDD step editor detected. Entering step-by-step.")
                return await self._enter_steps_bdd(steps)
            else:
                logger.info("Manual steps editor detected. Entering step-by-step.")
                return await self._enter_steps_manual(steps)
        except Exception as e:
            logger.error(f"Failed to enter steps: {e}")
            await self.capture_screenshot("enter_steps_failed")
            return False

    async def enter_steps_raw(self, name: str, steps: list[ScenarioStep]) -> bool:
        """Enters steps using CucumberStudio's Raw Version bulk editor."""
        logger.info(f"Entering steps in Raw Version mode for scenario '{name}'...")
        try:
            # 1. Click "Raw Version" link
            raw_link = None
            raw_link_selectors = [
                self.page.locator("button.t-editor-toggle"),
                self.page.locator(".t-editor-toggle"),
                self.page.locator("button:has-text('Raw version')"),
                self.page.locator("a:has-text('Raw Version')"),
                self.page.locator(".t-raw-version"),
                self.page.locator(".raw-version"),
                self.page.locator("text=Raw Version")
            ]
            for sel in raw_link_selectors:
                if await sel.count() > 0 and await sel.first.is_visible():
                    raw_link = sel.first
                    break
            
            if not raw_link:
                logger.error("Could not find 'Raw Version' link. Falling back to step-by-step editor.")
                return await self.enter_steps(steps, import_mode="default")
            
            await self.click(raw_link, "Raw Version Link")
            await asyncio.sleep(1.5) # Wait for editor to switch
            
            # 2. Find raw text editor textarea
            editor_textarea = None
            editor_locators = [
                self.page.locator(".steps-editor textarea:visible"),
                self.page.locator("textarea.raw-steps"),
                self.page.locator("textarea.t-raw-steps"),
                self.page.locator(".raw-version-editor textarea"),
                self.page.locator("textarea:visible")
            ]
            for loc in editor_locators:
                if await loc.count() > 0 and await loc.first.is_visible():
                    editor_textarea = loc.first
                    break
                    
            if not editor_textarea:
                logger.error("Raw Version editor textarea not found.")
                return False
                
            # 3. Construct raw scenario text
            lines = []
            escaped_name = name.replace("'", "\\'")
            lines.append(f"scenario '{escaped_name}' do")
            
            is_first_action = True
            for step in steps:
                # Actions
                actions = [a.strip() for a in step.action.split('\n') if a.strip()]
                for action in actions:
                    has_keyword = False
                    words = action.split()
                    if words:
                        has_keyword = words[0].lower() in ["given", "when", "then", "and", "but"]
                    
                    if has_keyword:
                        action_text = action
                    else:
                        keyword = "Given" if is_first_action else "When"
                        action_text = f"{keyword} {action}"
                    is_first_action = False
                    
                    escaped_action = action_text.replace('"', '\\"')
                    lines.append(f'  step {{action: "{escaped_action}"}}')
                    
                # Results
                results = [r.strip() for r in step.result.split('\n') if r.strip()] if step.result else []
                for result in results:
                    has_keyword = False
                    words = result.split()
                    if words:
                        has_keyword = words[0].lower() in ["given", "when", "then", "and", "but"]
                        
                    if has_keyword:
                        result_text = result
                    else:
                        result_text = f"Then {result}"
                        
                    escaped_result = result_text.replace('"', '\\"')
                    lines.append(f'  step {{result: "{escaped_result}"}}')
                    
            lines.append("end")
            raw_text = "\n".join(lines)
            
            # 4. Fill text into textarea
            await editor_textarea.focus()
            await editor_textarea.fill(raw_text)
            await asyncio.sleep(0.5)
            
            # 5. Click "Back To Editor" to save and return
            back_link = None
            back_link_selectors = [
                self.page.locator("button.t-editor-toggle"),
                self.page.locator(".t-editor-toggle"),
                self.page.locator("a:has-text('Back To Editor')"),
                self.page.locator("button:has-text('Back To Editor')"),
                self.page.locator(".t-back-to-editor"),
                self.page.locator(".back-to-editor"),
                self.page.locator("text=Back To Editor")
            ]
            for sel in back_link_selectors:
                if await sel.count() > 0 and await sel.first.is_visible():
                    back_link = sel.first
                    break
                    
            if back_link:
                await self.click(back_link, "Back To Editor Link")
                await asyncio.sleep(1.5)
            else:
                logger.warning("Could not find 'Back To Editor' link. Attempting save directly.")
                
            return True
        except Exception as e:
            logger.error(f"Failed to enter steps in Raw Version mode: {e}")
            await self.capture_screenshot("raw_version_failed")
            return False

    async def _enter_steps_manual(self, steps: list[ScenarioStep]) -> bool:
        """Enters steps into classical manual step grids (Action / Expected Result)."""
        # Selectors for inputs
        action_selectors = "textarea[placeholder*='Action'], textarea.step-action, textarea[name*='action'], input[placeholder*='Action']"
        result_selectors = "textarea[placeholder*='Expectation'], textarea[placeholder*='Result'], textarea.step-result, textarea[name*='result'], input[placeholder*='Result']"
        add_step_buttons = [
            self.page.locator("a:has-text('Add step'), button:has-text('Add step'), .add-step-btn, [data-action='add-step']"),
            self.page.locator(".btn:has-text('Step'), .btn:has-text('Add')")
        ]

        for idx, step in enumerate(steps):
            logger.info(f"Adding Step {idx + 1}/{len(steps)}")
            
            # If not first step, click 'Add step'
            if idx > 0:
                step_added = False
                for btn in add_step_buttons:
                    if await btn.count() > 0 and await btn.first.is_visible():
                        await self.click(btn.first, f"Add Step Button for Step {idx + 1}")
                        step_added = True
                        await asyncio.sleep(0.5)
                        break
                if not step_added:
                    # Try pressing Tab/Enter in the last field to create a new step
                    last_result = self.page.locator(result_selectors).last
                    if await last_result.count() > 0:
                        await last_result.press("Tab")
                        await asyncio.sleep(0.3)
            
            # Get action and result inputs (targeting the last ones, since they are newly added)
            action_input = self.page.locator(action_selectors).last
            result_input = self.page.locator(result_selectors).last
            
            if await action_input.count() == 0:
                logger.error(f"Action input not found for step {idx + 1}.")
                return False
                
            # Type action
            await self.type_human(action_input, step.action, f"Step {idx + 1} Action")
            
            # Type result/expectation
            if step.result:
                if await result_input.count() > 0:
                    await self.type_human(result_input, step.result, f"Step {idx + 1} Result")
                else:
                    logger.warning(f"Expected Result field not found for step {idx + 1}.")
                    
        return True

    async def _enter_steps_bdd(self, steps: list[ScenarioStep]) -> bool:
        """Enters steps into CucumberStudio BDD step editor (Action / Expected Result dropdowns)."""
        logger.info("BDD step editor detected. Entering steps via .t-add-step-input...")
        
        # Wait for any previous scenario DOM elements to be removed during SPA navigation
        await asyncio.sleep(2.0)
        
        # Wait up to 10 seconds for the editor and step input field to become visible
        try:
            await self.page.wait_for_selector(".t-add-step-input", state="visible", timeout=10000)
        except Exception as e:
            logger.error(f"Timed out waiting for BDD step input field to become visible: {e}")
            await self.capture_screenshot("bdd_input_not_visible")
            return False
            
        is_first_action = True
        
        for step_idx, step in enumerate(steps):
            # Split actions and expected results by newline to enter them line-by-line
            actions = [a.strip() for a in step.action.split('\n') if a.strip()]
            results = [r.strip() for r in step.result.split('\n') if r.strip()] if step.result else []
            
            # 1. Type Actions
            for action in actions:
                add_step_input = self.page.locator(".t-add-step-input").first
                try:
                    await add_step_input.wait_for(state="visible", timeout=5000)
                except Exception:
                    logger.error("BDD step input field not visible for action.")
                    return False
                    
                await add_step_input.focus()
                await asyncio.sleep(0.5)  # Let focus settle and JS event handlers attach
                
                # Check if the line already starts with a BDD keyword
                has_keyword = False
                words = action.split()
                if words:
                    has_keyword = words[0].lower() in ["given", "when", "then", "and", "but"]
                    
                if has_keyword:
                    action_text = action
                else:
                    keyword = "Given" if is_first_action else "When"
                    action_text = f"{keyword} {action}"
                    
                is_first_action = False
                
                logger.info(f"Typing action line: '{action_text}'")
                await add_step_input.press_sequentially(action_text, delay=30)
                await asyncio.sleep(0.3)
                
                # Click the action option or press Enter
                action_opt = self.page.locator(".t-action-suggestion-txt.action").first
                if await action_opt.count() > 0 and await action_opt.is_visible():
                    await action_opt.click()
                else:
                    await add_step_input.press("Enter")
                await asyncio.sleep(0.5)
                
            # 2. Type Expected Results
            for result in results:
                add_step_input = self.page.locator(".t-add-step-input").first
                try:
                    await add_step_input.wait_for(state="visible", timeout=5000)
                except Exception:
                    logger.error("BDD step input field not visible for result.")
                    return False
                    
                await add_step_input.focus()
                await asyncio.sleep(0.5)  # Let focus settle and JS event handlers attach
                
                # Check if the line already starts with a BDD keyword
                has_keyword = False
                words = result.split()
                if words:
                    has_keyword = words[0].lower() in ["given", "when", "then", "and", "but"]
                    
                if has_keyword:
                    result_text = result
                else:
                    result_text = f"Then {result}"
                
                logger.info(f"Typing result line: '{result_text}'")
                await add_step_input.press_sequentially(result_text, delay=30)
                await asyncio.sleep(0.3)
                
                # Click the result option
                result_opt = self.page.locator(".t-action-suggestion-txt.result").first
                if await result_opt.count() > 0 and await result_opt.is_visible():
                    await result_opt.click()
                else:
                    # Fallback to ArrowUp + Enter
                    await self.page.keyboard.press("ArrowUp")
                    await self.page.keyboard.press("Enter")
                await asyncio.sleep(0.5)
                
        return True

    async def _enter_steps_gherkin(self, steps: list[ScenarioStep]) -> bool:
        """Formats actions and results into Gherkin format and writes into text editor."""
        gherkin_lines = []
        for idx, step in enumerate(steps):
            # Format Action
            prefix = "Given" if idx == 0 else "When"
            gherkin_lines.append(f"  {prefix} {step.action}")
            
            # Format Result
            if step.result:
                gherkin_lines.append(f"  Then {step.result}")
                
        gherkin_text = "\n".join(gherkin_lines)
        
        # Paste or type Gherkin text
        editor_textareas = [
            self.page.locator("textarea.ace_text-input"),
            self.page.locator("textarea#scenario_gherkin"),
            self.page.locator("textarea.gherkin-textarea"),
            self.page.locator("div.editor textarea")
        ]
        
        editor = None
        for ed in editor_textareas:
            if await ed.count() > 0:
                editor = ed
                break
                
        if not editor:
            logger.error("Could not find Gherkin editor textarea.")
            return False
            
        await self.type_human(editor, gherkin_text, "Gherkin Editor Textarea")
        return True

    async def save_scenario(self) -> bool:
        """Clicks the Save Scenario button if present."""
        logger.info("Saving scenario...")
        try:
            save_buttons = [
                self.page.locator("button:has-text('Save'), input[type='submit'][value='Save']"),
                self.page.locator(".btn-save, .save-scenario-btn"),
                self.page.locator("a:has-text('Save')")
            ]
            
            for btn in save_buttons:
                if await btn.count() > 0 and await btn.is_visible():
                    await self.click(btn, "Save Button")
                    await self.page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(1.0)
                    logger.info("Scenario saved.")
                    return True
            
            logger.info("No explicit save button found (assuming auto-save is active).")
            return True
        except Exception as e:
            logger.error(f"Error saving scenario: {e}")
            return False

    async def go_back_to_folder(self, folder_name: str) -> bool:
        """Navigates back to the current folder by clicking the breadcrumb or returning to project root."""
        logger.info(f"Navigating back to folder: '{folder_name}'")
        try:
            # Try breadcrumb link first
            breadcrumb = self.page.locator(f".breadcrumb a:has-text('{folder_name}'), .breadcrumbs a:has-text('{folder_name}'), .t-breadcrumb a:has-text('{folder_name}')")
            if await breadcrumb.count() > 0:
                await self.click(breadcrumb.first, f"Breadcrumb '{folder_name}'")
                await self.page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(0.5)
                return True
                
            # Direct project root URL fallback to keep project context
            import re
            match = re.match(r"(https?://[^/]+/projects/\d+)", self.page.url)
            if match:
                project_url = match.group(1).rstrip("/") + "/test-plan"
                logger.info(f"Navigating back to project root scenarios: {project_url}")
                await self.page.goto(project_url, wait_until="domcontentloaded")
                await asyncio.sleep(1.0)
                return True

            logger.warning("Could not find project root URL. Navigating to Projects dashboard.")
            await self.page.goto(settings.PROJECTS_URL, wait_until="domcontentloaded")
            return True
        except Exception as e:
            logger.error(f"Error returning to folder: {e}")
            return False
