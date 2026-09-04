# CTEC 121 — rebuild and publish checklist

Every item here exists because it broke once. Work top to bottom.

## What is a source and what is generated

| Edit these | Never edit these — they are rebuilt |
|---|---|
| `CTEC_121_Syllabus_Fall_2026.md` | `CTEC_121_Syllabus_Fall_2026.docx` |
| `index.html` | `CTEC_121_Syllabus_Fall_2026.pdf` |
| `CTEC121_Day_One_source.html` | `CTEC121_Day_One.pdf` |
| `qr.png` | |

**`qr.png` stays local — it is not uploaded.** It encodes
`https://bit.ly/ctec121fall26?r=qr`. The two HTML files carry it inlined as a
base64 data URI (optimised to ~7 KB, 1-bit), so nothing can 404; the Word build
embeds the file itself via pandoc's `--resource-path`. If you replace the QR,
rerun the build so all three outputs pick it up, and check it still scans.

Editing a generated file means losing the change the next time anything is rebuilt.

## 1. Rebuild

In a Claude session with this folder connected, ask for a rebuild — or run:

```
python3 build/build_syllabus.py "/path/to/CTEC 121 Syllabus"
```

It needs chromium, pandoc, pikepdf and pypdf, which live in the Claude session's
container rather than on a Mac. It regenerates all three outputs and runs 29
checks. **If a check fails, fix the source — don't loosen the check.**

## 2. Keep the four copies telling the same story

The markdown, the web page, the PDF and the handout all repeat the same facts.
Change one and you must change all of them: dates, the grade weights, the
deadline rule, the AI rule. The build script verifies the weights total 100%
and that no stale text survives, but it cannot tell you that a date is wrong.

## 3. Upload

All four files go into the **same** directory on the server, because the page
links the PDF and DOCX by plain filename:

```
index.html
CTEC_121_Syllabus_Fall_2026.pdf
CTEC_121_Syllabus_Fall_2026.docx
CTEC121_Day_One.pdf
```

Server path: `/home/faculty/belgort/public_html/syllabi/<term>/ctec121/`
Public URL: `https://ctec.clark.edu/~belgort/syllabi/<term>/ctec121/`

## 4. Fix permissions — every single time

Uploading from macOS leaves files at `600` and directories possibly at `700`.
Apache answers that with **403 Forbidden**. Immediately after uploading:

```bash
chmod 711 /home/faculty/belgort
find /home/faculty/belgort/public_html -type d -exec chmod 755 {} \;
find /home/faculty/belgort/public_html -type f -exec chmod 644 {} \;
```

**403 vs 404 is the diagnosis.** 403 means Apache found the path and was
refused → permissions. 404 means the file genuinely isn't there → wrong name
or wrong directory. A correct leaf folder is not enough; every parent
directory needs `o+x`, home directory included.

If permissions are right and it is still forbidden: look for a stray
`.htaccess` with `Deny from all`, and on RHEL/Rocky/Alma run
`restorecon -Rv ~/public_html` for SELinux labels.

## 5. Check it in a browser

- The page loads and is styled.
- **Click the PDF and Word buttons** — they 403 for the same permission reason
  if you forgot step 4.
- Try the search box; type "exam".
- Open one collapsed College policies section.

## Things that have bitten before

- **Word showed "contains fields that may refer to other files."** Caused by a
  table-of-contents field. The build no longer uses one — headings are real
  Heading 1/2 styles, so Word's Navigation Pane works and
  References → Table of Contents inserts a live TOC in one click if wanted.
- **Printing from dark mode produced a black page.** The print CSS now
  redefines the whole palette under all three theme states. Don't remove those
  overrides.
- **Wide tables were clipped on paper.** The print CSS sets
  `overflow:visible` on table wrappers; the screen needs `overflow-x:auto`.
  Both are required.
- **Word opened as A4 for anyone outside the US.** Pandoc leaves the page size
  unset; the build stamps US Letter in.
- **Text too small.** Floors: **12px** on the web page, **9pt** in the handout
  and the print stylesheet. Watch `::before` pseudo-element content — the
  numbered step circles hid under a runtime scan and only a source scan caught
  them.
- **The QR fell below the masthead rule in the PDF.** `float:right` inside the
  print masthead drops past preceding block siblings. It is now anchored with
  `position:absolute` on a `position:relative` masthead, with right padding on
  `.masthead-in` to keep text clear of it. Don't reintroduce the float.
- **Generating the PDF with Playwright's `page.pdf()`** produces an untagged
  file and skips `beforeprint`. Use the chromium CLI with `--print-to-pdf`.

## Typography (decided Aug 30, 2026)

The web page must use **Atkinson Hyperlegible** — the Braille Institute's
legibility typeface, designed so easily-confused characters (I l 1, O 0, a e)
stay distinguishable. All three siblings are on Google Fonts:

- `Atkinson Hyperlegible Next` — body and headings (variable weight)
- `Atkinson Hyperlegible Mono` — labels, dates, tabular figures
- `Atkinson Hyperlegible` — the original, if the Next release is unavailable

Load them from `fonts.googleapis.com` with real fallback stacks, exactly as the
current page loads its faces. This replaces IBM Plex Sans / IBM Plex Mono.

## When the quarter changes

Update the markdown first, then the two HTML sources to match, then rebuild.
Check the Clark academic calendar for the new term's dates, and remember that
only **Monday and Wednesday** closures cost this section a class session.
