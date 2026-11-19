"""Build the submitted SDD PDF (#53) from `SDD.md`, with its Mermaid diagrams drawn.

    python -m pip install markdown==3.11.3       # once; Python 3.12+
    python docs/sdd/build_pdf.py                 # writes docs/sdd/SDD-<version>.pdf

It works like the RS's `docs/rs/build_pdf.py` (#41) and reuses its Chrome lookup, list fix and
page style: Markdown becomes one HTML page, which headless Chrome prints. What it adds:

* **Diagrams.** Each fenced `mermaid` block becomes a `<div class="mermaid">`, and the page
  carries Mermaid 11.4.1 inline from `vendor/` (MIT, `vendor/mermaid-LICENSE`), so the
  build needs no network. Chrome is given a virtual-time budget to let Mermaid draw before
  it prints; a diagram Mermaid cannot parse stops the build instead of printing an error box.
* **Links.** A relative link becomes a link to the same file on GitHub's `main` branch.

The PDF is a document, not build output: #53's acceptance criterion asks for it in
`docs/sdd/`. Rebuild it for each submitted version; never edit it by hand.
"""

from __future__ import annotations

import html
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO_URL = "https://github.com/galipdg/AYNA/blob/main/"
MERMAID = HERE / "vendor" / "mermaid-11.4.1.min.js"


def _rs_build():
    """The RS's build script, for its Chrome lookup, list fix and CSS."""
    spec = importlib.util.spec_from_file_location(
        "rs_build_pdf", ROOT / "docs/rs/build_pdf.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RS = _rs_build()

CSS = (
    RS.CSS.replace('"AYNA RS "', '"AYNA SDD "')
    + """
.mermaid { margin: 6pt 0 10pt; text-align: center; break-inside: avoid; }
.mermaid svg { max-width: 100%; height: auto; max-height: 230mm; }
p:has(+ .mermaid) { break-after: avoid; }
"""
)

# Mermaid draws every diagram, then marks the page so a failed parse is visible to the build.
SCRIPT = """
mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict",
                     flowchart: { useMaxWidth: true }, sequence: { useMaxWidth: true } });
mermaid.run({ querySelector: ".mermaid" })
  .then(() => { document.title = "MERMAID-OK " + document.title; })
  .catch((error) => { document.body.setAttribute("data-mermaid-error", String(error));
                      document.title = "MERMAID-FAILED"; });
"""


def version_of(sdd: str) -> str:
    match = re.search(r"^\| Version \| ([0-9.]+)", sdd, re.MULTILINE)
    if not match:
        sys.exit("SDD.md has no '| Version | x.y' row")
    return match.group(1)


def absolute_links(text: str) -> str:
    """Relative links to repository files become GitHub links."""

    def fix(match: re.Match[str]) -> str:
        target = match.group(1)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)
        resolved = (HERE / target).resolve().relative_to(ROOT)
        return f"]({REPO_URL}{resolved.as_posix()})"

    return re.sub(r"\]\(([^)\s]+)\)", fix, text)


def take_diagrams(text: str) -> tuple[str, list[str]]:
    """Replace each fenced mermaid block by a placeholder paragraph; return the sources."""
    diagrams: list[str] = []

    def take(match: re.Match[str]) -> str:
        diagrams.append(match.group(1))
        return f"\n\nMERMAIDDIAGRAM{len(diagrams) - 1}\n\n"

    return re.sub(
        r"^```mermaid\n(.*?)^```$", take, text, flags=re.MULTILINE | re.DOTALL
    ), diagrams


def put_diagrams(body: str, diagrams: list[str]) -> str:
    for index, source in enumerate(diagrams):
        div = f'<div class="mermaid">{html.escape(source)}</div>'
        body = body.replace(f"<p>MERMAIDDIAGRAM{index}</p>", div)
    if "MERMAIDDIAGRAM" in body:
        sys.exit("a diagram placeholder was not replaced")
    return body


def main() -> None:
    sdd = (HERE / "SDD.md").read_text(encoding="utf-8")
    version = version_of(sdd)
    text, diagrams = take_diagrams(sdd)
    text = RS.lists_after_paragraphs(absolute_links(text))
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    body = re.sub(
        r"<td>((?:[A-Z]+-)?\d+(?:\.\d+)*|Q\d+)</td>", r'<td class="id">\1</td>', body
    )
    body = put_diagrams(body, diagrams)
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>AYNA — Software Design Description {version}</title>"
        f"<style>{CSS.replace('--version: ""', f'--version: "{version}"')}</style>"
        f"</head><body>{body}"
        f"<script>{MERMAID.read_text(encoding='utf-8')}</script>"
        f"<script>{SCRIPT}</script></body></html>"
    )
    out = HERE / f"SDD-{version}.pdf"
    with tempfile.TemporaryDirectory() as tmp:
        page_file = Path(tmp) / "sdd.html"
        page_file.write_text(page, encoding="utf-8")
        chrome = [
            RS.find_chrome(),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--user-data-dir={Path(tmp) / 'profile'}",
            "--virtual-time-budget=30000",
        ]
        title = subprocess.run(
            [*chrome, "--dump-dom", page_file.as_uri()],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        ).stdout
        if 'aria-roledescription="error"' in title:
            sys.exit("Mermaid drew an error box: a diagram does not parse")
        if "MERMAID-OK" not in title:
            error = re.search(r'data-mermaid-error="([^"]*)"', title)
            sys.exit(
                f"Mermaid did not draw: {error.group(1) if error else 'no answer'}"
            )
        subprocess.run(
            [*chrome, f"--print-to-pdf={out}", page_file.as_uri()],
            check=True,
            capture_output=True,
            timeout=180,
        )
    print(f"wrote {out.relative_to(ROOT)} ({len(diagrams)} diagrams)")


if __name__ == "__main__":
    main()
