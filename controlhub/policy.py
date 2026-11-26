from pathlib import Path
import yaml

_PATH = Path(__file__).parent / "policy.yaml"
WRITE_PREFIXES = ("create_", "delete_", "send_", "forward_")


def load() -> dict:
    return yaml.safe_load(_PATH.read_text(encoding="utf-8")) or {}


def check(tool: str, tainted: bool = False) -> tuple[str, str]:
    """Returns (decision, reason). decision is 'allow', 'ask' or 'block'."""
    cfg = load()
    tools = cfg.get("tools", {})
    if tool in tools:
        decision = tools[tool]
        reason = f"policy: {tool} is {decision}"
    else:
        decision = cfg.get("default", "block")
        reason = f"{tool} is not in policy (default {decision})"
    name = tool.split(".")[-1]
    if decision == "allow" and name.startswith(WRITE_PREFIXES):
        decision, reason = "ask", "write tool always needs approval"
    if tainted and decision == "ask":
        reason += " (session has read untrusted content)"
    return decision, reason