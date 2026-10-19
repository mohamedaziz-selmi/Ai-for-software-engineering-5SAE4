import re
from dataclasses import dataclass

@dataclass
class Anonymized:
    text: str
    replacements: dict[str, str]

def anonymize(text: str) -> Anonymized:
    """Replace direct identifiers before a prompt is sent to an LLM."""
    replacements: dict[str, str] = {}
    counter = {"name": 0, "email": 0, "phone": 0}
    def replace(kind: str, value: str) -> str:
        key = f"<{kind.upper()}_{counter[kind]}>"
        counter[kind] += 1
        replacements[key] = value
        return key
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", lambda m: replace("email", m.group()), text)
    text = re.sub(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)", lambda m: replace("phone", m.group()), text)
    text = re.sub(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b", lambda m: replace("name", m.group()), text)
    return Anonymized(text, replacements)

def restore(text: str, replacements: dict[str, str]) -> str:
    """Restore identifiers only after schema validation has succeeded."""
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text
