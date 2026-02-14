# Chatbot Conversation Converter

A Python utility that converts chat conversations between different formats, including OpenAI Playground JSON, Nils' Workbench format¹ and Markdown. ChatGPT is also supported as a source.

## Features

- Convert between Chatbot data exchange formats
  - Input formats:
    - Open AI Prompts Playground
    - Nils' Workbench format¹
    - ChatGPT HTML
    - Codex session JSONL (`~/.codex/sessions/.../*.jsonl`)
  - Output formats:
    - Markdown
    - Nils' Workbench format¹
- Command-line interface

## Installation

Clone this repository and ensure you have Python 3.x installed.

## Usage

```bash
python chatbot_convert.py input_spec [--format {markdown,workbench}]
```

### Arguments

- `input_spec`: One of:
  - Path to an input file containing the chat conversation
  - OpenAI Codex
    - session/thread ID (for example `019c53b4-54d1-7753-b985-b491956970e9`)
    - thread URL (for example `codex://threads/019c53b4-54d1-7753-b985-b491956970e9`)
- `--format`: Output format (optional)
  - `markdown` (default): Converts to Markdown format
  - `workbench`: Converts to Workbench JSON format

### Example

```bash
python chatbot_convert.py sample_chat.json
```

```bash
python chatbot_convert.py 019c53b4-54d1-7753-b985-b491956970e9
```

```bash
python chatbot_convert.py codex://threads/019c53b4-54d1-7753-b985-b491956970e9
```

This will create a new file with the same base name and appropriate extension (`.md` for markdown or `_converted.json` for workbench format).
For Codex session/thread IDs (or `codex://threads/...`), output files are named using the recovered thread title when available (slugified), with the session ID appended.

## Supported Formats

- OpenAI Prompts Playground Format
- Workbench Format¹
- ChatGPT HTML (input)
- Codex session JSONL (input)

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

## Restrictions
- does not include images or file uploads from ChatGPT or Codex
- OpenAI Prompts Playground .json does not include (image) data

## References

¹ Nils' Workbench format refers to the conversation format used in:
  - [OpenAI Chat](https://github.com/ndurner/oai_chat)
  - [Amazon Bedrock Chat](https://github.com/ndurner/amz_bedrock_chat)
