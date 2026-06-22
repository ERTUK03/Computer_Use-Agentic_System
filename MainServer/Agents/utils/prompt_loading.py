from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = BASE_DIR / "Prompts"

def load_prompt(name):
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")