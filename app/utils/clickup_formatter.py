"""
ArkLog - Markdown to ClickUp Rich Text Converter

ClickUp comments use a Quill-based delta format where each op uses
"text" (not "insert") and lists use {"list": {"list": "bullet"}}.

Supported: ## headings, ### subheadings, **bold**, *italic*, - bullets, plain text.
"""

import re
from typing import Any

Op = dict[str, Any]


def markdown_to_clickup(text: str) -> list[Op]:
    """Convert Markdown to ClickUp delta operations."""
    ops: list[Op] = []

    for line in text.split("\n"):
        if line.startswith("### "):
            _parse_inline(ops, line[4:])
            ops.append({"text": "\n", "attributes": {"header": 3}})
        elif line.startswith("## "):
            _parse_inline(ops, line[3:])
            ops.append({"text": "\n", "attributes": {"header": 2}})
        elif line.startswith("# "):
            _parse_inline(ops, line[2:])
            ops.append({"text": "\n", "attributes": {"header": 1}})
        elif re.match(r"^[-*] ", line):
            _parse_inline(ops, line[2:])
            ops.append({"text": "\n", "attributes": {"list": {"list": "bullet"}}})
        elif line.strip() == "---":
            ops.append({"text": "\n"})
        else:
            _parse_inline(ops, line)
            ops.append({"text": "\n"})

    return ops


def _parse_inline(ops: list[Op], text: str) -> None:
    """Parse **bold** and *italic* inline markers into delta ops."""
    for m in re.finditer(r"\*\*(.+?)\*\*|\*(.+?)\*|([^*]+)", text):
        bold, italic, plain = m.group(1), m.group(2), m.group(3)
        if bold:
            ops.append({"text": bold, "attributes": {"bold": True}})
        elif italic:
            ops.append({"text": italic, "attributes": {"italic": True}})
        elif plain:
            ops.append({"text": plain})
