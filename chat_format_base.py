"""Chat Format Base Classes

This module contains the base classes for chat format handlers used
by the chatbot conversion system.
"""

from abc import ABC, abstractmethod
from datetime import datetime

class ChatFormatHandler(ABC):
    """Abstract base class for chat format handlers"""
    
    def __init__(self, json_data, file_timestamp=None):
        self.json_data = json_data
        self.file_timestamp = file_timestamp

    @classmethod
    @abstractmethod
    def can_handle(cls, json_data):
        """Check if this handler can process the given JSON data"""
        pass

    def _format_timestamp(self):
        """Format the file timestamp consistently"""
        return self.file_timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.file_timestamp else "Unknown"

    def _create_markdown_structure(self, model="unknown", timestamp=None):
        """Create consistent Markdown document structure with headers"""
        if timestamp is None:
            timestamp = self._format_timestamp()
        markdown = f"# Chat Transcript\n\n## Session Information\n\n"
        markdown += f"**Model:** {model}\n"
        markdown += f"**Timestamp:** {timestamp}\n\n"
        markdown += "## Conversation\n\n"
        return markdown

    def _format_message(self, role, content):
        if not content:
            return ""
        return f"::: {role}\n{content.strip()}\n:::\n\n"

    def _format_messages(self, messages):
        """Format all messages and handle the final separator"""
        markdown = ""
        for message in messages:
            markdown += self._format_message(message["role"], message.get("content", ""))
        return markdown + "\n"

    @abstractmethod
    def to_markdown(self):
        """Convert the chat data to markdown format"""
        pass

    @abstractmethod
    def to_workbench(self):
        """Convert the chat data to workbench format"""
        pass