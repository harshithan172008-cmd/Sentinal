import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from controlhub import audit, policy
from controlhub.injection_guard import sanitize, scan, wrap_untrusted

try:
    from controlhub.redactor import redact, restore  # Anagha's real redactor
    REDACTOR_IS_STUB = False
except Exception as e:  # not merged yet, or failed to load
    from shared.stubs import redact, restore
    REDACTOR_IS_STUB = True
    print(f"[ControlHub] WARNING: using stub redactor, nothing is masked ({e})")

ROOT = Path(__file__).resolve().parents[1]
SERVERS = {
    "gmail": ROOT / "connectors" / "gmail_server.py",
    "calendar": ROOT / "connectors" / "calendar_server.py",
    "pdf": ROOT / "connectors" / "pdf_server.py",
}
UNTRUSTED_TOOLS = {"gmail.search_billing_emails", "pdf.read_bill"}
def _root_cause(e):
    while isinstance(e, BaseExceptionGroup) and e.exceptions:
        e = e.exceptions[0]
    return e


class Gateway:
    def __init__(self):
        self.tainted = False
        self.killed = False
        self.views = []      # for the 'What the AI Saw' panel (memory only)
        self.mappings = {}   # placeholder -> real value (memory only, never saved)

    def kill(self):
        self.killed = True
        audit.log("user", "kill_switch", "-", "block", "all access revoked")

    async def call(self, tool: str, args: dict | None = None, actor: str = "agent") -> dict:
        args = args or {}
        if self.killed:
            audit.log(actor, "call", tool, "block", "kill switch active")
            return {"status": "blocked", "reason": "kill switch active"}
        decision, reason = policy.check(tool, self.tainted)
        audit.log(actor, "call", tool, decision, reason)
        if decision == "block":
            return {"status": "blocked", "reason": reason}
        if decision == "ask":
            return {"status": "needs_approval", "tool": tool, "args": args, "reason": reason}
        return await self._run(tool, args, actor)

    async def execute_approved(self, tool: str, args: dict, actor: str = "user") -> dict:
        """Called by the approval queue after the user clicks Approve."""
        if self.killed:
            return {"status": "blocked", "reason": "kill switch active"}
        decision, reason = policy.check(tool, self.tainted)
        if decision == "block":
            audit.log(actor, "approved", tool, "block", reason)
            return {"status": "blocked", "reason": reason}
        audit.log(actor, "approved", tool, "allow", "user approved")
        return await self._run(tool, args, actor)

    async def _run(self, tool: str, args: dict, actor: str) -> dict:
        try:
            data = await self._invoke(tool, args)
        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            real = _root_cause(e)
            audit.log(actor, "error", tool, "allow", type(real).__name__)
            return {"status": "error", "reason": f"{type(real).__name__}: {real}"}
        if tool in UNTRUSTED_TOOLS:
            self.tainted = True
            if isinstance(data, list):
                data = [self._clean_doc(d) for d in data]
                n = len(data)
            else:
                data = self._clean_doc(data)
                n = 1
            audit.log("controlhub", "sanitize_redact", tool, "allow", f"{n} document(s); session tainted")
        return {"status": "ok", "data": data}
    
    def _clean_doc(self, doc: dict) -> dict:
        raw = doc.get("body_html") or doc.get("body_text") or ""
        flags = scan(raw)
        clean = sanitize(raw)
        masked_body, body_map = redact(clean)
        masked_subj, subj_map = redact(doc.get("subject", ""))
        self.mappings[doc["id"]] = {"body": body_map, "subject": subj_map}
        wrapped = wrap_untrusted(masked_body)
        self.views.append({"id": doc["id"], "original": raw, "masked": wrapped, "flags": flags,
                           "sender": doc.get("sender", ""), "subject": doc.get("subject", ""),
                           "masked_subject": masked_subj,
                           "date": doc.get("date", ""), "source": doc.get("source", "gmail")})
        return {
            "id": doc["id"],
            "sender": doc.get("sender", ""),
            "subject": masked_subj,
            "date": doc.get("date", ""),
            "body_text": wrapped,
            "source": doc.get("source", "gmail"),
            "injection_flags": flags,
        }

    async def _invoke(self, tool: str, args: dict):
        server, name = tool.split(".", 1)
        path = SERVERS.get(server)
        if not path or not path.exists():
            raise RuntimeError(f"connector '{server}' is not available yet")
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(path)],
                        env={k: os.environ[k] for k in ("BILLS_DIR", "TZ_NAME", "TZ_OFFSET_MINUTES") if k in os.environ}
            | {"FAKE_MODE": os.getenv("FAKE_MODE", "1")},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.call_tool(name, args)
                is_err = getattr(res, "isError", None)
        if is_err is None:
            is_err = getattr(res, "is_error", False)
        if is_err:
            raise RuntimeError(res.content[0].text if res.content else "tool error")
        return json.loads(res.content[0].text)
