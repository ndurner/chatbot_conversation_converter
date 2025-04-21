"""Chatbot Conversation Converter

This module converts chat conversations between different formats including
OpenAI Playground JSON, Workbench format, and Markdown.
"""

import json
import sys
import os
import argparse
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
        """Format a single message consistently"""
        if not content:
            return ""
        return f"**{role}**: {content}\n\n---\n\n"

    def _format_messages(self, messages):
        """Format all messages and handle the final separator"""
        markdown = ""
        for message in messages:
            markdown += self._format_message(message["role"], message.get("content", ""))
        return markdown.rstrip("---\n\n") + "\n"

    @abstractmethod
    def to_markdown(self):
        """Convert the chat data to markdown format"""
        pass

    @abstractmethod
    def to_workbench(self):
        """Convert the chat data to workbench format"""
        pass

class PlaygroundFormatHandler(ChatFormatHandler):
    """Handler for OpenAI Playground JSON format"""

    @classmethod
    def can_handle(cls, json_data):
        return "input" in json_data

    def to_markdown(self):
        model = self.json_data.get("model", "unknown")        
        markdown = self._create_markdown_structure(model)
        messages = self._convert_to_messages(self.json_data.get("input", []))
        markdown += self._format_messages(messages)
        return markdown

    def _convert_to_messages(self, input_messages):
        """Convert playground format messages to standard format"""
        messages = []
        for message in input_messages:
            role = message.get("role")
            content = message.get("content", [])
            
            if role == "user":
                text = next((item.get("text") for item in content if item.get("type") == "input_text"), "")
                if text:
                    messages.append({"role": "user", "content": text})
            elif role == "assistant":
                text = next((item.get("text") for item in content if item.get("type") == "output_text"), "")
                if text:
                    messages.append({"role": "assistant", "content": text})
        return messages

    def to_workbench(self):
        return {"messages": self._convert_to_messages(self.json_data.get("input", []))}

class WorkbenchFormatHandler(ChatFormatHandler):
    """Handler for Workbench format (previously oai_chat)"""

    @classmethod
    def can_handle(cls, json_data):
        return "messages" in json_data

    def to_markdown(self):
        markdown = self._create_markdown_structure()
        markdown += self._format_messages(self.json_data["messages"])
        return markdown

    def to_workbench(self):
        return self.json_data

def detect_format(json_data, file_timestamp=None):
    """Automatically detect the format of the input JSON"""
    handlers = [PlaygroundFormatHandler, WorkbenchFormatHandler]
    for handler_class in handlers:
        if handler_class.can_handle(json_data):
            return handler_class(json_data, file_timestamp)
    raise ValueError("Unsupported chat format")

def convert_format(json_data, output_format, file_timestamp=None):
    """Convert the input JSON to the specified output format"""
    handler = detect_format(json_data, file_timestamp)
    
    if output_format == "markdown":
        return handler.to_markdown()
    elif output_format == "workbench":
        return handler.to_workbench()
    else:
        raise ValueError(f"Unsupported output format: {output_format}")

def main():
    parser = argparse.ArgumentParser(description='Convert chat JSON to different formats')
    parser.add_argument('input_file', help='Input JSON file')
    parser.add_argument('--format', choices=['markdown', 'workbench'], default='markdown',
                      help='Output format (markdown or workbench)')
    args = parser.parse_args()

    try:
        # Get file creation time
        file_timestamp = datetime.fromtimestamp(os.path.getctime(args.input_file))
        
        with open(args.input_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)
        
        # Convert the format
        output_content = convert_format(json_data, args.format, file_timestamp)
        
        # Generate output filename with appropriate extension
        base_name = os.path.splitext(args.input_file)[0]
        if args.format == 'markdown':
            output_file = f"{base_name}.md"
            final_output = output_content
        else:  # workbench
            output_file = f"{base_name}_converted.json"
            final_output = json.dumps(output_content, indent=2)
        
        # Write the output to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_output)
        
        print(f"Successfully converted to {output_file}")
        
    except json.JSONDecodeError:
        print("Error: Invalid JSON input", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File {args.input_file} not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()