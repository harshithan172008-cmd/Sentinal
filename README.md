# Sentinel

**A zero-trust MCP assistant for subscriptions, bills, and renewals**[cite: 1]  
**Hackathon Track:** Track 1 — *Make MCP Matter* (*Less magic, more utility*)[cite: 1]  
**Build & Run Cost:** ₹0 (100% free and open-source tools, local-first)[cite: 1]

> **One-Line Pitch:** Sentinel finds hidden price hikes, ending free trials and upcoming bills in your emails and prepares reminders and cancellation drafts for your approval, while ControlHub masks your private details, blocks malicious emails and never touches your bank account[cite: 1].

---

## Team & Presentation

- **Team Name:** `The Panic Pushers`
- **Team ID:** `843f4120`[cite: 2]
- **College / Event:** Ramaiah Institute of Technology — wHACKiest 2026[cite: 2, 5]
- **Presentation (PPT) Link:** `
https://docs.google.com/presentation/d/1Fml_sfwIPUtkwxDXzWESM3TOigBAsqc9/edit?usp=drivesdk&ouid=100004759257099192431&rtpof=true&sd=true`[cite: 5]

### Team Members
- **Member 1 (Lead):** `Harshitha N` — USN: `1MS25CS063`[cite: 2]
- **Member 2:** `Anagha Pai` — USN: `1MS25CS012`[cite: 2]
- **Member 3:** `Ananya AU` — USN: `1MS25CS017`[cite: 2]


---

## Why This Exists

Money quietly leaks through recurring subscriptions when free trials convert to paid plans, prices rise via one-line notices, or bill deadlines get buried in the inbox[cite: 1]. Today, users face an unfair choice[cite: 1]:
- **Subscription trackers** typically require bank logins, card access, or cloud financial sharing[cite: 1].
- **AI assistants** often ask for broad, unchecked access to your inbox—where a single malicious email can trick an agent into acting[cite: 1].

**Sentinel + ControlHub** gives you a helpful daily assistant without giving away control[cite: 1].

---

## How It Works: Two Parts, One Product

| Component | MCP Role | Responsibility |
| :--- | :--- | :--- |
| **Sentinel** *(The Assistant)*[cite: 1] | MCP Client[cite: 1] | Scans billing emails and a chosen folder of PDF bills, detects renewals/trials/price changes via Pydantic-validated extraction and deterministic Python comparison, links source proof, and proposes actions[cite: 1]. |
| **ControlHub** *(The Gateway)*[cite: 1] | MCP Server to Sentinel; MCP Client to Connectors[cite: 1] | Enforces `policy.yaml` rules in code (`Allow` / `Block` / `Ask`), redacts PII before the LLM sees text, isolates untrusted email/PDF content, manages the approval queue and undo, writes a hash-chained audit log, and provides a kill switch[cite: 1]. |
| **Gmail / Calendar / PDF Servers**[cite: 1] | MCP Servers[cite: 1] | Thin wrappers around Gmail (`readonly` + `compose` drafts only), Google Calendar (`calendar.events`), and one local PDF folder (`pdfplumber` + `Tesseract`)[cite: 1]. |

---

## Key Features

- **Inbox & PDF Bill Scanning:** Finds active subscriptions, expiring free trials, and upcoming bill dates across billing-related emails and a user-selected PDF folder[cite: 1].
- **Deterministic Price-Hike Detection:** Plain Python compares new notices against stored receipts (e.g., `Rs. 499 to Rs. 649 from 1 Dec`) rather than relying on LLM guesswork[cite: 1].
- **Renewal Timeline:** Local view of upcoming renewals and monthly totals without any bank connection[cite: 1].
- **Source Proof & Risk Flags:** Every proposal links back to the exact email line or PDF snippet it came from, and flags uncertain dates, external recipients, or price jumps[cite: 1].
- **PII Redaction & "What the AI Saw" Panel:** Masks sensitive details (phone numbers, addresses, card/account numbers, national IDs, OTPs) into placeholders (such as `[PHONE_1]`) before the model reads text, with a UI panel showing before/after masking[cite: 1].
- **Prompt-Injection Isolation:** Treats email bodies and documents as untrusted data and locks outgoing tools in code after reading untrusted content[cite: 1].
- **Approval Queue, Per-Item Undo & Kill Switch:** Nothing is created, drafted, or modified without user approval; users can edit, approve, reject, or undo calendar events and drafts, export CSV, wipe local data, or cut off access with one click[cite: 1].

---

## Hard Boundaries

- **No bank, UPI, or payment connections, ever.**[cite: 1]
- **Gmail access is read-only plus draft creation**—the app has no permission to send emails[cite: 1].
- **Propose-only execution**—nothing is created, sent, or changed until you approve it[cite: 1].
- **Minimal local storage**—emails are processed on demand; only extracted fields (merchant, amount, date, source snippet) are encrypted and stored locally, never raw emails[cite: 1].

---

## Tech Stack (100% Free)

- **MCP Framework:** Python `mcp` SDK (`FastMCP`)[cite: 1]
- **Default LLM (Local):** `Ollama` with `Qwen2.5` (`qwen2.5:3b`) or `Llama 3.1/3.2` (`llama3.1:8b`)[cite: 1]
- **Optional Cloud Fallback:** Free tier of Gemini or Groq (optional only; no billing account attached)[cite: 1]
- **Structured Extraction:** `pydantic`[cite: 1]
- **Price-Hike & Injection Guard:** Deterministic Python rules[cite: 1]
- **PII Redaction:** Microsoft `Presidio` + custom regex (including Indian formats such as PAN, phone numbers, UPI IDs, card numbers, and OTPs)[cite: 1]
- **Policy Engine:** `policy.yaml` + `pyyaml`[cite: 1]
- **Google APIs & Auth:** Gmail API (`gmail.readonly`, `gmail.compose`), Google Calendar API (`calendar.events`), `google-auth-oauthlib` (OAuth 2.0 desktop flow)[cite: 1]
- **PDF Parsing:** `pdfplumber` and `pytesseract` + Tesseract OCR[cite: 1]
- **Storage & Audit Log:** SQLite + `Fernet` (`cryptography`) for encrypted extracted fields; SQLite + `SHA-256` (`hashlib`) hash-chained audit log[cite: 1]
- **UI & Export:** `Streamlit`, `Plotly`, and `pandas` (CSV export & wipe)[cite: 1]
- **Optional Scheduler:** `APScheduler`[cite: 1]

---

## Project Layout

```text
sentinel/
  app.py                    # Streamlit UI (Approval Queue, Timeline, "What the AI Saw", Audit Log, Kill Switch)
  agent/                    # Extraction, Pydantic validation, price-hike logic, proposals
  controlhub/
    server.py               # FastMCP gateway
    policy.yaml             # Allow / Block / Ask rules
    redactor.py             # Presidio + regex PII masking
    injection_guard.py      # Untrusted text isolation & outgoing tool lock
    audit.py                # SHA-256 hash-chained audit log
  connectors/
    gmail_server.py
    calendar_server.py
    pdf_server.py
  db/                       # Encrypted SQLite database
  tests/attack_emails/      # Sample malicious emails for prompt-injection testing
```[cite: 1]

---

## Setup & Installation

```bash
pip install mcp google-api-python-client google-auth-oauthlib presidio-analyzer presidio-anonymizer spacy pdfplumber pytesseract pydantic pyyaml streamlit plotly pandas cryptography ollama apscheduler
python -m spacy download en_core_web_sm
ollama pull qwen2.5:3b
```[cite: 1]

### Run the integrated custom frontend (safe local demo)

The `sentinel-frontend/` page can use the existing Python scan, subscription, approval, timeline, privacy, and audit modules through `run_frontend.py`. From the repository folder, install the listed dependencies and start the local bridge:

```powershell
py -m pip install -r requirements.txt
py run_frontend.py
```

Open `http://127.0.0.1:8000`. The bridge binds to loopback only, forces `FAKE_MODE=1` and `USE_LLM=0`, and uses bundled sample messages. It does not connect to Gmail, Calendar, or an external model. Approvals exercise the existing backend in fake mode; they do not create real drafts or calendar events. The top-bar sign-in is a demo-only continuation and does not authenticate with Google; the repository OAuth helper is not wired into this frontend bridge. The frontend uses a separate temporary database and encryption key—not the Streamlit app’s data—and removes them when the process exits. Press `Ctrl+C` in PowerShell to stop it.

The original Streamlit interface is still available separately with `py -m streamlit run app.py`. Do not run both on the same port; Streamlit uses its own default port.

### Free-Cost & OAuth Checklist
- **Never attach a billing account** to Google Cloud or AI Studio[cite: 1].
- **Use local Ollama by default** to avoid cloud rate limits during demos[cite: 1].
- **Google OAuth Testing Mode:** Add teammates as test users on the OAuth consent screen, and re-authorize ~7 days before your demo/event since testing refresh tokens expire periodically[cite: 1].

---

## Honest Limitations

- **Prompt-injection detection is not infallible:** Protection relies on deterministic code rules—locking outgoing tools after untrusted content and requiring explicit user approval[cite: 1].
- **LLM extraction can make mistakes:** Source-proof links and warning flags on unclear dates, external recipients, or sharp price jumps help catch errors before approval[cite: 1].
- **Undo scope:** Undo deletes created Calendar events or Gmail drafts; sent emails cannot be unsent, which is why automatic sending is disabled[cite: 1].
- **Local inference speed:** Pre-filtering emails by billing keywords and caching extracted results keeps runs responsive on local hardware[cite: 1].
