# Syllabi

Course syllabi for Bruce Elgort's classes at Clark College, one folder per term and course:

```
<term>/<course>/
```

Each course folder holds three hand-edited sources and the three files built from them:

| Edit these | Generated — never hand-edit |
|---|---|
| `CTEC_121_Syllabus_<Term>.md` | `CTEC_121_Syllabus_<Term>.docx` |
| `index.html` | `CTEC_121_Syllabus_<Term>.pdf` |
| `CTEC121_Day_One_source.html` | `CTEC121_Day_One.pdf` |

`build/build_syllabus.py` regenerates the outputs and runs the checks; `build/PUBLISHING.md` is the rebuild-and-upload checklist. The generated files are committed too, because they are exactly what gets uploaded to `ctec.clark.edu/~belgort/syllabi/<term>/<course>/`.

## Terms

- [`fall-2026/ctec121`](fall-2026/ctec121) — CTEC 121, Introduction to Programming and Problem Solving
