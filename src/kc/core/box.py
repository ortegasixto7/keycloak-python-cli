from __future__ import annotations

from typing import Iterable, List


def render_box(lines: List[str], jira_ticket: str, realm_label: str, title: str = "Keycloak CLI") -> str:
    header = _build_header_text(jira_ticket=jira_ticket, realm_label=realm_label, title=title)
    content_width = max([len(header)] + [len(l) for l in lines] + [80])
    top_bottom = "|" + (":" * (content_width + 2)) + "|"

    out_lines: list[str] = [top_bottom]
    out_lines.append(f"| {_pad_right(header, content_width)} |")
    for l in lines:
        out_lines.append(f"| {_pad_right(l, content_width)} |")
    out_lines.append(top_bottom)
    return "\n".join(out_lines)


def print_box(lines: List[str], jira_ticket: str, realm_label: str, title: str = "Keycloak CLI") -> None:
    import sys

    sys.stdout.write(render_box(lines, jira_ticket=jira_ticket, realm_label=realm_label, title=title) + "\n")


def _build_header_text(*, jira_ticket: str, realm_label: str, title: str) -> str:
    parts: list[str] = []
    if jira_ticket:
        parts.append(f"Jira Ticket: {jira_ticket}")
    if realm_label:
        parts.append(f"Current realm: {realm_label}")
    if not parts:
        return title or "Keycloak CLI"
    return " ::: ".join(parts)


def _pad_right(s: str, width: int) -> str:
    if len(s) >= width:
        return s
    return s + (" " * (width - len(s)))
