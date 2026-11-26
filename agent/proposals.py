from datetime import datetime, timedelta

from shared.schemas import Proposal, Subscription

LABEL = {"trial": "trial ends", "active": "renews", "bill": "bill due"}


def build_proposals(sub: Subscription) -> list[Proposal]:
    out = []
    flags = list(sub.flags)
    if sub.old_amount is not None:
        flags.append(f"Rs.{sub.old_amount:g} -> Rs.{sub.amount:g}")
    label = LABEL.get(sub.status, "renews")

    if sub.renewal_date:
        d = datetime.fromisoformat(sub.renewal_date) - timedelta(days=2)
        start = d.replace(hour=10, minute=0).isoformat()
        end = d.replace(hour=10, minute=30).isoformat()
        out.append(Proposal(
            id=f"{sub.source_email_id}-reminder", kind="reminder",
            title=f"{sub.merchant}: {label} {sub.renewal_date} (Rs.{sub.amount:g})",
            details={"title": f"{sub.merchant} {label} soon", "start": start, "end": end,
                     "description": f"Rs.{sub.amount:g}. Source: {sub.source_snippet}"},
            source_snippet=sub.source_snippet, flags=flags))

    if sub.status == "trial" or "price_hike" in sub.flags:
        when = f" before {sub.renewal_date}" if sub.renewal_date else ""
        out.append(Proposal(
            id=f"{sub.source_email_id}-draft", kind="draft",
            title=f"Draft: cancel {sub.merchant}",
            details={"to": "", "subject": f"Cancel my {sub.merchant} subscription",
                     "body": f"Hello,\n\nPlease cancel my {sub.merchant} subscription{when} "
                             f"and confirm by reply.\n\nThank you"},
            source_snippet=sub.source_snippet, flags=flags + ["add_recipient"]))

    out.append(Proposal(
        id=f"{sub.source_email_id}-tracker", kind="tracker",
        title=f"Track: {sub.merchant} Rs.{sub.amount:g}",
        details={"merchant": sub.merchant, "amount": sub.amount, "renewal_date": sub.renewal_date,
                 "status": sub.status, "old_amount": sub.old_amount},
        source_snippet=sub.source_snippet, flags=flags))
    return out