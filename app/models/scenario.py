class ScenarioStep:
    def __init__(self, action: str = "", result: str = ""):
        self.action = action.strip()
        self.result = result.strip()

    def __repr__(self):
        return f"Step(Action: {self.action[:20]}..., Result: {self.result[:20]}...)"


class ScenarioModel:
    def __init__(self, name: str, folders: list[str]):
        self.name = name.strip()
        self.folders = [f.strip() for f in folders if f.strip()]
        self.steps: list[ScenarioStep] = []

    def add_step(self, action: str, result: str):
        self.steps.append(ScenarioStep(action, result))

    def __repr__(self):
        return f"Scenario('{self.name}', Folders: {self.folders}, Steps: {len(self.steps)})"
