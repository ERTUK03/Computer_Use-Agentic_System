from pathlib import Path

def load_prompt(name):
    return Path(f"Prompts/{name}.md").read_text(encoding="utf-8")