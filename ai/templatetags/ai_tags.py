"""Renders Ask AI answers: markdown tables become HTML tables, everything else plain text. All text is escaped."""

import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_SEPARATOR = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")
_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _inline(text):
    """Escape, then drop any **bold** markers."""
    return _BOLD.sub(r"\1", escape(text))
    pass


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]
    pass


def _table(lines):
    rows = [_cells(line) for line in lines if not _SEPARATOR.match(line.strip())]
    if not rows:
        return ""
    head, body = rows[0], rows[1:]
    html = ['<div class="overflow-x-auto"><table class="w-full text-xs border-collapse"><thead><tr>']
    for cell in head:
        html.append(f'<th class="text-left font-semibold text-gray-600 border-b border-gray-200 px-1.5 py-1 whitespace-nowrap">{_inline(cell)}</th>')
    html.append("</tr></thead><tbody>")
    for row in body:
        html.append("<tr>")
        for cell in row:
            html.append(f'<td class="border-b border-gray-100 px-1.5 py-1 text-gray-700">{_inline(cell)}</td>')
        html.append("</tr>")
    html.append("</tbody></table></div>")
    return "".join(html)
    pass


@register.filter
def render_answer(text):
    """Split the answer into table and text blocks and render each."""
    blocks = []
    for line in (text or "").splitlines():
        kind = "table" if line.strip().startswith("|") else "text"
        if blocks and blocks[-1][0] == kind:
            blocks[-1][1].append(line)
        else:
            blocks.append((kind, [line]))

    parts = []
    for kind, lines in blocks:
        if kind == "table":
            parts.append(_table(lines))
            continue
        text_lines = [_inline(line) for line in lines]
        while text_lines and not text_lines[0].strip():
            text_lines.pop(0)
        while text_lines and not text_lines[-1].strip():
            text_lines.pop()
        if text_lines:
            parts.append("<p>" + "<br>".join(text_lines) + "</p>")

    return mark_safe('<div class="space-y-2">' + "".join(parts) + "</div>")
    pass