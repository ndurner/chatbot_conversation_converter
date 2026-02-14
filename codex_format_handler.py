"""Codex session JSONL format handler."""

import json
import os
import re
from pathlib import Path
from typing import Dict, List

from chat_format_base import ChatFormatHandler


class CodexFormatHandler(ChatFormatHandler):
    """Handler for Codex session JSONL exports."""

    _CONTROL_PREFIXES = (
        "<permissions instructions>",
        "<collaboration_mode>",
        "<app-context>",
        "<model_switch>",
    )
    _IDE_CONTEXT_PREFIX = "# Context from my IDE setup:"
    _IDE_REQUEST_MARKER = "## My request for Codex:"
    _SESSION_ID_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    _THREAD_URL_PATTERN = re.compile(
        r"^codex://threads/([0-9a-f-]{36})/?$",
        re.IGNORECASE,
    )
    _SESSION_FILE_PATTERN = re.compile(
        r".*-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$",
        re.IGNORECASE,
    )

    @classmethod
    def can_handle(cls, data):
        if not isinstance(data, str):
            return False

        seen = 0
        for raw_line in data.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            seen += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                return False

            if not isinstance(obj, dict):
                return False

            if "type" not in obj or "payload" not in obj:
                return False

            if obj.get("type") in {"session_meta", "response_item", "turn_context", "event_msg"}:
                return True

            if seen >= 20:
                break

        return False

    @classmethod
    def _find_session_file(cls, session_id: str) -> str:
        sessions_root = Path("~/.codex/sessions").expanduser()
        if not sessions_root.exists():
            raise FileNotFoundError(f"Codex sessions directory not found: {sessions_root}")

        matches = list(sessions_root.glob(f"**/*-{session_id}.jsonl"))
        if not matches:
            raise FileNotFoundError(f"No Codex session found for ID: {session_id}")

        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return str(matches[0])

    @classmethod
    def extract_session_id_from_path(cls, path: str):
        match = cls._SESSION_FILE_PATTERN.match(os.path.basename(path))
        if match:
            return match.group(1)
        return None

    @classmethod
    def resolve_input_spec(cls, input_spec: str):
        """Resolve Codex input spec (session ID / thread URL / session file path)."""
        if os.path.isfile(input_spec):
            session_id = cls.extract_session_id_from_path(input_spec)
            if session_id:
                return {"resolved_path": input_spec, "codex_session_id": session_id}
            return None

        url_match = cls._THREAD_URL_PATTERN.match(input_spec)
        if url_match:
            session_id = url_match.group(1)
            return {"resolved_path": cls._find_session_file(session_id), "codex_session_id": session_id}

        if cls._SESSION_ID_PATTERN.match(input_spec):
            session_id = input_spec
            return {"resolved_path": cls._find_session_file(session_id), "codex_session_id": session_id}

        return None

    @classmethod
    def _lookup_thread_title(cls, session_id: str):
        state_file = Path("~/.codex/.codex-global-state.json").expanduser()
        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        try:
            title = data["thread-titles"]["titles"].get(session_id)
        except (KeyError, TypeError, AttributeError):
            return None

        if isinstance(title, str) and title.strip():
            return title.strip()
        return None

    @classmethod
    def _slugify_filename_part(cls, text: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
        if not slug:
            return "codex-thread"
        return slug[:80]

    @classmethod
    def build_output_base_name(cls, session_id: str, output_dir: str):
        thread_title = cls._lookup_thread_title(session_id)
        if thread_title:
            safe_title = cls._slugify_filename_part(thread_title)
            return os.path.join(output_dir, f"{safe_title}-{session_id}")
        return os.path.join(output_dir, session_id)

    def _parse_records(self) -> List[Dict]:
        records: List[Dict] = []
        for raw_line in self.json_data.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                records.append(obj)
        return records

    def _extract_session_meta(self, records: List[Dict]) -> Dict:
        for record in records:
            if record.get("type") == "session_meta":
                payload = record.get("payload")
                if isinstance(payload, dict):
                    return payload
        return {}

    def _extract_text(self, content_items) -> str:
        if not isinstance(content_items, list):
            return ""

        chunks: List[str] = []
        for item in content_items:
            if not isinstance(item, dict):
                continue
            if item.get("type") in {"input_text", "output_text"}:
                text = item.get("text")
                if isinstance(text, str) and text:
                    chunks.append(text)

        if not chunks:
            return ""

        text = "\n\n".join(chunks)
        return text.replace("\r\n", "\n").replace("\r", "\n")

    def _is_bootstrap_or_control(self, role: str, text: str) -> bool:
        if role != "user":
            return False

        stripped = text.strip()
        if not stripped:
            return True

        if stripped.startswith("# AGENTS.md instructions for"):
            return True
        if "<environment_context>" in stripped:
            return True
        if stripped.startswith("<turn_aborted>") and stripped.endswith("</turn_aborted>"):
            return True
        if any(stripped.startswith(prefix) for prefix in self._CONTROL_PREFIXES):
            return True

        return False

    def _clean_user_text(self, text: str) -> str:
        """Remove known IDE context wrappers and keep only the actual request text."""
        stripped = text.lstrip()
        if not stripped.startswith(self._IDE_CONTEXT_PREFIX):
            return text

        marker_index = stripped.find(self._IDE_REQUEST_MARKER)
        if marker_index < 0:
            return text

        request_text = stripped[marker_index + len(self._IDE_REQUEST_MARKER):].lstrip("\n")
        return request_text.strip() or text

    def _extract_messages(self, records: List[Dict]) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        for record in records:
            if record.get("type") != "response_item":
                continue

            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("type") != "message":
                continue

            role = payload.get("role")
            if role not in {"user", "assistant"}:
                continue

            text = self._extract_text(payload.get("content"))
            if not text:
                continue
            if role == "user":
                text = self._clean_user_text(text)
            if self._is_bootstrap_or_control(role, text):
                continue

            messages.append({"role": role, "content": text})

        return messages

    def to_markdown(self):
        records = self._parse_records()
        metadata = self._extract_session_meta(records)
        messages = self._extract_messages(records)

        model = metadata.get("model_provider") or "Codex"
        timestamp = metadata.get("timestamp") or self._format_timestamp()
        markdown = self._create_markdown_structure(model=model, timestamp=timestamp)

        session_lines: List[str] = []
        session_id = metadata.get("id")
        cwd = metadata.get("cwd")
        source = metadata.get("source")
        originator = metadata.get("originator")
        cli_version = metadata.get("cli_version")

        if session_id:
            session_lines.append(f"**Session ID:** {session_id}")
        if cwd:
            session_lines.append(f"**Working Directory:** {cwd}")
        if source:
            session_lines.append(f"**Connected Sources:** {source}")
        if originator:
            session_lines.append(f"**Originator:** {originator}")
        if cli_version:
            session_lines.append(f"**CLI Version:** {cli_version}")

        if session_lines:
            markdown = markdown.replace("\n## Conversation\n\n", "\n".join(session_lines) + "\n\n## Conversation\n\n")

        markdown += self._format_messages(messages)
        return markdown

    def to_workbench(self):
        records = self._parse_records()
        return {"messages": self._extract_messages(records)}
