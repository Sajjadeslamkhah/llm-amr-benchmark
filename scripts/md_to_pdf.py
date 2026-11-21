#!/usr/bin/env python3
"""Render a Markdown document to PDF, with Turkish characters intact.

    python scripts/md_to_pdf.py docs/DEGERLENDIRME_TR.md results/TALIMAT.pdf

Written for the adjudication instructions, which go to a reader who should not
have to open a Markdown file. Handles what those documents use: headings, bullet
lists, numbered lists, tables, paragraphs, inline code and bold.

The font matters: reportlab's built-in faces cover Latin-1, which has no ş, ğ or
ı, so Turkish text would come out with gaps. A Unicode TTF is registered instead,
looked for in the usual macOS and Linux places, and the script stops with a clear
message rather than producing a document with missing letters.
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (ListFlowable, ListItem, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

# Regular and bold, in order of preference. macOS first, then Linux.
FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf",) * 2,
    ("/Library/Fonts/Arial Unicode.ttf",) * 2,
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]
MONO_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def register_fonts() -> tuple[str, str, str]:
    base = bold = None
    for reg, bld in FONT_CANDIDATES:
        if Path(reg).exists():
            pdfmetrics.registerFont(TTFont("Body", reg))
            base = "Body"
            if Path(bld).exists() and bld != reg:
                pdfmetrics.registerFont(TTFont("Body-Bold", bld))
                bold = "Body-Bold"
            else:
                bold = "Body"
            break
    if not base:
        raise SystemExit(
            "No Unicode TTF found. reportlab's built-in fonts have no Turkish\n"
            "characters, so the PDF would be missing letters rather than merely\n"
            "looking different. Looked in:\n  " +
            "\n  ".join(r for r, _ in FONT_CANDIDATES))
    mono = base
    for m in MONO_CANDIDATES:
        if Path(m).exists():
            try:
                pdfmetrics.registerFont(TTFont("Body-Mono", m))
                mono = "Body-Mono"
                break
            except Exception:
                continue        # a .ttc collection reportlab cannot open; try the next
    return base, bold, mono


def inline(text: str, bold_font: str, mono_font: str) -> str:
    """Markdown bold, inline code and emphasis to reportlab markup."""
    t = html.escape(text)
    t = re.sub(r"`([^`]+)`", rf'<font face="{mono_font}" size="9">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", rf'<font face="{bold_font}">\1</font>', t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    return t


def build(md: str, out: Path, title: str) -> None:
    base, bold, mono = register_fonts()
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontName=base, fontSize=10.5,
                          leading=15, alignment=TA_LEFT, spaceAfter=6)
    h = {
        1: ParagraphStyle("h1", parent=body, fontName=bold, fontSize=17, leading=22,
                          spaceBefore=4, spaceAfter=10),
        2: ParagraphStyle("h2", parent=body, fontName=bold, fontSize=13, leading=18,
                          spaceBefore=14, spaceAfter=6),
        3: ParagraphStyle("h3", parent=body, fontName=bold, fontSize=11.5, leading=16,
                          spaceBefore=10, spaceAfter=4),
    }
    cell = ParagraphStyle("cell", parent=body, fontSize=9.5, leading=13, spaceAfter=0)

    flow = []
    lines = md.splitlines()
    i = 0
    bullets: list[str] = []
    numbered: list[str] = []

    def flush_lists():
        nonlocal bullets, numbered
        for items, kind, start in ((bullets, "bullet", None), (numbered, "1", 1)):
            if items:
                flow.append(ListFlowable(
                    [ListItem(Paragraph(inline(x, bold, mono), body), leftIndent=14)
                     for x in items],
                    bulletType=kind, start=start, leftIndent=12,
                    bulletFontName=base, bulletFontSize=10))
                flow.append(Spacer(1, 4))
        bullets, numbered = [], []

    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            flush_lists()
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            flush_lists()
            flow.append(Paragraph(inline(m.group(2), bold, mono), h[len(m.group(1))]))
            i += 1
            continue
        if line.lstrip().startswith(("- ", "* ")):
            bullets.append(line.lstrip()[2:])
            i += 1
            continue
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            numbered.append(m.group(1))
            i += 1
            continue
        if line.lstrip().startswith("|"):
            flush_lists()
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                raw = lines[i].strip().strip("|")
                if not re.fullmatch(r"[\s|:\-]+", raw):
                    rows.append([c.strip() for c in raw.split("|")])
                i += 1
            if rows:
                data = [[Paragraph(inline(c, bold, mono), cell) for c in r] for r in rows]
                t = Table(data, hAlign="LEFT", repeatRows=1)
                t.setStyle(TableStyle([
                    ("FONTNAME", (0, 0), (-1, -1), base),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                flow.append(t)
                flow.append(Spacer(1, 8))
            continue
        # a paragraph: join its continuation lines
        para = [line.strip()]
        i += 1
        while (i < len(lines) and lines[i].strip()
               and not re.match(r"^\s*(#{1,3}\s|[-*]\s|\d+\.\s|\|)", lines[i])):
            para.append(lines[i].strip())
            i += 1
        flush_lists()
        flow.append(Paragraph(inline(" ".join(para), bold, mono), body))

    flush_lists()
    out.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(out), pagesize=A4, title=title,
                      leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=18 * mm, bottomMargin=18 * mm).build(flow)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("out")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    src = Path(a.source)
    md = src.read_text(encoding="utf-8")
    title = a.title or next((l.lstrip("# ").strip() for l in md.splitlines()
                             if l.startswith("# ")), src.stem)
    build(md, Path(a.out), title)
    print(f"{a.out}  ({Path(a.out).stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
