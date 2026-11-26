from controlhub import audit, storage
from shared.schemas import Proposal

TOOL = {"reminder": "calendar.create_event", "draft": "gmail.create_draft"}
UNDO = {"reminder": ("calendar.delete_event", "event_id"), "draft": ("gmail.delete_draft", "draft_id")}


def add(p: Proposal) -> bool:
    if storage.get("proposal", p.id):
        return False
    storage.put("proposal", p.id, p.model_dump())
    return True


def get(id_: str):
    d = storage.get("proposal", id_)
    return Proposal(**d) if d else None


def list_all(status: str | None = None) -> list[Proposal]:
    items = [Proposal(**d) for d in storage.all_("proposal")]
    items = [p for p in items if status is None or p.status == status]
    return sorted(items, key=lambda p: p.id)


def _save(p: Proposal) -> None:
    storage.put("proposal", p.id, p.model_dump())


def reject(id_: str) -> None:
    p = get(id_)
    if p and p.status == "pending":
        p.status = "rejected"
        _save(p)
        audit.log("user", "reject", p.kind, "allow", id_)


async def approve(gw, id_: str, edits: dict | None = None) -> dict:
    p = get(id_)
    if not p or p.status != "pending":
        return {"status": "error", "reason": "not pending"}
    if edits:
        p.details.update(edits)
    if p.kind == "draft" and not p.details.get("to"):
        return {"status": "error", "reason": "recipient required: edit the draft first"}
    if p.kind in TOOL:
        res = await gw.execute_approved(TOOL[p.kind], dict(p.details))
        if res["status"] != "ok":
            return res
        p.external_id = res["data"].get(UNDO[p.kind][1])
    else:
        audit.log("user", "approve", "local.tracker", "allow", id_)
    p.status = "approved"
    _save(p)
    return {"status": "ok", "proposal": p}


async def undo(gw, id_: str) -> dict:
    p = get(id_)
    if not p or p.status != "approved":
        return {"status": "error", "reason": "nothing to undo"}
    if p.kind in UNDO and p.external_id:
        tool, key = UNDO[p.kind]
        res = await gw.execute_approved(tool, {key: p.external_id})
        if res["status"] != "ok":
            return res
    audit.log("user", "undo", p.kind, "allow", id_)
    p.status = "undone"
    _save(p)
    return {"status": "ok", "proposal": p}