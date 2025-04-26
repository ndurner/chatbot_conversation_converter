"""
chatgpt_format_handler.py
~~~~~~~~~~~~~~~~~~~~~~~~~

Parses raw HTML exported from the ChatGPT web UI and converts it into
Workbench-style message dicts or clean Markdown (incl. code blocks).
"""

import re
from abc import ABC
from typing import Dict, List, Tuple, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from chat_format_base import ChatFormatHandler


# ────────────────────────────────────────────────────────────────────────────
#   Tiny HTML → Markdown engine tailored to ChatGPT HTML
# ────────────────────────────────────────────────────────────────────────────
class _HTML2MD:
    """
    Converts the restricted HTML that ChatGPT emits into Markdown.

    Supported:
      * headings h1-h6         * bold / italic / del
      * p / br                 * links
      * ul / ol / li           * blockquotes
      * hr                     * tables
      * <code> inline          * <pre><code> fenced blocks  ← NEW
    """

    def __init__(self):
        self._list_stack: List[Tuple[str, int]] = []

    # ── public entry ───────────────────────────────────────────────────────
    def convert(self, root: Tag) -> str:
        buf = [self._node_to_md(c) for c in root.children]
        md = "".join(buf)
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        return md

    # ── element dispatch ───────────────────────────────────────────────────
    def _node_to_md(self, node) -> str:
        if isinstance(node, NavigableString):
            return self._escape(node)

        if not isinstance(node, Tag):
            return ""

        name = node.name.lower()

        # ---------- block level ----------
        if name == "p":
            return self._children_md(node) + "\n\n"
        if name == "br":
            return "  \n"
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lvl = int(name[1])
            return "#" * lvl + " " + self._children_md(node).strip() + "\n\n"
        if name == "hr":
            return "\n---\n\n"
        if name == "blockquote":
            inner = self._children_md(node).strip().splitlines()
            return "\n".join("> " + l for l in inner) + "\n\n"

        # ---------- lists ----------
        if name in ("ul", "ol"):
            self._list_stack.append((name, 0))
            body = self._children_md(node)
            self._list_stack.pop()
            return body
        if name == "li":
            bullet, _ = self._current_list_marker()
            nested = self._children_md(node).strip().replace("\n", "\n   ")
            return f"{bullet} {nested}\n"

        # ---------- tables ----------
        if name == "table":
            return self._table_to_md(node) + "\n\n"

        # ---------- CODE BLOCKS ----------
        if name == "pre":
            return self._pre_to_md(node)

        # ---------- inline ----------
        if name == "strong":
            return f"**{self._children_md(node).strip()}**"
        if name == "em":
            return f"*{self._children_md(node).strip()}*"
        if name == "del":
            return f"~~{self._children_md(node).strip()}~~"
        if name == "a":
            txt = self._children_md(node).strip()
            href = node.get("href", "#")
            return f"[{txt}]({href})"
        if name == "sup":
            return f"^{self._children_md(node).strip()}"
        if name == "code":                       # INLINE CODE (NEW)
            return f"`{self._children_md(node).strip()}`"

        # fallback – descend
        return self._children_md(node)

    # ── helpers ────────────────────────────────────────────────────────────
    def _children_md(self, parent: Tag) -> str:
        return "".join(self._node_to_md(c) for c in parent.children)

    def _escape(self, txt: str) -> str:
        return (str(txt)
                .replace("\\", "\\\\")
                .replace("*", "\\*")
                .replace("_", "\\_"))

    def _current_list_marker(self) -> Tuple[str, int]:
        if not self._list_stack:
            return ("*", 0)
        kind, idx = self._list_stack[-1]
        if kind == "ul":
            return ("*", idx)
        self._list_stack[-1] = (kind, idx + 1)
        return (f"{idx + 1}.", idx + 1)

    # ── table conversion ───────────────────────────────────────────────────
    def _table_to_md(self, table: Tag) -> str:
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            rows.append([self._children_md(c).strip() for c in cells])

        if not rows:
            return ""

        header = "| " + " | ".join(rows[0]) + " |"
        sep = "| " + " | ".join("---" for _ in rows[0]) + " |"
        body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
        return "\n".join([header, sep, body])

    # ── code-block conversion ────────────────────────────────────────
    def _pre_to_md(self, pre: Tag) -> str:
        """
        ChatGPT wraps its block code like:

        <pre>
          <div>python</div>        ← language label
          … more divs …
          <code><span>def …</span></code>
        </pre>
        """
        # language: first inner DIV's text if short
        lang = ""
        first_div = pre.find("div")
        if first_div and first_div.string:
            txt = first_div.string.strip()
            if 0 < len(txt) <= 20 and " " not in txt:
                lang = txt

        code_tag = pre.find("code") or pre
        code_text = code_tag.get_text("", strip=False)

        # Normalise line endings & trim leading / trailing newlines
        code_text = code_text.replace("\r\n", "\n").strip("\n")

        return f"\n```{lang}\n{code_text}\n```\n\n"


# ────────────────────────────────────────────────────────────────────────────
#                         ChatGPTFormatHandler
# ────────────────────────────────────────────────────────────────────────────
class ChatGPTFormatHandler(ChatFormatHandler):
    """Handles raw ChatGPT chat-page HTML."""

    # ---------- detection --------------------------------------------------
    @classmethod
    def can_handle(cls, data):
        return (isinstance(data, str)
                and "<article" in data
                and "data-message-author-role" in data)

    # ---------- extraction -------------------------------------------------
    def _extract_messages(self, html: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        h2md = _HTML2MD()
        messages: List[Dict[str, str]] = []

        for n in soup.find_all(attrs={"data-message-author-role": True}):
            role_raw = n["data-message-author-role"].lower()
            role = "assistant" if role_raw == "assistant" else "user"

            # assistant messages – use the dedicated .markdown div if present
            md_container = n.find(class_="markdown")
            if md_container:
                content = h2md.convert(md_container).strip()
            else:
                # user messages:
                #  - if it *contains* a <pre> / <code> (or table …) we need full MD conversion
                #  - otherwise plain visible text is fine
                if n.find(["pre", "code", "table", "blockquote", "ul", "ol"]):
                    content = h2md.convert(n).strip()
                else:
                    content = n.get_text(" ", strip=True)

            if content:
                messages.append({"role": role, "content": content})

        return messages
    
    # ---------- public API -------------------------------------------------
    def to_markdown(self) -> str:
        msgs = self._extract_messages(self.json_data)
        md = self._create_markdown_structure(model="ChatGPT-web")
        md += self._format_messages(msgs)
        return md

    def to_workbench(self):
        return {"messages": self._extract_messages(self.json_data)}