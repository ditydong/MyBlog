"""Render Obsidian .canvas boards as MkDocs pages.

A .canvas file is JSON: nodes (text / file / group / link) positioned on an
infinite plane, plus edges between them. This hook turns every non-empty
canvas into a virtual page: nodes become absolutely positioned HTML boxes
(the text inside them is real Markdown), edges become an SVG layer with
arrowheads, and the whole board is scaled to fit the content width.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
from urllib.parse import quote

import markdown
from mkdocs.structure.files import File

CANVAS_SUFFIX = ".canvas"
CANVAS_EXT = ".canvas"

# src_uri of a generated page -> rendered board HTML
BOARDS: dict[str, str] = {}

# basename of a canvas (no extension) -> src_uri of its generated page
CANVAS_PAGES: dict[str, str] = {}

WIKI_CANVAS_LINK = re.compile(r"\[\[([^\]|#]+?)\.canvas(?:\|([^\]]+))?\]\]", re.IGNORECASE)

PRESET_COLORS = {
    "1": "#e93147",  # red
    "2": "#ec7500",  # orange
    "3": "#e0ac00",  # yellow
    "4": "#08b94e",  # green
    "5": "#00bfbc",  # cyan
    "6": "#7852ee",  # purple
}

WIKI_EMBED = re.compile(r"!\[\[([^\]|#]+?)(?:\|([^\]]+))?\]\]")
WIKI_LINK = re.compile(r"\[\[([^\]|#]+?)(?:\|([^\]]+))?\]\]")

BOARD_CSS = """
<style>
.canvas-scroll{overflow:auto;max-height:80vh;border:1px solid var(--md-default-fg-color--lightest);
border-radius:8px;background:var(--md-default-bg-color);margin:1em 0}
.canvas-board{position:relative}
.canvas-edges{position:absolute;left:0;top:0;pointer-events:none}
.canvas-node{position:absolute;box-sizing:border-box;overflow:hidden;
border:1px solid var(--md-default-fg-color--lightest);border-radius:8px;
background:var(--md-default-bg-color);padding:8px 10px;font-size:13px;line-height:1.55;
color:var(--md-default-fg-color)}
.canvas-node>:first-child{margin-top:0}
.canvas-node>:last-child{margin-bottom:0}
.canvas-node h1,.canvas-node h2,.canvas-node h3,.canvas-node h4{font-size:15px;margin:0 0 6px;
font-weight:600;color:var(--md-default-fg-color)}
.canvas-node p{margin:0 0 6px}
.canvas-node ul,.canvas-node ol{margin:0 0 6px;padding-left:1.2em}
.canvas-node pre{font-size:11px;line-height:1.45;margin:4px 0;padding:8px;overflow:auto}
.canvas-node code{font-size:11px}
.canvas-node table{font-size:11px;display:block;overflow:auto;color:var(--md-default-fg-color)}
.canvas-node img{max-width:100%}
.canvas-node blockquote{margin:0 0 6px;padding-left:8px;
border-left:3px solid var(--md-default-fg-color--lighter);color:var(--md-default-fg-color--light)}
.canvas-node a{color:var(--md-typeset-a-color)}
.canvas-group{position:absolute;box-sizing:border-box;border:1px solid;border-radius:10px}
.canvas-group-label{position:absolute;font-size:12px;color:var(--md-default-fg-color--light)}
.canvas-file{display:flex;align-items:center;gap:8px;font-size:13px}
.canvas-missing{color:var(--md-default-fg-color--light);font-style:italic}
</style>
"""


def _md() -> markdown.Markdown:
    return markdown.Markdown(
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html",
    )


def _tint(color: str) -> str:
    """Return an 8-digit hex with ~10% alpha for a preset color."""
    return color + "1a"


def _node_colors(node: dict) -> tuple[str | None, str | None]:
    """Return (background, border) for a node, or (None, None) for defaults."""
    color = node.get("color")
    if isinstance(color, str) and color in PRESET_COLORS:
        base = PRESET_COLORS[color]
        return _tint(base), base
    if isinstance(color, str) and color.startswith("#") and len(color) >= 7:
        return color + "22", color
    return None, None


def _rel_url(page_uri: str, target_uri: str, use_directory_urls: bool) -> str:
    """Relative URL from a generated page to a docs file."""
    stem, _ = posixpath.splitext(page_uri)
    if use_directory_urls:
        base = stem
    else:
        base = posixpath.dirname(page_uri)
    rel = posixpath.relpath(target_uri, start=base or ".")
    return quote(rel, safe="/")


def _doc_url(page_uri: str, target_uri: str, use_directory_urls: bool) -> str:
    """Relative URL of a Markdown page (its extension is not part of the URL)."""
    if not use_directory_urls:
        return _rel_url(page_uri, target_uri, False)
    stemless = target_uri[:-3] if target_uri.lower().endswith(".md") else target_uri
    base = posixpath.splitext(page_uri)[0]
    rel = posixpath.relpath(stemless, start=base or ".")
    return quote(rel, safe="/") + "/"


def _resolve_wiki(
    text: str,
    page_uri: str,
    docs_uris: set[str],
    use_directory_urls: bool,
) -> str:
    """Turn ![[image.png]] into a Markdown image and [[note]] into text."""

    def embed(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        target = _find_asset(name, page_uri, docs_uris)
        if target is None:
            return f"*（找不到附件：{name}）*"
        url = _rel_url(page_uri, target, use_directory_urls)
        return f'<img src="{url}" alt="{_inline_escape(name)}">'

    def link(match: re.Match[str]) -> str:
        label = (match.group(2) or match.group(1)).strip()
        target = _find_doc(match.group(1).strip(), page_uri, docs_uris)
        if target is None:
            return f"**{_inline_escape(label)}**"
        url = _doc_url(page_uri, target, use_directory_urls)
        return f'<a href="{url}">{_inline_escape(label)}</a>'

    text = WIKI_EMBED.sub(embed, text)
    text = WIKI_LINK.sub(link, text)
    return text


def _find_asset(name: str, page_uri: str, docs_uris: set[str]) -> str | None:
    """Find an attachment by its Obsidian vault-relative name."""
    candidates = [name, posixpath.join(posixpath.dirname(page_uri), name)]
    for candidate in candidates:
        candidate = candidate.replace("\\", "/").lstrip("/")
        if candidate in docs_uris:
            return candidate
    # Fall back to a suffix match anywhere in the docs tree
    for uri in docs_uris:
        if uri.endswith("/" + name):
            return uri
    return None


def _find_doc(name: str, page_uri: str, docs_uris: set[str]) -> str | None:
    """Find a Markdown note referenced as [[name]] / [[name.md]]."""
    base = name if name.lower().endswith(".md") else name + ".md"
    candidates = [base, posixpath.join(posixpath.dirname(page_uri), base)]
    for candidate in candidates:
        candidate = candidate.replace("\\", "/").lstrip("/")
        if candidate in docs_uris:
            return candidate
    for uri in docs_uris:
        if uri.endswith("/" + base):
            return uri
    return None


def _anchor(node: dict, side: str) -> tuple[float, float]:
    x, y = float(node["x"]), float(node["y"])
    w, h = float(node.get("width", 0)), float(node.get("height", 0))
    if side == "top":
        return x + w / 2, y
    if side == "bottom":
        return x + w / 2, y + h
    if side == "left":
        return x, y + h / 2
    if side == "right":
        return x + w, y + h / 2
    return x + w / 2, y + h / 2


def _edge_path(a: tuple[float, float], a_side: str, b: tuple[float, float], b_side: str) -> str:
    """Cubic bezier that leaves and enters each node perpendicular to its side."""
    offset = 70.0

    def ctrl(point: tuple[float, float], side: str) -> tuple[float, float]:
        x, y = point
        if side == "top":
            return x, y - offset
        if side == "bottom":
            return x, y + offset
        if side == "left":
            return x - offset, y
        if side == "right":
            return x + offset, y
        return x, y

    c1 = ctrl(a, a_side)
    c2 = ctrl(b, b_side)
    return (
        f"M {a[0]:.1f} {a[1]:.1f} "
        f"C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} "
        f"{b[0]:.1f} {b[1]:.1f}"
    )


def _render_node(
    node: dict,
    page_uri: str,
    docs_uris: set[str],
    use_directory_urls: bool,
    left: float,
    top: float,
) -> str:
    node_type = node.get("type")
    width = float(node.get("width", 0))
    height = float(node.get("height", 0))
    bg, border = _node_colors(node)

    if node_type == "group":
        label = (node.get("label") or "").strip()
        style = [
            f"left:{left:.0f}px",
            f"top:{top:.0f}px",
            f"width:{width:.0f}px",
            f"height:{height:.0f}px",
            f"border-color:{(border or '#88888855')}",
            f"background:{bg}" if bg else "background:transparent",
        ]
        label_html = ""
        if label:
            label_html = (
                f'<div class="canvas-group-label" style="left:{left + 10:.0f}px;'
                f'top:{top + 6:.0f}px">{_inline_escape(label)}</div>'
            )
        return (
            f'<div class="canvas-group" style="{";".join(style)}"></div>{label_html}'
        )

    if node_type == "file":
        return _render_file_node(
            node, page_uri, docs_uris, use_directory_urls, left, top, width, height
        )

    if node_type == "link":
        url = (node.get("url") or "").strip()
        style = [
            f"left:{left:.0f}px",
            f"top:{top:.0f}px",
            f"width:{width:.0f}px",
            f"height:{height:.0f}px",
        ]
        if bg:
            style.append(f"background:{bg}")
        if border:
            style.append(f"border-color:{border}")
        return (
            f'<div class="canvas-node" style="{";".join(style)}">'
            f'<a href="{_inline_escape(url)}">{_inline_escape(url)}</a></div>'
        )

    # text node (default)
    text = (node.get("text") or "").strip()
    if not text:
        return ""

    text = _resolve_wiki(text, page_uri, docs_uris, use_directory_urls)
    inner = _md().convert(text)

    style = [
        f"left:{left:.0f}px",
        f"top:{top:.0f}px",
        f"width:{width:.0f}px",
        f"height:{height:.0f}px",
    ]
    if bg:
        style.append(f"background:{bg}")
    if border:
        style.append(f"border-color:{border}")
    return f'<div class="canvas-node" style="{";".join(style)}">{inner}</div>'


def _render_file_node(
    node: dict,
    page_uri: str,
    docs_uris: set[str],
    use_directory_urls: bool,
    left: float,
    top: float,
    width: float,
    height: float,
) -> str:
    name = (node.get("file") or "").strip()
    style = [
        f"left:{left:.0f}px",
        f"top:{top:.0f}px",
        f"width:{width:.0f}px",
        f"height:{height:.0f}px",
    ]
    bg, border = _node_colors(node)
    if bg:
        style.append(f"background:{bg}")
    if border:
        style.append(f"border-color:{border}")

    target = _find_doc(name, page_uri, docs_uris) or _find_asset(name, page_uri, docs_uris)
    if target is None:
        return (
            f'<div class="canvas-node" style="{";".join(style)}">'
            f'<span class="canvas-missing">文件不存在：{_inline_escape(name)}</span></div>'
        )

    url = _rel_url(page_uri, target, use_directory_urls)
    if target.lower().endswith(".md"):
        url = _doc_url(page_uri, target, use_directory_urls)
    if target.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
        inner = f'<img src="{url}" alt="{_inline_escape(name)}">'
    else:
        label = posixpath.splitext(posixpath.basename(target))[0]
        inner = (
            f'<div class="canvas-file">📄 <a href="{url}">{_inline_escape(label)}</a></div>'
        )
    return f'<div class="canvas-node" style="{";".join(style)}">{inner}</div>'


def _inline_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_board(
    data: dict,
    page_uri: str,
    docs_uris: set[str],
    use_directory_urls: bool,
) -> str:
    nodes = [n for n in data.get("nodes", []) if isinstance(n, dict)]
    edges = [e for e in data.get("edges", []) if isinstance(e, dict)]
    if not nodes:
        return ""

    min_x = min(float(n.get("x", 0)) for n in nodes)
    min_y = min(float(n.get("y", 0)) for n in nodes)
    max_x = max(float(n.get("x", 0)) + float(n.get("width", 0)) for n in nodes)
    max_y = max(float(n.get("y", 0)) + float(n.get("height", 0)) for n in nodes)

    pad = 40.0
    width = max(max_x - min_x + 2 * pad, 400.0)
    height = max(max_y - min_y + 2 * pad, 300.0)

    def shift(node: dict) -> tuple[float, float]:
        return (
            float(node.get("x", 0)) - min_x + pad,
            float(node.get("y", 0)) - min_y + pad,
        )

    by_id = {n.get("id"): n for n in nodes}

    parts: list[str] = [BOARD_CSS]
    parts.append('<div class="canvas-scroll">')
    parts.append(
        f'<div class="canvas-board" style="width:{width:.0f}px;height:{height:.0f}px">'
    )

    # Edges first so nodes paint on top.
    if edges:
        parts.append(
            f'<svg class="canvas-edges" width="{width:.0f}" height="{height:.0f}" '
            f'viewBox="0 0 {width:.0f} {height:.0f}">'
            '<defs><marker id="canvas-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#888888"/></marker></defs>'
        )
        for edge in edges:
            src = by_id.get(edge.get("fromNode"))
            dst = by_id.get(edge.get("toNode"))
            if not src or not dst:
                continue
            a = _anchor(src, edge.get("fromSide", "right"))
            b = _anchor(dst, edge.get("toSide", "left"))
            a = (a[0] - min_x + pad, a[1] - min_y + pad)
            b = (b[0] - min_x + pad, b[1] - min_y + pad)
            path = _edge_path(a, edge.get("fromSide", "right"), b, edge.get("toSide", "left"))
            label = (edge.get("label") or "").strip()
            parts.append(
                f'<path d="{path}" fill="none" stroke="#888888" stroke-width="1.5" '
                'marker-end="url(#canvas-arrow)"/>'
            )
            if label:
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                parts.append(
                    f'<text x="{mx:.0f}" y="{my:.0f}" font-size="12" fill="#666666" '
                    f'text-anchor="middle">{_inline_escape(label)}</text>'
                )
        parts.append("</svg>")

    for node in nodes:
        left, top = shift(node)
        parts.append(
            _render_node(node, page_uri, docs_uris, use_directory_urls, left, top)
        )

    parts.append("</div></div>")
    return "".join(parts)


def on_files(files, config):
    """Add a virtual Markdown page for every non-empty canvas file."""
    docs_dir = config["docs_dir"]
    use_directory_urls = bool(config.get("use_directory_urls", True))
    existing = {f.src_uri for f in files}
    docs_uris = set(existing)

    generated = []
    for canvas_file in list(files):
        uri = canvas_file.src_uri
        if not uri.lower().endswith(CANVAS_SUFFIX):
            continue

        abs_path = os.path.join(docs_dir, uri.replace("/", os.sep))
        try:
            with open(abs_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue

        page_uri = uri[: -len(CANVAS_EXT)] + ".md"
        if page_uri in existing:
            continue

        html = render_board(data, page_uri, docs_uris, use_directory_urls)
        if not html:
            continue

        BOARDS[page_uri] = html
        CANVAS_PAGES[posixpath.splitext(posixpath.basename(uri))[0]] = page_uri
        generated.append(File.generated(config, page_uri, content=""))

    for file in generated:
        files.append(file)
    return files


def on_page_content(html, page, config, files):
    """Swap the placeholder page body for the rendered board."""
    board = BOARDS.get(page.file.src_uri)
    if board is None:
        return html
    return board


def on_page_markdown(markdown_text, page, config, files):
    """Point [[something.canvas]] links at the generated canvas page."""
    if not CANVAS_PAGES or ".canvas" not in markdown_text.lower():
        return markdown_text

    page_uri = page.file.src_uri
    use_directory_urls = bool(config.get("use_directory_urls", True))

    def replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        label = (match.group(2) or name).strip()
        target = CANVAS_PAGES.get(posixpath.basename(name)) or CANVAS_PAGES.get(name)
        if target is None:
            return match.group(0)
        url = _doc_url(page_uri, target, use_directory_urls)
        return f"[{label}]({url})"

    return WIKI_CANVAS_LINK.sub(replace, markdown_text)
