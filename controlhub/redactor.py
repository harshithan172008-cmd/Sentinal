import re

PRIORITY = {"EMAIL": 0, "UPI": 1, "PAN": 2, "OTP": 3, "PIN": 4, "NUM": 5}

EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
UPI_RE = re.compile(r"(?<![\w.\-])[\w.\-]{2,}@[A-Za-z]{2,}(?![\w.@])")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
OTP_RE = re.compile(
    r"(?i)\b(?:otp|one[- ]time (?:password|code)|verification code|passcode|security code)\b"
    r"[^\d\n]{0,25}?(\d{4,8})\b"
)
OTP_REV_RE = re.compile(
    r"(?i)\b(\d{4,8})\b(?=[^\n.]{0,25}\b(?:otp|verification code|passcode)\b)"
)
PIN_RE = re.compile(r"(?i)\b(?:pin ?code|pincode|pin)\b[^\d\n]{0,10}?(\d{6})\b")
CAND_RE = re.compile(r"(?<!\w)\+?\d+(?:[ \-]\d+)*(?!\w)")


def _luhn(d: str) -> bool:
    total, alt = 0, False
    for ch in reversed(d):
        n = int(ch)
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


def _classify(d: str, raw: str, ctx: str):
    if len(d) == 10 and d[0] in "6789":
        return "PHONE"
    if len(d) == 11 and d[0] == "0" and d[1] in "6789":
        return "PHONE"
    if len(d) == 12 and d[:2] == "91" and d[2] in "6789":
        return "PHONE"
    if len(d) == 12 and d[0] in "23456789":
        if re.fullmatch(r"\d{4}[ \-]\d{4}[ \-]\d{4}", raw) or re.search(r"aadhaar|aadhar|uidai|\buid\b", ctx):
            return "AADHAAR"
        return None
    if 13 <= len(d) <= 19 and _luhn(d):
        return "CARD"
    return None


def _numeric_spans(text: str):
    spans = []
    for m in CAND_RE.finditer(text):
        s0 = m.start()
        parts = [(g.start() + s0, g.end() + s0) for g in re.finditer(r"\d+", m.group(0))]
        i = 0
        while i < len(parts):
            hit = None
            for j in range(min(len(parts), i + 5) - 1, i - 1, -1):
                a, b = parts[i][0], parts[j][1]
                raw = text[a:b]
                d = re.sub(r"\D", "", raw)
                kind = _classify(d, raw, text[max(0, a - 30):a].lower())
                if kind:
                    if a > 0 and text[a - 1] == "+":
                        a -= 1
                    hit = (a, b, kind, text[a:b], j)
                    break
            if hit:
                spans.append((hit[0], hit[1], "NUM", hit[2], hit[3]))
                i = hit[4] + 1
            else:
                i += 1
    return spans


def _collect(text: str):
    found = []
    for m in EMAIL_RE.finditer(text):
        found.append((m.start(), m.end(), "EMAIL", "EMAIL", m.group(0)))
    for m in UPI_RE.finditer(text):
        found.append((m.start(), m.end(), "UPI", "UPI", m.group(0)))
    for m in PAN_RE.finditer(text):
        found.append((m.start(), m.end(), "PAN", "PAN", m.group(0)))
    for rx in (OTP_RE, OTP_REV_RE):
        for m in rx.finditer(text):
            found.append((m.start(1), m.end(1), "OTP", "OTP", m.group(1)))
    for m in PIN_RE.finditer(text):
        found.append((m.start(1), m.end(1), "PIN", "PIN", m.group(1)))
    for a, b, _, label, val in _numeric_spans(text):
        found.append((a, b, "NUM", label, val))
    return found


def redact(text: str):
    """Returns (masked_text, mapping). mapping = {'[PHONE_1]': '9876543210'}."""
    if not text:
        return text, {}
    found = sorted(_collect(text), key=lambda f: (f[0], PRIORITY[f[2]], -(f[1] - f[0])))
    keep, last_end = [], -1
    for f in found:
        if f[0] >= last_end:
            keep.append(f)
            last_end = f[1]
    mapping, reverse, counters = {}, {}, {}
    out, pos = [], 0
    for start, end, _, label, value in keep:
        key = (label, value)
        if key not in reverse:
            counters[label] = counters.get(label, 0) + 1
            reverse[key] = f"[{label}_{counters[label]}]"
            mapping[reverse[key]] = value
        out.append(text[pos:start])
        out.append(reverse[key])
        pos = end
    out.append(text[pos:])
    return "".join(out), mapping


def restore(text: str, mapping: dict) -> str:
    for placeholder, value in mapping.items():
        text = text.replace(placeholder, value)
    return text


if __name__ == "__main__":
    samples = [
        "Call me on 9876543210 or +91 98765 43210 about the Netflix bill of Rs. 499.",
        "Card 4111 1111 1111 1111 was charged Rs. 1,499 on 2026-11-10.",
        "Aadhaar: 2345 6789 0123 and PAN ABCDE1234F are on file.",
        "Your OTP is 482913. Do not share. Pay to rahul@oksbi or mail help@netflix.com",
        "Invoice INV-2026-0012345 for Spotify Rs. 119, renews 29 Nov 2026. Pincode 560001.",
        "Rs. 499 9876543210",
    ]
    for s in samples:
        m, mp = redact(s)
        print("IN :", s)
        print("OUT:", m)
        print("MAP:", mp, "| restored ok:", restore(m, mp) == s)
        print()