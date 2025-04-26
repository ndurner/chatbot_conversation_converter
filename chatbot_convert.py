"""Chatbot Conversation Converter

This module converts chat conversations between different formats including
OpenAI Playground JSON, Workbench format, and Markdown.
"""

import json
import sys
import os
import argparse
from abc import abstractmethod
from datetime import datetime
from bs4 import BeautifulSoup

from chat_format_base import ChatFormatHandler

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
    # Import here to avoid circular import
    from chatgpt_format_handler import ChatGPTFormatHandler
    
    handlers = [
        ChatGPTFormatHandler,
        PlaygroundFormatHandler,
        WorkbenchFormatHandler
    ]

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
            raw = file.read()
        # Try JSON first; if that fails we keep the raw string
        try:
            json_data = json.loads(raw)
        except json.JSONDecodeError:
            json_data = raw      # hand the raw HTML string to the detector

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
        print("Error: Unsupported input format", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File {args.input_file} not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()