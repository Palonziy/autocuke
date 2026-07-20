import logging
from pathlib import Path
from app.models.scenario import ScenarioModel

logger = logging.getLogger("CucumberStudioImporter")

class TXTParser:
    @staticmethod
    def parse_file(file_path: Path) -> list[ScenarioModel]:
        """
        Parses a single TXT scenario file.
        Supports UTF-8, ignores comments (starting with # or //) and blank lines.
        """
        scenarios: list[ScenarioModel] = []
        folders: list[str] = []
        
        current_scenario: ScenarioModel | None = None
        current_action_lines: list[str] = []
        current_result_lines: list[str] = []
        
        # State machine states: OUTSIDE, READING_ACTION, READING_RESULT
        state = "OUTSIDE"

        def save_current_step():
            if current_scenario is not None:
                action_str = "\n".join(current_action_lines).strip()
                result_str = "\n".join(current_result_lines).strip()
                if action_str or result_str:
                    current_scenario.add_step(action_str, result_str)
            current_action_lines.clear()
            current_result_lines.clear()

        def save_current_scenario():
            nonlocal current_scenario
            if current_scenario is not None:
                save_current_step()
                if current_scenario.steps:
                    scenarios.append(current_scenario)
                else:
                    logger.warning(f"Scenario '{current_scenario.name}' in {file_path.name} has no steps. Skipping.")
                current_scenario = None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            
            # Skip blank lines and comments
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            
            # Detect folder / subfolder directives
            if line.lower().startswith("folder:"):
                save_current_scenario()
                folder_name = line[len("folder:"):].strip()
                folders = [folder_name]
                state = "OUTSIDE"
                continue
                
            if line.lower().startswith("subfolder:"):
                save_current_scenario()
                subfolder_name = line[len("subfolder:"):].strip()
                folders.append(subfolder_name)
                state = "OUTSIDE"
                continue

            # Detect Scenario
            if line.lower().startswith("scenario:"):
                save_current_scenario()
                scenario_name = line[len("scenario:"):].strip()
                current_scenario = ScenarioModel(scenario_name, folders)
                state = "INSIDE"
                continue

            # Detect Action
            if line.lower().startswith("action:"):
                if current_scenario is None:
                    logger.warning(f"Line {line_num} in {file_path.name}: Found 'Action:' outside of a Scenario block.")
                    continue
                # Save previous action/result step if we already completed a pair
                if current_result_lines:
                    save_current_step()
                state = "READING_ACTION"
                inline_text = line[len("action:"):].strip()
                if inline_text:
                    current_action_lines.append(inline_text)
                continue

            # Detect Result
            if line.lower().startswith("result:"):
                if current_scenario is None:
                    logger.warning(f"Line {line_num} in {file_path.name}: Found 'Result:' outside of a Scenario block.")
                    continue
                state = "READING_RESULT"
                inline_text = line[len("result:"):].strip()
                if inline_text:
                    current_result_lines.append(inline_text)
                continue

            # Detect End Scenario
            if line.upper() == "END_SCENARIO":
                save_current_scenario()
                state = "OUTSIDE"
                continue

            # Accumulate content based on state
            if state == "READING_ACTION":
                current_action_lines.append(line)
            elif state == "READING_RESULT":
                current_result_lines.append(line)
            elif state == "INSIDE":
                # Text inside scenario block but before any Action/Result
                logger.warning(f"Line {line_num} in {file_path.name}: Ignored text inside scenario block before Action/Result: '{line}'")
            else:
                # Text outside any block
                logger.warning(f"Line {line_num} in {file_path.name}: Ignored text outside scenario block: '{line}'")

        # Save final scenario if file ended without END_SCENARIO
        save_current_scenario()

        return scenarios
