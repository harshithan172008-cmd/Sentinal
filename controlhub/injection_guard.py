import re
from html.parser import HTMLParser

ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u200e\u200f\u2060\ufeff]")
HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0|opacity\s*:\s*0"
    r"|(?<![-\w])color\s*:\s*(#fff(?:fff)?|white)\b",
    re.I,
)
SUSPICIOUS = re.compile(
    r"ignore (all |any )?(previous|prior) instructions|forward (all|every)|delete (all|every)"
    r"|system prompt|you are now|send .{0,40}@",
    re.I,
)
VOID = {"br", "hr", "img", "input", "meta", "link"}


class _Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if tag == "br":
                self.out.append(" ")
            return
        a = dict(attrs)
        hid = tag in ("script", "style", "head") or "hidden" in a or bool(HIDDEN_STYLE.search(a.get("style") or ""))
        self.stack.append(hid)
        if hid:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        if self.stack.pop():
            self.hidden -= 1

    def handle_data(self, data):
        if self.hidden == 0:
            self.out.append(data)


def sanitize(raw: str) -> str:
    """Strip HTML, comments, hidden text and zero-width characters."""
    if not raw:
        return ""
    if re.search(r"<[a-zA-Z!/][^>]*>", raw):
        p = _Extractor()
        try:
            p.feed(raw)
            p.close()
        except Exception:
            pass
        text = " ".join(p.out)
    else:
        text = raw
    text = ZERO_WIDTH.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def scan(raw: str) -> list[str]:
    """Flags only. The real protection is policy rules in code, not this."""
    flags = []
    if raw and (HIDDEN_STYLE.search(raw) or "<!--" in raw):
        flags.append("hidden_content")
    if raw and ZERO_WIDTH.search(raw):
        flags.append("zero_width_chars")
    if raw and SUSPICIOUS.search(raw):
        flags.append("suspicious_instruction")
    return flags


def wrap_untrusted(text: str) -> str:
    return f"<untrusted_data>\n{text}\n</untrusted_data>"