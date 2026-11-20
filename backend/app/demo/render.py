"""HTML pages of the demo documents, to be rendered as JPEG images for field extraction (ADR 0007).

    uv run python -m app.demo.render            # writes data/demo/documents/html/ and manifest.json
    node tools/demo-documents/render.mjs        # turns the HTML pages into JPEG images

Every document of every demo file is drawn as it would look on paper, marked SAMPLE, with the
values of the demo file. A labelled error that changes a value gets its own image of the changed
document, so the extraction and the model-only baseline can be run on every error. Each field that
a document type defines is printed somewhere on it (the blank pages of a passport as a strip of
its visa pages, a translation as a second page, the date of a photograph on the studio's label),
so the model can read every value that the rules need.

Nothing here is a real document: people, numbers, companies and stamps are invented, and every
page says so.
"""

import argparse
import hashlib
import json
import random
from datetime import date
from html import escape
from pathlib import Path

from app.demo.files import DEMO_DIR, DemoDocument, DemoFile, changed, load_all, stored_values
from app.requirements.loader import RequirementData, load_requirement_data

OUT_DIR = DEMO_DIR / "documents"

# Invented details that the rules do not read but a real document would show.
PEOPLE = {
    "employed-nl": {"birth": "1994-06-12", "sex": "M", "id_no": "10000000146"},
    "student-no": {"birth": "2004-09-03", "sex": "M", "id_no": "10000000272"},
}
TR_MONTHS = [
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
]
EN_MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
# Language of a document type when the demo file does not state one.
DEFAULT_LANGUAGE = {
    "application_form": "en",
    "passport": "tr",
    "photo": "tr",
    "civil_registry_extract": "tr",
    "travel_reservation": "en",
    "accommodation": "en",
    "bank_statement": "tr",
    "payslip": "tr",
    "employer_letter": "tr",
    "sgk_employment_declaration": "tr",
    "sgk_service_record": "tr",
    "yok_student_certificate": "tr",
    "travel_insurance": "en",
}

CSS = """
* { box-sizing: border-box; }
body { margin: 0; background: #fff; font-family: "Helvetica Neue", Arial, "Liberation Sans",
  sans-serif; color: #1c1c1c; }
.page { position: relative; width: 1240px; height: 1754px; padding: 90px 100px; overflow: hidden;
  background: #fff; border-bottom: 2px dashed #bbb; }
.page:last-child { border-bottom: 0; }
.mark { position: absolute; top: 640px; left: -60px; width: 1400px; text-align: center;
  font-size: 230px; font-weight: 800; color: rgba(200, 30, 30, .09); transform: rotate(-28deg);
  letter-spacing: 30px; pointer-events: none; }
.foot { position: absolute; bottom: 40px; left: 100px; right: 100px; font-size: 17px;
  color: #a33; border-top: 1px solid #e3c4c4; padding-top: 10px; }
h1 { font-size: 40px; margin: 0 0 6px; } h2 { font-size: 27px; margin: 34px 0 12px; }
.sub { color: #555; font-size: 21px; } p, td, th, li { font-size: 23px; line-height: 1.5; }
table { border-collapse: collapse; width: 100%; } td, th { padding: 9px 12px; text-align: left; }
.grid td { border: 1px solid #c9c9c9; } .grid th { border: 1px solid #c9c9c9; background: #f0f0f0; }
.kv td:first-child { color: #555; width: 38%; } .kv td { border-bottom: 1px solid #e2e2e2; }
.head { display: flex; justify-content: space-between; align-items: flex-start;
  border-bottom: 4px solid var(--c, #234); padding-bottom: 18px; margin-bottom: 26px; }
.logo { font-size: 31px; font-weight: 800; color: var(--c, #234); }
.sig { font-family: "Snell Roundhand", "Brush Script MT", cursive; font-size: 46px; color: #1f3a8a; }
.stamp { display: inline-block; border: 4px solid #7a1f6b; color: #7a1f6b; border-radius: 50%;
  width: 190px; height: 190px; text-align: center; padding-top: 52px; font-weight: 700;
  font-size: 19px; transform: rotate(-12deg); }
.mono { font-family: "OCR B", "Courier New", monospace; letter-spacing: 3px; }
.box { border: 2px solid #999; padding: 18px 22px; border-radius: 6px; }
"""


# Formatting -------------------------------------------------------------------------------------


def d(value: str | None, lang: str) -> str:
    if not value:
        return "—"
    y, m, day = (int(x) for x in value.split("-"))
    if lang == "tr":
        return f"{day:02d}.{m:02d}.{y}"
    return f"{day} {EN_MONTHS[m - 1][:3]} {y}"


def month_name(value: str, lang: str) -> str:
    y, m, _ = (int(x) for x in value.split("-"))
    return f"{TR_MONTHS[m - 1]} {y}" if lang == "tr" else f"{EN_MONTHS[m - 1]} {y}"


def money(value: dict, lang: str) -> str:
    amount = f"{value['amount']:,.0f}"
    if lang == "tr":
        amount = amount.replace(",", ".")
    return f"{value['currency']} {amount}"


def e(text: object) -> str:
    return escape(str(text))


def latin(text: str) -> str:
    """Upper case without Turkish letters, as on bookings and in the passport's MRZ."""
    table = str.maketrans("ÇĞİIÖŞÜçğıiöşü", "CGIIOSUCGIIOSU")
    return text.translate(table).upper()


def seeded(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:12], 16))


# Building blocks --------------------------------------------------------------------------------


def page(body: str, lang: str) -> str:
    foot = (
        "ÖRNEK / SAMPLE — Sentetik demo belgesi; gerçek bir kişiye ya da kuruma ait değildir."
        if lang == "tr"
        else "SAMPLE — Synthetic demo document; it does not belong to a real person or company."
    )
    return f'<section class="page"><div class="mark">SAMPLE</div>{body}<div class="foot">{foot}</div></section>'


def header(org: str, title: str, sub: str, colour: str) -> str:
    return (
        f'<div class="head" style="--c:{colour}"><div><div class="logo">{e(org)}</div>'
        f'<div class="sub">{e(sub)}</div></div><div style="text-align:right"><h1>{e(title)}</h1>'
        "</div></div>"
    )


def kv(rows: list[tuple[str, str]]) -> str:
    return (
        '<table class="kv">'
        + "".join(f"<tr><td>{e(k)}</td><td><b>{v}</b></td></tr>" for k, v in rows)
        + "</table>"
    )


def signature(name: str, signed: bool, label: str) -> str:
    ink = (
        f'<div class="sig">{e(name.split(",")[0])}</div>'
        if signed
        else '<div style="height:64px"></div>'
    )
    return f'<div style="margin-top:40px;width:420px">{ink}<div style="border-top:2px solid #333;font-size:20px;padding-top:6px">{e(label)}</div></div>'


def qr(seed: str, readable: bool) -> str:
    """A QR-like pattern; an unreadable code is smudged and torn as on a bad copy."""
    rng = seeded(seed)
    n, cell = 29, 7
    cells = []
    finders = ((0, 0), (n - 7, 0), (0, n - 7))
    for y in range(n):
        for x in range(n):
            origin = next(
                ((fx, fy) for fx, fy in finders if fx <= x < fx + 7 and fy <= y < fy + 7), None
            )
            if origin:
                on = max(abs(x - origin[0] - 3), abs(y - origin[1] - 3)) != 2
            else:
                on = rng.random() < 0.5
            if on:
                cells.append(
                    f'<rect x="{x * cell}" y="{y * cell}" width="{cell}" height="{cell}"/>'
                )
    size = n * cell
    damage = (
        f'<ellipse cx="{size * 0.55}" cy="{size * 0.5}" rx="{size * 0.42}" ry="{size * 0.3}" fill="#6b5b3e" opacity=".55" filter="url(#b)"/>'
        f'<path d="M0,{size * 0.62} L{size},{size * 0.38} L{size},{size * 0.5} L0,{size * 0.74} z" fill="#fff"/>'
        if not readable
        else ""
    )
    return (
        f'<svg width="{size + 20}" height="{size + 20}" viewBox="-10 -10 {size + 20} {size + 20}">'
        '<defs><filter id="b"><feGaussianBlur stdDeviation="6"/></filter></defs>'
        f'<rect x="-10" y="-10" width="{size + 20}" height="{size + 20}" fill="#fff"/><g fill="#111">{"".join(cells)}</g>{damage}</svg>'
    )


def mrz_check(text: str) -> str:
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(text):
        value = int(ch) if ch.isdigit() else (ord(ch) - 55 if ch.isalpha() else 0)
        total += value * weights[i % 3]
    return str(total % 10)


def mrz(
    surname: str, given: str, number: str, birth: str, sex: str, expiry: str
) -> tuple[str, str]:
    line1 = f"P<TUR{latin(surname)}<<{latin(given).replace(' ', '<')}".ljust(44, "<")[:44]
    num = number.replace(" ", "").ljust(9, "<")[:9]
    b, x = birth.replace("-", "")[2:], expiry.replace("-", "")[2:]
    personal = "<" * 14
    composite = (
        num + mrz_check(num) + b + mrz_check(b) + x + mrz_check(x) + personal + mrz_check(personal)
    )
    line2 = f"{num}{mrz_check(num)}TUR{b}{mrz_check(b)}{sex}{x}{mrz_check(x)}{personal}{mrz_check(personal)}{mrz_check(composite)}"
    return line1, line2


def split_name(full: str) -> tuple[str, str]:
    parts = full.split()
    return parts[-1], " ".join(parts[:-1])


# Documents ---------------------------------------------------------------------------------------


def passport(v: dict, who: dict, seed: str) -> str:
    surname, given = split_name(v["full_name"])
    l1, l2 = mrz(surname, given, v["passport_number"], who["birth"], who["sex"], v["expiry_date"])
    photo = (
        '<svg width="230" height="290" viewBox="0 0 230 290"><rect width="230" height="290" fill="#dfe6ee"/>'
        '<circle cx="115" cy="110" r="58" fill="#9aa7b4"/><path d="M20,290 C30,200 200,200 210,290 z" fill="#9aa7b4"/>'
        '<text x="115" y="275" font-size="26" text-anchor="middle" fill="#a33" font-weight="700">SAMPLE</text></svg>'
    )
    rows = [
        ("Soyadı / Surname", e(latin(surname))),
        ("Adı / Given names", e(latin(given))),
        ("Uyruğu / Nationality", "TÜRKİYE CUMHURİYETİ / TUR"),
        ("Doğum tarihi / Date of birth", d(who["birth"], "tr")),
        ("Cinsiyeti / Sex", who["sex"]),
        ("Pasaport No / Passport No", e(v["passport_number"])),
        ("Veriliş tarihi / Date of issue", d(v["issue_date"], "tr")),
        ("Geçerlilik tarihi / Date of expiry", d(v["expiry_date"], "tr")),
        ("Veren makam / Authority", "T.C. İÇİŞLERİ BAKANLIĞI"),
    ]
    sig = signature(v["full_name"], bool(v.get("signed")), "Hamilin imzası / Holder's signature")
    pages = 24
    used = pages - int(v.get("blank_pages", pages))
    rng = seeded(seed, "stamps")
    thumbs = []
    for i in range(pages):
        stamp = ""
        if i < used:
            colour = rng.choice(["#7a1f6b", "#1f5a7a", "#2f6b1f", "#8a4a12"])
            stamp = (
                f'<div style="position:absolute;left:{rng.randint(6, 40)}px;top:{rng.randint(8, 70)}px;'
                f"width:58px;height:44px;border:3px solid {colour};border-radius:{rng.choice(['50%', '4px'])};"
                f'transform:rotate({rng.randint(-25, 25)}deg)"></div>'
            )
        thumbs.append(
            f'<div style="position:relative;width:118px;height:150px;border:1px solid #9aa;background:#f7f4ec">'
            f'<span style="position:absolute;bottom:4px;right:6px;font-size:15px;color:#777">{i + 9}</span>{stamp}</div>'
        )
    body = (
        header(
            "TÜRKİYE CUMHURİYETİ",
            "PASAPORT / PASSPORT",
            "Pasaport veri sayfası / Data page",
            "#7a1020",
        )
        + f'<div style="display:flex;gap:40px">{photo}<div style="flex:1">{kv(rows)}</div></div>{sig}'
        + f'<div class="mono" style="margin-top:36px;font-size:30px;background:#f3f3f3;padding:16px">{e(l1)}<br>{e(l2)}</div>'
        + f"<h2>Vize sayfaları / Visa pages (taranmış / scanned, {pages} sayfa / pages)</h2>"
        + f'<div style="display:grid;grid-template-columns:repeat(8,118px);gap:12px">{"".join(thumbs)}</div>'
    )
    return page(body, "tr")


def photo(v: dict, who: dict, seed: str) -> str:
    body = (
        header("FOTO ÖRNEK", "Biyometrik fotoğraf", "Fotoğraf stüdyosu / Photo studio", "#334")
        + '<div style="display:flex;gap:60px;margin-top:60px"><svg width="420" height="540" viewBox="0 0 230 290">'
        '<rect width="230" height="290" fill="#eef1f4"/><circle cx="115" cy="110" r="58" fill="#8b98a6"/>'
        '<path d="M20,290 C30,200 200,200 210,290 z" fill="#8b98a6"/>'
        '<text x="115" y="275" font-size="24" text-anchor="middle" fill="#a33" font-weight="700">SAMPLE</text></svg>'
        f'<div class="box" style="align-self:flex-start;width:520px">{kv([("Ölçü / Size", "35 × 45 mm"), ("Çekim tarihi / Date taken", d(v["taken_on"], "tr")), ("Arka plan / Background", "Beyaz / White")])}</div></div>'
    )
    return page(body, "tr")


def application_form(v: dict, who: dict, seed: str, name: str) -> str:
    rows = [
        ("1. Surname", e(latin(split_name(name)[0]))),
        ("2. First name(s)", e(latin(split_name(name)[1]))),
        ("4. Date of birth", d(who["birth"], "en")),
        ("13. Purpose of journey", "Tourism"),
        ("Type of visa", "Uniform visa (C), single entry"),
    ]
    body = (
        header(
            "Schengen", "Application for Schengen Visa", "Harmonised application form", "#1f3a8a"
        )
        + kv(rows)
        + "<p style='margin-top:30px'>I am aware that the visa fee is not refunded if the visa is refused. "
        "I declare that to the best of my knowledge all particulars supplied by me are correct and complete.</p>"
        + signature(name, bool(v.get("signed")), "Place and date, signature")
    )
    return page(body, "en")


def registry(v: dict, who: dict, seed: str) -> str:
    surname, given = split_name(v["full_name"])
    rows = [
        ("T.C. Kimlik No", who["id_no"]),
        ("Adı", e(given)),
        ("Soyadı", e(surname)),
        ("Baba adı", "Ali"),
        ("Ana adı", "Ayşe"),
        ("Doğum yeri / tarihi", f"İstanbul / {d(who['birth'], 'tr')}"),
        ("Medeni hali", "Bekâr"),
        ("Nüfusa kayıtlı olduğu il / ilçe", "İstanbul / Kadıköy"),
    ]
    return page(
        header(
            "T.C. İÇİŞLERİ BAKANLIĞI",
            "TAM VUKUATLI NÜFUS KAYIT ÖRNEĞİ",
            "Nüfus ve Vatandaşlık İşleri Genel Müdürlüğü",
            "#7a1020",
        )
        + kv(rows)
        + f"<p style='margin-top:30px'>Belge düzenlenme tarihi: <b>{d(v['issue_date'], 'tr')}</b></p>"
        + f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:30px"><span>Doğrulama kodu: ÖRNEK-{seed[-6:].upper()}</span>{qr(seed, True)}</div>',
        "tr",
    )


def reservation(v: dict, who: dict, seed: str, dest: str) -> str:
    rng = seeded(seed)
    pnr = "".join(rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ23456789") for _ in range(6))
    city = {"NL": ("IST", "AMS", "Amsterdam"), "NO": ("IST", "OSL", "Oslo")}[dest]
    legs = (
        '<table class="grid"><tr><th>Flight</th><th>From</th><th>To</th><th>Date</th><th>Class</th></tr>'
        f"<tr><td>SX 1201</td><td>Istanbul ({city[0]})</td><td>{city[2]} ({city[1]})</td><td>{d(v['departure_date'], 'en')}</td><td>Economy</td></tr>"
        f"<tr><td>SX 1202</td><td>{city[2]} ({city[1]})</td><td>Istanbul ({city[0]})</td><td>{d(v['return_date'], 'en')}</td><td>Economy</td></tr></table>"
    )
    return page(
        header("SampleAir", "Flight reservation", "Itinerary receipt — not a ticket", "#0d6e6e")
        + kv(
            [
                ("Booking reference", pnr),
                ("Passenger", f"{e(v['passenger_name'])} MR"),
                ("Status", "Confirmed"),
            ]
        )
        + "<h2>Itinerary</h2>"
        + legs,
        "en",
    )


def accommodation(v: dict, who: dict, seed: str, dest: str) -> str:
    hotel = {"NL": "Hotel Sample Canal, Amsterdam", "NO": "Sample Fjord Hostel, Oslo"}[dest]
    nights = (date.fromisoformat(v["check_out"]) - date.fromisoformat(v["check_in"])).days
    return page(
        header("SampleStay", "Booking confirmation", hotel, "#8a4a12")
        + kv(
            [
                ("Guest name", e(v["guest_name"])),
                ("Check-in", d(v["check_in"], "en")),
                ("Check-out", d(v["check_out"], "en")),
                ("Nights", str(nights)),
                ("Room", "Single room, breakfast included"),
                ("Booking number", f"SS-{seeded(seed).randint(100000, 999999)}"),
            ]
        )
        + "<p style='margin-top:30px'>The booking is confirmed and paid in full.</p>",
        "en",
    )


def bank(v: dict, who: dict, seed: str) -> str:
    rng = seeded(seed)
    start, end = date.fromisoformat(v["period_start"]), date.fromisoformat(v["period_end"])
    rows, balance, day = [], 48250.0, start
    while day <= end and len(rows) < 14:
        amount = rng.choice([-1250.5, -420.0, -2300.0, -185.9, 42000.0 if day.day > 24 else -640.0])
        balance += amount
        rows.append(
            f"<tr><td>{d(day.isoformat(), 'tr')}</td><td>{'MAAŞ ÖDEMESİ' if amount > 0 else rng.choice(['MARKET', 'FATURA', 'KART ÖDEMESİ', 'KİRA'])}</td>"
            f"<td style='text-align:right'>{amount:,.2f}</td><td style='text-align:right'>{balance:,.2f}</td></tr>"
        )
        day = date.fromordinal(day.toordinal() + max(1, (end - start).days // 13))
    table = (
        '<table class="grid"><tr><th>Tarih</th><th>Açıklama</th><th>Tutar (TRY)</th><th>Bakiye (TRY)</th></tr>'
        + "".join(rows)
        + "</table>"
    )
    return page(
        header("ÖRNEK BANK A.Ş.", "HESAP DÖKÜMÜ", "Account statement", "#14532d")
        + kv(
            [
                ("Hesap sahibi", e(v["holder_name"])),
                ("IBAN", "TR00 0000 0000 0000 0000 0000 00"),
                ("Dönem", f"{d(v['period_start'], 'tr')} – {d(v['period_end'], 'tr')}"),
                ("Düzenlenme tarihi", d(v["issue_date"], "tr")),
            ]
        )
        + "<h2>Hareketler</h2>"
        + table
        + '<div style="margin-top:30px;text-align:right"><span class="stamp">ÖRNEK BANK<br>ŞUBE<br>KAŞE</span></div>',
        "tr",
    )


def payslip(v: dict, who: dict, seed: str, name: str) -> str:
    return page(
        header("ÖRNEK MUHASEBE A.Ş.", "ÜCRET BORDROSU", "Salary slip", "#1f3a8a")
        + kv(
            [
                ("Personel", e(v["employee_name"])),
                ("Dönem", month_name(v["pay_month"], "tr")),
                ("Ödeme tarihi", d(v["pay_month"], "tr")),
                ("Düzenlenme tarihi", d(v["issue_date"], "tr")),
            ]
        )
        + '<h2>Kazançlar ve kesintiler</h2><table class="grid"><tr><th>Kalem</th><th style="text-align:right">TRY</th></tr>'
        "<tr><td>Brüt ücret</td><td style='text-align:right'>58.000,00</td></tr>"
        "<tr><td>SGK işçi payı</td><td style='text-align:right'>−8.120,00</td></tr>"
        "<tr><td>Gelir vergisi</td><td style='text-align:right'>−7.880,00</td></tr>"
        "<tr><td><b>Net ödenen</b></td><td style='text-align:right'><b>42.000,00</b></td></tr></table>",
        "tr",
    )


def employer_letter(v: dict, who: dict, seed: str, dest: str) -> str:
    to = (
        {"NL": "Hollanda Krallığı Başkonsolosluğu'na", "NO": "Norveç Krallığı Büyükelçiliği'ne"}[
            dest
        ]
        if v.get("addressed_to_consulate")
        else "İlgili makama"
    )
    paid = "ücretli" if v.get("leave_paid") else "ücretsiz"
    text = (
        f"<p>Şirketimiz çalışanı <b>{e(v['employee_name'])}</b> (pasaport no: <b>{e(v['passport_number'])}</b>), "
        f"<b>{d(v['employment_start'], 'tr')}</b> tarihinden bu yana şirketimizde <b>{e(v['job_title'])}</b> olarak "
        "tam zamanlı çalışmaktadır.</p>"
        f"<p>Kendisine <b>{d(v['leave_start'], 'tr')}</b> – <b>{d(v['leave_end'], 'tr')}</b> tarihleri arasında "
        f"<b>{paid}</b> yıllık izin verilmiştir. İzin dönüşünde görevine devam edecektir.</p>"
        "<p>Seyahatine ilişkin bütün masraflar kendisi tarafından karşılanacaktır.</p>"
    )
    return page(
        header("ÖRNEK MUHASEBE A.Ş.", "", e(v["employer_contact"]), "#1f3a8a")
        + f"<p style='text-align:right'>{d(v['issue_date'], 'tr')}</p><p><b>{e(to)}</b></p>"
        + text
        + signature(v["signatory_name"], True, e(v["signatory_name"]))
        + '<div style="margin-top:20px"><span class="stamp">ÖRNEK<br>MUHASEBE<br>A.Ş.</span></div>',
        "tr",
    )


def sgk(v: dict, who: dict, seed: str, kind: str) -> str:
    title = {
        "sgk_employment_declaration": "SİGORTALI İŞE GİRİŞ BİLDİRGESİ",
        "sgk_service_record": "SİGORTALI HİZMET DÖKÜMÜ",
    }[kind]
    rows = [
        ("T.C. Kimlik No", who["id_no"]),
        ("Adı Soyadı", e(v["full_name"])),
        ("İşyeri", "Örnek Muhasebe A.Ş."),
        ("Belge tarihi", d(v["issue_date"], "tr")),
    ]
    extra = ""
    if kind == "sgk_service_record":
        extra = (
            '<h2>Hizmet dökümü</h2><table class="grid"><tr><th>Yıl/Ay</th><th>Gün</th><th>Kazanç (TRY)</th></tr>'
            + "".join(
                f"<tr><td>{y}/{m:02d}</td><td>30</td><td>58.000,00</td></tr>"
                for y, m in ((2026, 10), (2026, 11), (2026, 12), (2027, 1))
            )
            + "</table>"
        )
    return page(
        header("T.C. SOSYAL GÜVENLİK KURUMU", title, "e-Devlet çıktısı", "#7a1020")
        + kv(rows)
        + extra
        + f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:40px"><span>Barkod doğrulama: turkiye.gov.tr (ÖRNEK)</span>{qr(seed, bool(v.get("qr_code_readable")))}</div>',
        "tr",
    )


def yok(v: dict, who: dict, seed: str) -> str:
    return page(
        header("T.C. YÜKSEKÖĞRETİM KURULU", "ÖĞRENCİ BELGESİ", "e-Devlet çıktısı", "#7a1020")
        + kv(
            [
                ("T.C. Kimlik No", who["id_no"]),
                ("Adı Soyadı", e(v["full_name"])),
                ("Üniversite", "Örnek Üniversitesi"),
                ("Fakülte / Bölüm", "Mühendislik Fakültesi / Bilgisayar Mühendisliği"),
                ("Sınıf", "3"),
                ("Öğrencilik durumu", "Aktif"),
                ("Belge tarihi", d(v["issue_date"], "tr")),
            ]
        )
        + f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:40px"><span>Barkod doğrulama: turkiye.gov.tr (ÖRNEK)</span>{qr(seed, bool(v.get("qr_code_readable")))}</div>',
        "tr",
    )


def insurance(v: dict, who: dict, seed: str) -> str:
    area = "All Schengen states" if v.get("covers_all_schengen") else "Norway only"
    return page(
        header(
            "Sample Sigorta A.Ş.", "Travel Health Insurance", "Certificate of insurance", "#0d6e6e"
        )
        + kv(
            [
                ("Insured person", e(v["insured_name"])),
                ("Policy number", f"SG-{seeded(seed).randint(1000000, 9999999)}"),
                (
                    "Period of cover",
                    f"{d(v['coverage_start'], 'en')} – {d(v['coverage_end'], 'en')}",
                ),
                ("Medical expenses limit", money(v["coverage_amount"], "en")),
                ("Territorial validity", area),
                ("Repatriation", "Included" if v.get("covers_repatriation") else "Not included"),
            ]
        )
        + "<p style='margin-top:30px'>This certificate is valid for the visa application of the insured person.</p>",
        "en",
    )


def translation(original_title: str, rows: list[tuple[str, str]], issue: str) -> str:
    return page(
        header(
            "Sample Translation Office",
            "Sworn translation",
            "Translation from Turkish into English",
            "#444",
        )
        + f"<p><b>Translation of:</b> {e(original_title)}</p>"
        + kv(rows)
        + f"<p style='margin-top:30px'>I certify that this is a true and complete translation of the attached document.</p>"
        f"<p>Sworn translator: Sample Translator — {d(issue, 'en')}</p>",
        "en",
    )


def render_document(demo: DemoFile, doc: DemoDocument, data: RequirementData) -> tuple[str, str]:
    """The HTML of one document and its language."""
    v = {
        k: (x.isoformat() if isinstance(x, date) else x)
        for k, x in stored_values(data, doc).items()
    }
    who = PEOPLE[demo.id]
    seed = f"{demo.id}/{doc.id}"
    name = next(dd.values["full_name"] for dd in demo.documents if dd.type == "passport")
    lang = v.get("language") or DEFAULT_LANGUAGE[doc.type]
    t = doc.type
    if t == "passport":
        pages = passport(v, who, seed)
    elif t == "photo":
        pages = photo(v, who, seed)
    elif t == "application_form":
        pages = application_form(v, who, seed, name)
    elif t == "civil_registry_extract":
        pages = registry(v, who, seed)
    elif t == "travel_reservation":
        pages = reservation(v, who, seed, demo.destination)
    elif t == "accommodation":
        pages = accommodation(v, who, seed, demo.destination)
    elif t == "bank_statement":
        pages = bank(v, who, seed)
    elif t == "payslip":
        pages = payslip(v, who, seed, name)
    elif t == "employer_letter":
        pages = employer_letter(v, who, seed, demo.destination)
    elif t in ("sgk_employment_declaration", "sgk_service_record"):
        pages = sgk(v, who, seed, t)
    elif t == "yok_student_certificate":
        pages = yok(v, who, seed)
    elif t == "travel_insurance":
        pages = insurance(v, who, seed)
    else:
        raise ValueError(f"no template for {t}")
    if v.get("translation_language") == "en":
        title = data.catalog.document(t).title.en
        rows = [
            (
                k.replace("_", " ").capitalize(),
                e(d(x, "en") if isinstance(x, str) and x[:4].isdigit() and len(x) == 10 else x),
            )
            for k, x in v.items()
            if k not in ("language", "translation_language", "qr_code_readable")
        ]
        pages += translation(title, rows, v.get("issue_date") or v.get("period_end"))
    html = f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{pages}</body></html>'
    return html, lang


def render_all(out: Path = OUT_DIR) -> list[dict]:
    """Write one HTML file per document and per value-changing error, and the manifest."""
    data = load_requirement_data()
    html_dir = out / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for demo in load_all():
        variants: list[tuple[str | None, list]] = [(None, [])]
        variants += [(err.id, [err.change]) for err in demo.errors if err.change.set is not None]
        for error_id, changes in variants:
            target = changes[0].set.document if changes else None
            for doc in changed(demo, changes):
                if error_id and doc.id != target:
                    continue
                name = f"{demo.id}--{doc.id}" + (f"--{error_id}" if error_id else "")
                html, lang = render_document(demo, doc, data)
                (html_dir / f"{name}.html").write_text(html, encoding="utf-8")
                manifest.append(
                    {
                        "file": demo.id,
                        "document": doc.id,
                        "type": doc.type,
                        "error": error_id,
                        "image": f"{name}.jpg",
                        "language": lang,
                        "values": {
                            k: (x.isoformat() if isinstance(x, date) else x)
                            for k, x in stored_values(data, doc).items()
                        },
                    }
                )
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    manifest = render_all(args.out)
    print(f"{len(manifest)} document pages written to {args.out / 'html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
