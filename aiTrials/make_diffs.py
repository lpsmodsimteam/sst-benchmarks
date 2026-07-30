#!/usr/bin/env python3
"""Generate one HTML report with notebook cell-content diffs for all AI trials."""

import difflib
import html as html_lib
import markdown as markdown_lib
import nbformat
import pathlib

import pygments
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

_LEXER     = PythonLexer()
_FORMATTER = HtmlFormatter(nowrap=True, style="friendly")
_PYGMENTS_CSS = HtmlFormatter(style="friendly").get_style_defs("")


def _hl(line):
    """Return syntax-highlighted HTML for a single line of Python."""
    return pygments.highlight(line, _LEXER, _FORMATTER).rstrip("\n")

BASE_NB    = pathlib.Path("./scale_model_size.ipynb")
BASE_WORKFLOWS = pathlib.Path("./utils/workflows.py")
TRIALS_DIR = pathlib.Path(".")
OUT_FILE   = pathlib.Path("all_trials_diff.html")
AI_HEADER  = "# AI Modified Workflow"


def _extract_header_cell_parts(nb):
    """Return (prompt_text, commentary_text) from the AI header cell, or (None, None)."""
    cells = list(nb.cells)
    if not cells:
        return None, None
    first = cells[0]
    if not (first.cell_type == "markdown" and (first.source or "").strip().startswith(AI_HEADER)):
        return None, None
    lines = first.source.splitlines()

    # Find the first '---' separator — prompt is everything between the intro line and it
    try:
        sep_idx = next(i for i, l in enumerate(lines) if l.strip() == "---")
    except StopIteration:
        return None, None

    # Prompt: lines between the intro paragraph and the separator
    # Skip lines that are part of the intro (lines containing "For this workflow" etc.)
    prompt_lines = []
    in_intro = True
    for line in lines[1:sep_idx]:
        if in_intro and (not line.strip() or line.strip().startswith("For this workflow")):
            continue
        in_intro = False
        prompt_lines.append(line)
    prompt = "\n".join(prompt_lines).strip()

    # Commentary: everything after the first separator, stripping trailing separators
    commentary_lines = lines[sep_idx + 1:]
    while commentary_lines and commentary_lines[-1].strip() in ("-", "--", "---"):
        commentary_lines.pop()
    commentary = "\n".join(commentary_lines).strip()

    return (prompt or None), (commentary or None)


def _normalize_cells(nb):
    """Return cells from the first post-separator cell, with Configuration fallback."""
    cells = list(nb.cells)
    if not cells:
        return cells

    # Preferred start: first cell after a markdown cell that contains at least
    # three horizontal-rule separator lines ("---").
    for idx, cell in enumerate(cells):
        if cell.cell_type != "markdown":
            continue
        sep_count = sum(1 for line in cell.source.splitlines() if line.strip() == "---")
        if sep_count >= 3:
            return cells[idx + 1:]

    # Fallback for older notebook structures: start at Configuration.
    for idx, cell in enumerate(cells):
        if cell.cell_type != "markdown":
            continue
        lines = [l.strip() for l in cell.source.splitlines() if l.strip()]
        if not lines:
            continue
        first_line = lines[0]
        if first_line.startswith("#") and first_line.lstrip("#").strip().lower().startswith("configuration"):
            return cells[idx:]

    return cells


def _find_preceding_header(cells, idx):
    """Return the nearest markdown header text before cells[idx], or None."""
    for i in range(idx - 1, -1, -1):
        cell = cells[i]
        if cell.cell_type == "markdown":
            for line in cell.source.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    return stripped.lstrip("#").strip()
    return None


def _make_diff_table(base_lines, trial_lines, fromdesc, todesc):
    """Side-by-side diff table with Pygments syntax highlighting per line."""
    matcher = difflib.SequenceMatcher(None, base_lines, trial_lines, autojunk=False)
    rows = []
    ln_l = ln_r = 1

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        lchunk = base_lines[i1:i2]
        rchunk = trial_lines[j1:j2]

        if tag == "equal":
            for l, r in zip(lchunk, rchunk):
                rows.append(("", ln_l, _hl(l), "", ln_r, _hl(r)))
                ln_l += 1; ln_r += 1
        elif tag == "replace":
            for k in range(max(len(lchunk), len(rchunk))):
                lc = rc = "diff_chg"
                if k >= len(lchunk): lc = ""
                if k >= len(rchunk): rc = ""
                ll = _hl(lchunk[k]) if k < len(lchunk) else ""
                rr = _hl(rchunk[k]) if k < len(rchunk) else ""
                lno = ln_l if k < len(lchunk) else ""
                rno = ln_r if k < len(rchunk) else ""
                rows.append((lc, lno, ll, rc, rno, rr))
                if k < len(lchunk): ln_l += 1
                if k < len(rchunk): ln_r += 1
        elif tag == "delete":
            for l in lchunk:
                rows.append(("diff_sub", ln_l, _hl(l), "diff_sub", "", ""))
                ln_l += 1
        elif tag == "insert":
            for r in rchunk:
                rows.append(("diff_add", "", "", "diff_add", ln_r, _hl(r)))
                ln_r += 1

    row_html = [
        f'<tr>'
        f'<td class="ln">{lno}</td><td class="{lc}">{ll}</td>'
        f'<td class="ln">{rno}</td><td class="{rc}">{rr}</td>'
        f'</tr>'
        for lc, lno, ll, rc, rno, rr in rows
    ]

    return (
        f'<table class="diff">'
        f'<thead><tr>'
        f'<th colspan="2">{html_lib.escape(fromdesc)}</th>'
        f'<th colspan="2">{html_lib.escape(todesc)}</th>'
        f'</tr></thead>'
        f'<tbody>{"" .join(row_html)}</tbody>'
        f'</table>'
    )


def _prompt_html(text):
    """Render the prompt as a styled callout block."""
    return (
        f'<div class="prompt"><strong>Prompt:</strong>'
        f'<blockquote>{html_lib.escape(text)}</blockquote></div>'
    )


def _commentary_html(text):
    """Render markdown commentary as HTML inside a styled div."""
    rendered = markdown_lib.markdown(text, extensions=["fenced_code", "nl2br"])
    return f'<div class="commentary"><strong>Commentary:</strong>{rendered}</div>'


def _make_section(base_cells, trial_cells, base_desc, trial_desc):
    """Produce HTML showing all changed cells, with preceding section header as context."""
    base_sources  = [c.source for c in base_cells]
    trial_sources = [c.source for c in trial_cells]

    matcher = difflib.SequenceMatcher(None, base_sources, trial_sources, autojunk=False)
    parts = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        # Determine the preceding header for context
        if tag == "insert":
            header = _find_preceding_header(trial_cells, j1)
        else:
            header = _find_preceding_header(base_cells, i1)
            if header is None and tag == "replace":
                header = _find_preceding_header(trial_cells, j1)

        header_html = (
            f'<p class="cell-context">Section: <strong>{html_lib.escape(header)}</strong></p>'
            if header else ""
        )

        if tag == "replace":
            base_text  = "\n\n# ---- cell ----\n\n".join(base_sources[i1:i2])
            trial_text = "\n\n# ---- cell ----\n\n".join(trial_sources[j1:j2])
            table = _make_diff_table(base_text.splitlines(), trial_text.splitlines(), base_desc, trial_desc)
        elif tag == "delete":
            base_text = "\n\n# ---- cell ----\n\n".join(base_sources[i1:i2])
            table = _make_diff_table(base_text.splitlines(), [], base_desc, trial_desc)
        elif tag == "insert":
            trial_text = "\n\n# ---- cell ----\n\n".join(trial_sources[j1:j2])
            table = _make_diff_table([], trial_text.splitlines(), base_desc, trial_desc)

        parts.append(header_html + table)

    return "\n".join(parts) if parts else "<p><em>No differences found.</em></p>"


def _make_file_diff_section(base_file, trial_file):
    """Produce HTML for a Python file diff, or None if the trial file is absent."""
    if not trial_file.exists():
        return None

    base_lines = base_file.read_text().splitlines()
    trial_lines = trial_file.read_text().splitlines()
    table = _make_diff_table(
        base_lines,
        trial_lines,
        str(base_file),
        str(trial_file.relative_to(TRIALS_DIR)),
    )
    return f'<h3>workflows.py diff</h3>\n{table}'



def _build_report(base_desc, sections):
    nav_items     = []
    body_sections = []

    for section_id, title, nb_path, transcript_path, extra_paths, prompt, commentary, content_html in sections:
        nav_items.append(f'<li><a href="#{section_id}">{html_lib.escape(title)}</a></li>')
        prompt_block     = _prompt_html(prompt) if prompt else ""
        commentary_block = _commentary_html(commentary) if commentary else ""
        links = [f'<a href="{html_lib.escape(nb_path)}">notebook</a>']
        if transcript_path:
            links.append(f'<a href="{html_lib.escape(transcript_path)}">transcript</a>')
        for label, path in extra_paths:
            links.append(f'<a href="{html_lib.escape(path)}">{html_lib.escape(label)}</a>')
        links_html = f'<p class="trial-links">{" &nbsp;|&nbsp; ".join(links)}</p>'
        body_sections.append(
            f'<h2 id="{section_id}">{html_lib.escape(title)}</h2>\n'
            f"{links_html}\n"
            f"{prompt_block}\n"
            f"{commentary_block}\n"
            f"{content_html}"
        )

    return f"""<!-- AUTOGENERATED FILE. Do not edit directly.
     To regenerate, run: python make_diffs.py  (from the aiTrials/ directory) -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Trial Notebook Diffs</title>
  <style>
    body {{ font-family: sans-serif; margin: 1.5rem; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .meta {{ color: #555; margin-bottom: 1rem; }}
    .toc {{ margin-bottom: 2rem; }}
    .cell-context {{ font-size: 0.9rem; color: #333; margin: 1.5rem 0 0.25rem; border-left: 3px solid #aaa; padding-left: 0.5rem; }}
    .prompt {{ background: #eef4ff; border-left: 4px solid #4a90d9; padding: 0.4rem 1rem; margin: 0.75rem 0 0.5rem; font-size: 0.9rem; }}
    .prompt blockquote {{ margin: 0.3rem 0 0; padding: 0; font-style: italic; }}
    .trial-links {{ font-size: 0.85rem; margin: 0.25rem 0 0.75rem; }}
    .commentary {{ background: #f9f9f9; border-left: 4px solid #888; padding: 0.6rem 1rem; margin: 0.25rem 0 1.5rem; font-size: 0.9rem; line-height: 1.5; }}
    .commentary p {{ margin: 0.4rem 0; }}
    table.diff {{ width: 100%; border-collapse: collapse; margin-bottom: 0.5rem; font-family: monospace; font-size: 0.85rem; }}
    table.diff th {{ background: #f3f3f3; text-align: left; padding: 0.3rem 0.5rem; }}
    td, th {{ padding: 0.2rem 0.4rem; vertical-align: top; }}
    td.ln {{ width: 2.5rem; color: #999; text-align: right; user-select: none; border-right: 1px solid #ddd; }}
    .diff_add {{ background-color: #d6ffd6; }}
    .diff_chg {{ background-color: #fff3bf; }}
    .diff_sub {{ background-color: #ffd6d6; }}
    h2 {{ border-top: 2px solid #ccc; padding-top: 0.75rem; margin-top: 2.5rem; }}
    {_PYGMENTS_CSS}
  </style>
</head>
<body>
  <h1>AI Trial Notebook Diffs</h1>
  <p class="meta">
    Base: <code>{html_lib.escape(base_desc)}</code>.
    Shows full cell content for changed cells only.
        Comparison starts at the first cell after a header cell with three &ldquo;---&rdquo; separators (or &ldquo;Configuration&rdquo; when no separator block is present).
    Section labels above each diff come from the nearest preceding markdown header.
  </p>
  <div class="toc">
    <h2>Contents</h2>
    <ul>
      {"".join(nav_items)}
    </ul>
  </div>
  {"".join(body_sections)}
</body>
</html>
"""


def main():
    base_nb    = nbformat.read(BASE_NB, as_version=4)
    base_cells = _normalize_cells(base_nb)

    trials   = sorted(TRIALS_DIR.glob("*/*.ipynb"))
    sections = []

    for trial_path in trials:
        trial_nb    = nbformat.read(trial_path, as_version=4)
        trial_cells = _normalize_cells(trial_nb)

        base_desc  = str(BASE_NB)
        trial_desc = str(trial_path.relative_to(TRIALS_DIR))

        prompt, commentary = _extract_header_cell_parts(trial_nb)
        nb_path         = str(trial_path.relative_to(TRIALS_DIR))
        transcript_file = trial_path.parent / "transcript.txt"
        transcript_path = str(transcript_file.relative_to(TRIALS_DIR)) if transcript_file.exists() else None
        content_html = _make_section(base_cells, trial_cells, base_desc, trial_desc)

        extra_paths = []
        workflows_new_file = trial_path.parent / "workflows_new.py"
        if workflows_new_file.exists():
            extra_paths.append(("workflows_new.py", str(workflows_new_file.relative_to(TRIALS_DIR))))
            workflows_diff_html = _make_file_diff_section(BASE_WORKFLOWS, workflows_new_file)
            if workflows_diff_html:
                content_html = f"{content_html}\n{workflows_diff_html}"

        section_id   = f"trial-{trial_path.parent.name}"
        title        = f"{trial_path.parent.name} / {trial_path.name}"
        sections.append((section_id, title, nb_path, transcript_path, extra_paths, prompt, commentary, content_html))

    OUT_FILE.write_text(_build_report(str(BASE_NB), sections))
    print(f"wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
