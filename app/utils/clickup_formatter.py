"""
ArkLog - Markdown to ClickUp Rich Text Converter

ClickUp comments use Quill delta format, not Markdown.
This module converts the Markdown subset produced by the AI into
ClickUp-compatible delta operations.

Supported: ## headings, ### subheadings, **bold**, *italic*, - bullets, plain text.
"""

import re
from typing import Any

Op = dict[str, Any]


def markdown_to_clickup(text: str) -> list[Op]:
    """Convert Markdown to ClickUp Quill delta operations."""
    ops: list[Op] = []

    for line in text.split("\n"):
        if line.startswith("### "):
            _parse_inline(ops, line[4:])
            ops.append({"insert": "\n", "attributes": {"header": 3}})
        elif line.startswith("## "):
            _parse_inline(ops, line[3:])
            ops.append({"insert": "\n", "attributes": {"header": 2}})
        elif line.startswith("# "):
            _parse_inline(ops, line[2:])
            ops.append({"insert": "\n", "attributes": {"header": 1}})
        elif re.match(r"^[-*] ", line):
            _parse_inline(ops, line[2:])
            ops.append({"insert": "\n", "attributes": {"list": "bullet"}})
        elif line.strip() == "---":
            ops.append({"insert": "\n"})
        else:
            _parse_inline(ops, line)
            ops.append({"insert": "\n"})

    return ops


def _parse_inline(ops: list[Op], text: str) -> None:
    """Parse **bold** and *italic* inline markers into delta ops."""
    for m in re.finditer(r"\*\*(.+?)\*\*|\*(.+?)\*|([^*]+)", text):
        bold, italic, plain = m.group(1), m.group(2), m.group(3)
        if bold:
            ops.append({"insert": bold, "attributes": {"bold": True}})
        elif italic:
            ops.append({"insert": italic, "attributes": {"italic": True}})
        elif plain:
            ops.append({"insert": plain})
