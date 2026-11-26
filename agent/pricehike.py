from controlhub import storage
from shared.schemas import Subscription


def apply(sub: Subscription, email_date: str, email_id: str) -> Subscription:
    earlier = [
        r for r in storage.all_("receipt")
        if r["merchant"].lower() == sub.merchant.lower()
        and r["email_id"] != email_id and r["date"] <= email_date
    ]
    if earlier:
        last = sorted(earlier, key=lambda r: r["date"])[-1]
        if abs(last["amount"] - sub.amount) > 0.01:
            sub.old_amount = last["amount"]
            sub.flags.append("price_hike" if sub.amount > last["amount"] else "price_drop")
    storage.put("receipt", email_id, {
        "merchant": sub.merchant, "amount": sub.amount, "date": email_date, "email_id": email_id,
    })
    return sub