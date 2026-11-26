from typing import Optional, Literal
from pydantic import BaseModel, Field


class EmailDoc(BaseModel):
    id: str
    sender: str
    subject: str
    date: str
    body_text: str
    body_html: Optional[str] = None
    source: Literal["gmail", "pdf"] = "gmail"


class Subscription(BaseModel):
    merchant: str
    amount: float
    currency: str = "INR"
    renewal_date: Optional[str] = None
    status: Literal["active", "trial", "bill"]
    old_amount: Optional[float] = None
    source_email_id: str
    source_snippet: str
    flags: list[str] = Field(default_factory=list)


class Proposal(BaseModel):
    id: str
    kind: Literal["reminder", "draft", "tracker"]
    title: str
    details: dict = Field(default_factory=dict)
    source_snippet: str = ""
    flags: list[str] = Field(default_factory=list)
    status: Literal["pending", "approved", "rejected", "undone"] = "pending"
    external_id: Optional[str] = None


class AuditEntry(BaseModel):
    id: int
    ts: str
    actor: str
    action: str
    tool: str
    decision: Literal["allow", "block", "ask"]
    detail: str = ""
    prev_hash: str
    hash: str