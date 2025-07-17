from pathlib import Path
from core.config import settings

def generate_system_prompt(history:str) -> str:
    original_prompt = Path(settings.system_prompt_path).read_text(encoding='utf-8')

    system_prompt = original_prompt.replace("{history}", history)

    return system_prompt