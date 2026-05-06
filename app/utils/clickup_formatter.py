"""
ArkLog - Markdown to ClickUp Plain Text Converter

ClickUp task comment API only accepts comment_text (plain text).
Rich text delta format is not supported via the public API.

This module strips Markdown markers and replaces them with
visual plain-text equivalents that render cleanly in ClickUp.
"""

import re


def markdown_to_clickup(text: str) -> str:
    """Convert Markdown to visually structured plain text for ClickUp."""
    lines = text.split("\n")
    out: list[str] = []

    for line in lines:
        if line.startswith("### "):
            content = _strip_inline(line[4:])
            out.append(f"\n◆ {content}")
        elif line.startswith("## "):
            content = _strip_inline(line[3:])
            out.append(f"\n{content.upper()}")
        elif line.startswith("# "):
            content = _strip_inline(line[2:])
            out.append(f"\n{content.upper()}")
        elif re.match(r"^[-*] ", line):
            content = _strip_inline(line[2:])
            out.append(f"  • {content}")
        elif line.strip() == "---":
            out.append("─" * 40)
        else:
            out.append(_strip_inline(line))

    return "\n".join(out).strip()


def _strip_inline(text: str) -> str:
    """Remove **bold** and *italic* markers, keeping the text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text
