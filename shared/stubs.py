import json
from pathlib import Path
from shared.schemas import EmailDoc


def redact(text: str):
    return text, {}


def restore(text: str, mapping: dict) -> str:
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text


def list_bills(folder: str):
    return []


def load_sample_emails() -> list[EmailDoc]:
    data = json.loads((Path(__file__).parent / "sample_emails.json").read_text(encoding="utf-8"))
    return [EmailDoc(**d) for d in data]