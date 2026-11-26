"""Creates 3 small text PDFs in bills/ with no extra libraries."""
import os

BILLS = {
    "netflix_bill.pdf": [
        "Netflix India - Tax Invoice",
        "Date: 2026-10-05",
        "Your Netflix plan renewed. Amount charged: Rs. 499.",
        "Next billing date: 5 Nov 2026.",
    ],
    "electricity_bill.pdf": [
        "BESCOM Electricity Bill",
        "Date: 2026-11-18",
        "Your electricity bill is due. Amount due: Rs. 1,240.",
        "Please pay by 5 Dec 2026.",
    ],
    "gym_receipt.pdf": [
        "FitZone Gym - Membership Receipt",
        "Date: 2026-11-02",
        "Payment received for your monthly subscription: Rs. 899.",
        "Your membership renews on 2 Dec 2026.",
    ],
}


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(lines: list[str]) -> bytes:
    stream = "BT /F1 14 Tf 60 780 Td 22 TL\n" + "\n".join(f"({esc(l)}) Tj T*" for l in lines) + "\nET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


os.makedirs("bills", exist_ok=True)
for name, lines in BILLS.items():
    with open(os.path.join("bills", name), "wb") as f:
        f.write(make_pdf(lines))
    print("created bills/" + name)