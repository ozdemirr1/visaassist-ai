"""A one-page PDF that says SAMPLE, for the documents of the demo files.

The file only gives the demo something to upload and to open; nothing reads its content, since
the field values are entered separately (FR-08). It is written by hand (one page, Helvetica, no
library) and lists the values the demo enters, so what the page shows matches the form.
"""

# Helvetica in the PDF's standard encoding covers Latin-1; the Turkish letters outside it are
# written without their marks on the page (the entered values keep them).
_PLAIN = str.maketrans({"ğ": "g", "Ğ": "G", "ş": "s", "Ş": "S", "ı": "i", "İ": "I", "–": "-"})


def _text(value: str) -> bytes:
    raw = value.translate(_PLAIN).encode("latin-1", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def sample_pdf(title: str, lines: list[str]) -> bytes:
    """A valid one-page A4 PDF with a large SAMPLE mark, a title and the given lines."""
    content = [b"BT /F1 64 Tf 0.85 g 1 0 0 1 150 420 Tm (SAMPLE) Tj ET"]
    content.append(b"BT /F1 16 Tf 0 g 1 0 0 1 56 780 Tm (" + _text(title) + b") Tj ET")
    content.append(
        b"BT /F1 9 Tf 0.4 g 1 0 0 1 56 760 Tm "
        b"(Synthetic demo document - not a real document, no real person.) Tj ET"
    )
    y = 720
    for line in lines[:40]:
        content.append(b"BT /F1 11 Tf 0 g 1 0 0 1 56 %d Tm (" % y + _text(line) + b") Tj ET")
        y -= 16
    stream = b"\n".join(content)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n% SAMPLE\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)
