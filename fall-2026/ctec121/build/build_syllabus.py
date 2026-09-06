#!/usr/bin/env python3
"""
Rebuild every CTEC 121 syllabus output from its source, then verify it.

Run this in a Claude session (it needs the cloud container's chromium, pandoc,
pikepdf and pypdf — not tools that live on a Mac). Point it at the folder that
holds the sources:

    python3 build_syllabus.py "/path/to/CTEC 121 Syllabus"

SOURCES (hand-edited)          OUTPUTS (never hand-edit; regenerate)
  CTEC_121_Syllabus_...md        CTEC_121_Syllabus_Fall_2026.docx
  index.html                     CTEC_121_Syllabus_Fall_2026.pdf
  CTEC121_Day_One_source.html    CTEC121_Day_One.pdf

Every check below exists because that exact thing broke once. If a check
fails, do not "fix" it by loosening the check.
"""

import io, os, re, sys, shutil, zipfile, subprocess, tempfile, warnings
from datetime import datetime
from zoneinfo import ZoneInfo
warnings.filterwarnings("ignore")

CHROMIUM = "/opt/pw-browsers/chromium"
MD   = "CTEC_121_Syllabus_Fall_2026.md"
SITE = "index.html"                       # renamed from CTEC_121_Syllabus_Fall_2026.html
HAND = "CTEC121_Day_One_source.html"
OUT_DOCX = "CTEC_121_Syllabus_Fall_2026.docx"
OUT_PDF  = "CTEC_121_Syllabus_Fall_2026.pdf"
OUT_HAND = "CTEC121_Day_One.pdf"

MIN_PT_PRINT = 9.0     # smallest type allowed in anything that prints
MIN_PX_SCREEN = 12.0   # smallest type allowed on the web page

problems, notes = [], []
def check(ok, msg):
    (notes if ok else problems).append(("PASS " if ok else "FAIL ") + msg)


# ---------------------------------------------------------------- Word .docx
def build_docx(folder):
    src = io.open(os.path.join(folder, MD), encoding="utf-8").read()

    # the web page's own contents list means nothing in Word
    i = src.index("## Table of contents"); j = src.index("---", i)
    s = src[:i] + src[j + 4:]
    # in-page anchors don't resolve in Word — keep the words, drop the link
    s = re.sub(r"\[([^\]]+)\]\(#[^)]+\)", r"\1", s)
    # the YAML title below renders the H1; keeping both duplicates it
    s = re.sub(r"^# .*\n\n", "", s, count=1)
    # ...and the Word copy has no contents list to point at
    s = s.replace("Use the table of contents, and ask me",
                  "Jump to the section you need, and ask me")
    # markdown joins consecutive lines into one paragraph; the masthead needs breaks
    for line in re.findall(r"^\*\*[^\n]+\*\*$", s, re.M)[:2]:
        s = s.replace(line + "\n", line + "  \n", 1)

    # written from Python: passing these via pandoc's --metadata mangles em dashes
    yaml = ('---\n'
            'title: "CTEC 121 — Introduction to Programming and Problem Solving"\n'
            'author: "Bruce Elgort · Clark College"\n'
            'subject: "Course syllabus · Fall 2026"\n'
            'keywords: [CTEC 121, Clark College, Fall 2026, Python, syllabus]\n'
            'lang: en-US\n---\n\n')

    tmp = tempfile.mkdtemp()
    md_path = os.path.join(tmp, "word.md")
    io.open(md_path, "w", encoding="utf-8").write(yaml + s)

    # NO --toc: a TOC field makes Word open with "contains fields that may
    # refer to other files". Headings are real Heading 1/2, so the Navigation
    # Pane works and References > Table of Contents builds one on demand.
    base = os.path.join(tmp, "base.docx")
    subprocess.run(["pandoc", md_path, "--shift-heading-level-by=-1",
                    "--resource-path", folder, "-o", base], check=True)

    un = os.path.join(tmp, "x"); os.makedirs(un, exist_ok=True)
    with zipfile.ZipFile(base) as z: z.extractall(un)
    doc = os.path.join(un, "word", "document.xml")
    d = io.open(doc, encoding="utf-8").read()
    # pandoc leaves an empty sectPr, so page size falls back to the reader's locale (A4 abroad)
    if "<w:sectPr />" not in d:
        raise SystemExit("pandoc output changed: no empty <w:sectPr /> to replace")
    d = d.replace("<w:sectPr />",
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>')
    io.open(doc, "w", encoding="utf-8").write(d)
    # NOTE: never add updateFields to word/settings.xml — element order is schema-enforced.

    # Bruce: nothing in the Word doc is centered. Pandoc's default reference doc
    # centers Title/Subtitle/Author/Date, which reads wrong against the
    # left-aligned masthead in the web page and the handout.
    sty = os.path.join(un, "word", "styles.xml")
    t = io.open(sty, encoding="utf-8").read()
    t = re.sub(r'<w:jc w:val="center"\s*/>', '<w:jc w:val="left"/>', t)
    io.open(sty, "w", encoding="utf-8").write(t)

    out = os.path.join(folder, OUT_DOCX)
    if os.path.exists(out): os.remove(out)
    subprocess.run(["zip", "-Xrq", out, "."], cwd=un, check=True)

    x = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
    check(x.count("<w:fldChar") == 0, "Word doc is field-free (no scary dialog on open)")
    check("w:dirty" not in x, "Word doc has no dirty field flags")
    check('w:w="12240"' in x, "Word doc is US Letter, not locale-default A4")
    check("Heading1" in x, "Word doc uses real Heading styles (Navigation Pane works)")
    check("table of contents" not in x.lower(), "Word doc has no stale contents-list reference")
    sx = zipfile.ZipFile(out).read("word/styles.xml").decode("utf-8")
    check('w:jc w:val="center"' not in sx, "Word doc left-aligns everything (no centered title block)")
    media = [n for n in zipfile.ZipFile(out).namelist()
             if n.startswith("word/media/") and not n.endswith("/")]
    check(len(media) == 0, "Word doc embeds no images (QR removed Sept 2026; found %d)" % len(media))
    shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------- the PDFs
def render_pdf(html_path, pdf_path):
    # The CLI fires beforeprint (link URLs, open <details>) AND emits a tagged
    # PDF. Playwright's page.pdf() does neither — do not swap it in.
    subprocess.run([CHROMIUM, "--headless", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", "--print-to-pdf=" + pdf_path, html_path],
                   check=True, capture_output=True)

def stamp(pdf_path, title, desc):
    import pikepdf
    pdf = pikepdf.open(pdf_path, allow_overwriting_input=True)
    with pdf.open_metadata(set_pikepdf_as_editor=False) as m:
        m["dc:title"] = title
        m["dc:description"] = desc
        m["dc:creator"] = ["Bruce Elgort"]
        m["dc:language"] = ["en-US"]
        m["pdf:Keywords"] = "CTEC 121, Clark College, Fall 2026, Python, syllabus"
    pdf.docinfo["/Title"] = title
    pdf.docinfo["/Author"] = "Bruce Elgort"
    pdf.docinfo["/Subject"] = "Clark College · Fall 2026"
    pdf.Root.ViewerPreferences = pikepdf.Dictionary(
        Type=pikepdf.Name.ViewerPreferences, DisplayDocTitle=True)
    tmp = pdf_path + ".tmp"
    pdf.save(tmp, linearize=True); pdf.close(); os.replace(tmp, pdf_path)

def verify_pdf(path, label, expect_pages=None):
    from pypdf import PdfReader
    r = PdfReader(path); root = r.trailer["/Root"]
    check("/StructTreeRoot" in root, f"{label} is tagged for screen readers")
    check(root.get("/Lang") is not None, f"{label} declares a language")
    check("/Metadata" in root, f"{label} carries XMP metadata")
    if expect_pages:
        check(len(r.pages) == expect_pages,
              f"{label} is {expect_pages} page(s) — got {len(r.pages)}")
    return r


# --------------------------------------------------------------- the timestamp
def stamp_site(folder):
    """Write the current Pacific date and time into index.html's sidebar stamp.

    This is the ONE place the build edits a source file, and it is deliberate.
    The stamp used to be hand-maintained; on Sept 6, 2026 a full content pass
    shipped with a two-day-old date and Bruce reasonably concluded the deploy
    had failed. A stamp nobody has to remember cannot go stale.
    """
    path = os.path.join(folder, SITE)
    s = io.open(path, encoding="utf-8").read()
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    when = "%s %d, %d at %d:%02d %s Pacific" % (
        now.strftime("%B"), now.day, now.year,
        (now.hour % 12) or 12, now.minute, now.strftime("%p"))
    s, n = re.subn(r"Last updated [^<\n]*", "Last updated " + when, s, count=1)
    if n != 1:
        raise SystemExit("index.html: no 'Last updated' line to stamp")
    io.open(path, "w", encoding="utf-8").write(s)
    return when


# ------------------------------------------------------------------ the checks
def check_sources(folder):
    site = io.open(os.path.join(folder, SITE), encoding="utf-8").read()
    hand = io.open(os.path.join(folder, HAND), encoding="utf-8").read()
    md   = io.open(os.path.join(folder, MD),   encoding="utf-8").read()

    px = [float(x) for x in re.findall(r"font-size:([\d.]+)px", site)]
    check(min(px) >= MIN_PX_SCREEN,
          f"web page: nothing below {MIN_PX_SCREEN}px (smallest {min(px)}px)")

    # the print block must neutralise the dark palette or printing turns the page black
    pr = site[site.index("@media print{"):]
    for sel in (':root[data-theme="dark"]', ':root:not([data-theme="light"])'):
        check(sel in pr, f"print CSS overrides {sel} (dark-mode printing stays legible)")
    check("overflow:visible!important" in pr, "print CSS un-clips wide tables")
    check("display:table-header-group" in pr, "print CSS repeats table headers across pages")
    ppt = [float(x) for x in re.findall(r"font-size:([\d.]+)pt", pr)]
    check(min(ppt) >= 8.0, f"print CSS: nothing below 8pt (smallest {min(ppt)}pt)")

    hpt = [float(x) for x in re.findall(r"font-size:([\d.]+)pt", hand)]
    check(min(hpt) >= MIN_PT_PRINT,
          f"handout: nothing below {MIN_PT_PRINT}pt (smallest {min(hpt)}pt)")

    w = [int(x) for x in re.findall(r"^\| \*\*[^|]+\*\* \| (\d+)% \|", md, re.M)]
    check(sum(w) == 100, f"grade weights total 100% (got {sum(w)}: {w})")

    for name, text in (("web page", site), ("handout", hand), ("syllabus", md)):
        check("no final exam" not in text.lower(), f"{name}: no stale 'no final exam' text")
        check("Copilot and AI autocomplete in your editor" not in text,
              f"{name}: no stale 'turn off Copilot' instruction (students use cs50.dev)")

    check(bool(re.search(r"Last updated \w+ \d{1,2}, \d{4} at \d{1,2}:\d{2} [AP]M Pacific", site)),
          "web page carries a full date-and-time stamp")

    for f in (OUT_PDF, OUT_DOCX, OUT_HAND):
        check(f'href="{f}"' in site, f"web page still links {f}")

    for name, text in (("web page", site), ("handout", hand)):
        check("data:image/png;base64," not in text, f"{name}: no inlined QR image remains (removed Sept 2026)")
        check("bit.ly/ctec121fall2026" in text,
              f"{name}: the bit.ly short link is present as readable text")


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    for f in (MD, SITE, HAND):
        if not os.path.exists(os.path.join(folder, f)):
            raise SystemExit(f"missing source: {f} (in {folder})")

    print("stamped: Last updated " + stamp_site(folder) + "\n")

    check_sources(folder)
    build_docx(folder)

    pdf = os.path.join(folder, OUT_PDF)
    render_pdf(os.path.join(folder, SITE), pdf)
    stamp(pdf, "CTEC 121 Syllabus — Fall 2026",
          "Course syllabus for CTEC 121, Introduction to Programming and Problem "
          "Solving, Clark College, Fall 2026.")
    r = verify_pdf(pdf, "syllabus PDF")
    body = " ".join((r.pages[i].extract_text() or "") for i in range(min(3, len(r.pages))))
    check("clarkcollege.instructure.com" in body or "clark.edu" in body,
          "syllabus PDF printed link destinations (beforeprint ran)")

    hand = os.path.join(folder, OUT_HAND)
    render_pdf(os.path.join(folder, HAND), hand)
    stamp(hand, "CTEC 121 — Day One",
          "One-page reference for CTEC 121, Clark College, Fall 2026.")
    verify_pdf(hand, "handout PDF", expect_pages=1)

    print("\n".join(notes))
    if problems:
        print("\n" + "\n".join(problems))
        raise SystemExit(f"\n{len(problems)} check(s) failed — fix before publishing.")
    print(f"\nAll {len(notes)} checks passed. Outputs rebuilt in {folder}")


if __name__ == "__main__":
    main()
