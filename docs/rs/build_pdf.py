"""Build the submitted RS PDF (#41): `RS.md`, with `scenarios.md` in full as Appendix C.

    python -m pip install markdown==3.11.3       # once; Python 3.12+
    python docs/rs/build_pdf.py                  # writes docs/rs/RS-<version>.pdf

It turns the Markdown into one HTML page and prints it with Google Chrome in headless mode, so
it needs Chrome (or Chromium) and nothing else: no LaTeX, no pandoc. Set `CHROME` to the
browser's executable if it is not in the usual place.

What it changes on the way, and why:

* **Appendix C.** `RS.md` only points to `scenarios.md`. The appendix's text is put under the
  "Appendix C" heading with its headings moved down two levels, so the PDF stands alone (RS
  Appendix C says so).
* **Links.** A relative link (`../../schemas/step.schema.json`) means nothing in a PDF, so it
  becomes a link to the same file on GitHub's `main` branch. A link to `scenarios.md` becomes
  a link to the appendix inside the PDF.

The output is a document, not build output: it is committed next to the Markdown because #41's
acceptance criterion asks for the PDF in `docs/rs/`. Rebuild it whenever a new version of the
RS is submitted, never edit it by hand.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
REPO_URL = "https://github.com/galipdg/AYNA/blob/main/"

CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "google-chrome",
    "chromium",
    "chromium-browser",
)

CSS = """
@page {
  size: A4;
  margin: 18mm 15mm 18mm 15mm;
  @bottom-center { content: "AYNA RS " var(--version) " · " counter(page) " / " counter(pages);
                   font: 8pt "Helvetica Neue", Arial, sans-serif; color: #555; }
}
html { --version: ""; }
body { font: 10pt/1.42 "Helvetica Neue", Arial, sans-serif; color: #111; }
h1 { font-size: 20pt; margin: 0 0 8pt; }
h2 { font-size: 15pt; margin: 18pt 0 6pt; border-bottom: 1px solid #999; padding-bottom: 2pt;
     break-before: page; }
h1 + table + h2, h2:first-of-type { break-before: auto; }
h3 { font-size: 12.5pt; margin: 14pt 0 5pt; }
h4 { font-size: 11pt; margin: 11pt 0 4pt; }
h5 { font-size: 10.5pt; margin: 10pt 0 3pt; }
h6 { font-size: 10pt; margin: 9pt 0 3pt; }
h2, h3, h4, h5, h6 { break-after: avoid; }
p, li { orphans: 3; widows: 3; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 9pt; font-size: 8pt;
        line-height: 1.3; }
th, td { border: 0.6pt solid #888; padding: 2.5pt 4pt; vertical-align: top; text-align: left; }
th { background: #eee; }
td.id { white-space: nowrap; }
tr { break-inside: avoid; }
code { font: 8.5pt Menlo, Consolas, monospace; background: #f3f3f3; padding: 0 1.5pt; }
pre { font: 7.5pt/1.25 Menlo, Consolas, monospace; background: #f6f6f6; padding: 6pt;
      border: 0.6pt solid #ccc; white-space: pre; overflow: hidden; break-inside: avoid; }
pre code { background: none; padding: 0; font: inherit; }
a { color: #0645ad; text-decoration: none; }
"""


def find_chrome() -> str:
    explicit = os.environ.get("CHROME")
    if explicit:
        return explicit
    for candidate in CHROME_CANDIDATES:
        found = shutil.which(candidate) or (
            candidate if Path(candidate).exists() else None
        )
        if found:
            return found
    sys.exit("Google Chrome or Chromium not found; set CHROME to its executable")


def version_of(rs: str) -> str:
    match = re.search(r"^\| Version \| ([0-9.]+)", rs, re.MULTILINE)
    if not match:
        sys.exit("RS.md has no '| Version | x.y' row")
    return match.group(1)


def with_appendix_c(rs: str, scenarios: str) -> str:
    """Put `scenarios.md` under the RS's Appendix C heading, two heading levels down."""
    heading = "### Appendix C — Reference scenarios"
    start = rs.index(heading)
    end = rs.index("\n### ", start + len(heading))
    body = scenarios.split("\n", 1)[1]  # its own title duplicates the appendix heading
    body = re.sub(
        r"^(#{2,4}) ",
        lambda m: "#" * (len(m.group(1)) + 2) + " ",
        body,
        flags=re.MULTILINE,
    )
    pointer = rs[start + len(heading) : end].strip()
    return f'{rs[:start]}<a id="appendix-c"></a>\n\n{heading}\n\n{pointer}\n\n{body}\n{rs[end:]}'


def absolute_links(text: str) -> str:
    """Relative links to repository files become GitHub links; `scenarios.md` stays inside."""

    def fix(match: re.Match[str]) -> str:
        target = match.group(1)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)
        if target in ("scenarios.md", "RS.md"):
            return "](#appendix-c)" if target == "scenarios.md" else "](#)"
        resolved = (HERE / target).resolve().relative_to(HERE.parents[1])
        return f"]({REPO_URL}{resolved.as_posix()})"

    return re.sub(r"\]\(([^)\s]+)\)", fix, text)


def lists_after_paragraphs(text: str) -> str:
    """Put a blank line before a list that follows a paragraph line directly.

    GitHub starts a list there; Python-Markdown does not and runs the items into the
    paragraph, which is how every scenario's Given/When/Then would print.
    """
    lines = text.split("\n")
    out: list[str] = []
    item = re.compile(r"^(?:- |\d+\. )")
    for line in lines:
        previous = out[-1] if out else ""
        if (
            item.match(line)
            and previous.strip()
            and not item.match(previous)
            and not previous.startswith((" ", "|"))
        ):
            out.append("")
        out.append(line)
    return "\n".join(out)


def main() -> None:
    rs = (HERE / "RS.md").read_text(encoding="utf-8")
    scenarios = (HERE / "scenarios.md").read_text(encoding="utf-8")
    version = version_of(rs)
    text = lists_after_paragraphs(absolute_links(with_appendix_c(rs, scenarios)))
    html_body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "sane_lists"]
    )
    # An ID such as `NFR-05` must not break at its hyphen; only those cells are kept whole,
    # because a wide cell that cannot wrap makes Chrome shrink the whole page to fit.
    html_body = re.sub(
        r"<td>((?:[A-Z]+-)?\d+(?:\.\d+)*|Q\d+)</td>",
        r'<td class="id">\1</td>',
        html_body,
    )
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>AYNA — Requirements Specification {version}</title>"
        f"<style>{CSS.replace('--version: ""', f'--version: "{version}"')}</style>"
        f"</head><body>{html_body}</body></html>"
    )
    out = HERE / f"RS-{version}.pdf"
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "rs.html"
        html.write_text(page, encoding="utf-8")
        subprocess.run(
            [
                find_chrome(),
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--user-data-dir={Path(tmp) / 'profile'}",
                f"--print-to-pdf={out}",
                html.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=180,
        )
    print(f"wrote {out.relative_to(HERE.parents[1])}")


if __name__ == "__main__":
    main()
