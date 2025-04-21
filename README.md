# Chatbot Conversation Converter

A Python utility that converts chat conversations between different formats, including OpenAI Playground JSON, Nils' Workbench format¹ and Markdown.

## Features

- Convert OpenAI Playground JSON format to Markdown
- Convert OpenAI Playground JSON to Nils' Workbench format¹
- Convert Workbench format to Markdown
- Automatic format detection
- Command-line interface

## Installation

Clone this repository and ensure you have Python 3.x installed.

## Usage

```bash
python json_to_markdown.py input_file [--format {markdown,workbench}]
```

### Arguments

- `input_file`: Path to the input JSON file containing the chat conversation
- `--format`: Output format (optional)
  - `markdown` (default): Converts to Markdown format
  - `workbench`: Converts to Workbench JSON format

### Example

```bash
python json_to_markdown.py sample_chat.json
```

This will create a new file with the same base name and appropriate extension (`.md` for markdown or `_converted.json` for workbench format).

## Supported Formats

- OpenAI Prompts Playground Format
- Workbench Format¹

## Output

### Markdown Output
Creates a formatted markdown file with:
- Chat transcript title
- Messages clearly labeled with roles
- Model information (for Playground format)

### Workbench Output
Creates a JSON file in the Workbench format with:
- Simplified message structure
- Preserved conversation flow

## Error Handling

The tool includes error handling for:
- Invalid JSON input
- File not found
- Unsupported chat formats
- UTF-8 encoding issues

## References

¹ Nils' Workbench format refers to the conversation format used in:
  - [OpenAI Chat](https://github.com/ndurner/oai_chat)
  - [Amazon Bedrock Chat](https://github.com/ndurner/amz_bedrock_chat)