from agent.extract import extract
from agent.pricehike import apply
from agent.proposals import build_proposals
from controlhub import approvals, storage


async def _collect_docs(gw, max_results: int) -> tuple[list, str | None]:
    docs = []
    r = await gw.call("gmail.search_billing_emails", {"max_results": max_results})
    if r["status"] != "ok":
        return docs, r.get("reason", "Gmail read failed")
    docs.extend(r["data"])
    # PDF bills are optional: if the PDF connector is missing or empty, just skip it.
    lst = await gw.call("pdf.list_bills", {})
    if lst["status"] == "ok" and isinstance(lst["data"], list):
        for path in lst["data"]:
            d = await gw.call("pdf.read_bill", {"path": path})
            if d["status"] == "ok":
                docs.append(d["data"])
    return docs, None


async def _flag_clashes(gw, proposals) -> None:
    for p in proposals:
        if p.kind != "reminder":
            continue
        try:
            start = p.details["start"]
            end = p.details["end"]
        except KeyError:
            continue
        r = await gw.call("calendar.list_events", {"start": start, "end": end})
        if r["status"] == "ok" and r["data"]:
            names = ", ".join(e.get("summary", "event") for e in r["data"][:3])
            p.flags.append(f"clashes with: {names}")


async def run_scan(gw, max_results: int = 20) -> dict:
    docs, err = await _collect_docs(gw, max_results)
    if err:
        return {"status": "error", "reason": err}
    subs, new_props, skipped = [], [], 0
    for d in sorted(docs, key=lambda x: x.get("date", "")):
        sub = extract(d)
        if not sub:
            skipped += 1
            continue
        sub = apply(sub, d.get("date", ""), d["id"])
        storage.put("subscription", d["id"], sub.model_dump())
        subs.append(sub)
        fresh = [p for p in build_proposals(sub) if not approvals.get(p.id)]
        await _flag_clashes(gw, fresh)
        for p in fresh:
            if approvals.add(p):
                new_props.append(p)
    return {"status": "ok", "subscriptions": subs, "proposals": new_props, "skipped": skipped}