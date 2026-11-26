from agent.extract import extract
from agent.pricehike import apply
from agent.proposals import build_proposals
from controlhub import approvals, storage


async def run_scan(gw, max_results: int = 20) -> dict:
    r = await gw.call("gmail.search_billing_emails", {"max_results": max_results})
    if r["status"] != "ok":
        return r
    subs, new_props, skipped = [], [], 0
    for d in sorted(r["data"], key=lambda x: x.get("date", "")):
        sub = extract(d)
        if not sub:
            skipped += 1
            continue
        sub = apply(sub, d.get("date", ""), d["id"])
        storage.put("subscription", d["id"], sub.model_dump())
        subs.append(sub)
        for p in build_proposals(sub):
            if approvals.add(p):
                new_props.append(p)
    return {"status": "ok", "subscriptions": subs, "proposals": new_props, "skipped": skipped}