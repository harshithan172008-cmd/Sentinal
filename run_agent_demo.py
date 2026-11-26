import asyncio
import os

os.environ.setdefault("FAKE_MODE", "1")

from agent.pipeline import run_scan
from controlhub import approvals, audit
from controlhub.gateway import Gateway


async def main():
    gw = Gateway()
    r = await run_scan(gw)
    print("subscriptions:", len(r["subscriptions"]), "| new proposals:", len(r["proposals"]), "| skipped:", r["skipped"])
    for s in r["subscriptions"]:
        print(f"  {s.merchant} Rs.{s.amount:g} {s.status} renews={s.renewal_date} old={s.old_amount} flags={s.flags}")
    print("pending:")
    for p in approvals.list_all("pending"):
        print(f"  {p.id}: {p.title}")

    a = await approvals.approve(gw, "s2-reminder")
    print("approve s2-reminder ->", a["status"], a.get("proposal").external_id if a["status"] == "ok" else a)
    a = await approvals.approve(gw, "s2-draft")
    print("approve s2-draft without recipient ->", a["status"], a.get("reason"))
    a = await approvals.approve(gw, "s2-draft", {"to": "support@netflix.com"})
    print("approve s2-draft with recipient ->", a["status"])
    u = await approvals.undo(gw, "s2-reminder")
    print("undo s2-reminder ->", u["status"], u["proposal"].status)
    print("audit chain intact:", audit.verify_chain())


asyncio.run(main())