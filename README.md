# Classify-files-agent

Intelligent document processing agent — classify, search, and answer questions about your documents.

## Features

- **📄 Document Classification** — Classify Word (.docx), PowerPoint (.pptx), and PDF files into user-defined categories using Claude AI. Automatically creates category folders and moves files.
- **🔍 Web Search** — Search the web via Tavily API and get AI-synthesized answers.
- **💬 Document Q&A** — Ask questions about your documents and get answers with source references.
- **🤖 Agent Architecture** — Full tool-use loop with context engineering, prompt caching, and structured output.

## Installation

```bash
# Clone and install
cd Create-agent
pip install -e .

# Or for development
pip install -e ".[dev]"
```

## Configuration

1. Copy the example config:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Set your API keys as environment variables:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export TAVILY_API_KEY="tvly-..."
   ```

3. (Optional) Edit `config.yaml` to customize model, batch size, etc.

Configuration is loaded from (in order):
- Explicit `--config` path
- `./config.yaml` (current directory)
- `~/.create-agent/config.yaml`

## Usage

### Classify documents

```bash
create-agent classify --folder ./documents --categories "Contract,Invoice,Report"
```

This will:
1. Scan the folder for .docx, .pptx, .pdf files
2. Extract text from each document
3. Classify each document using Claude
4. Create category sub-folders and move files
5. Display a summary table

### Search the web

```bash
create-agent search --query "Latest developments in AI regulation"
create-agent search --query "Python async best practices" --max-results 3
```

### Ask about documents

```bash
create-agent ask --folder ./reports --question "What was Q4 revenue?"
create-agent ask --folder ./contracts --question "Which contracts expire in 2026?"
```

### Interactive chat

```bash
create-agent chat
```

Chat with the agent naturally — it can classify, search, and answer questions as needed.

### Verbose mode

```bash
create-agent --verbose classify --folder ./docs --categories "Legal,HR"
```

## Project Structure

```
src/create_agent/
├── main.py              # CLI entry point (click)
├── agent/
│   ├── core.py          # Agent loop: LLM ↔ Tools orchestration
│   ├── conversation.py  # Message history management
│   └── prompts.py       # System prompt builder
├── tools/
│   ├── base.py          # Abstract BaseTool, ToolResult
│   ├── registry.py      # Tool registration and lookup
│   ├── file_scanner.py  # Scan folders for documents
│   ├── text_extractor.py # Extract document text
│   ├── classifier.py    # AI-powered classification
│   ├── file_organizer.py # Create folders, move files
│   ├── web_search.py    # Tavily web search
│   └── document_qa.py   # Document question answering
├── extraction/
│   ├── dispatcher.py    # Route by file extension
│   ├── docx_extractor.py
│   ├── pptx_extractor.py
│   └── pdf_extractor.py
├── config/
│   ├── loader.py        # YAML loading + env var resolution
│   └── models.py        # Pydantic config schema
└── cli/
    ├── commands.py      # Click commands
    └── display.py       # Rich console output
```

## How It Works

The agent follows a **tool-use loop**:

1. User provides a task → sent to Claude with available tools
2. Claude decides which tool(s) to call
3. Agent executes tools, returns results to Claude
4. Claude may call more tools or provide a final answer
5. Loop continues until Claude finishes or max iterations reached

### Tool Architecture

Each tool extends `BaseTool` and defines:
- `name` — unique identifier
- `description` — what it does AND when to use it
- `input_schema` — JSON Schema for parameters
- `execute()` — runs the tool, returns `ToolResult`

Two tools use the **hybrid pattern** — they appear as normal tools to the agent but make internal Claude API calls:
- `classify_documents` uses **structured output** (JSON schema) for guaranteed format
- `search_documents` makes an internal call to answer questions from document context

## Running Tests

```bash
pytest tests/ -v
```

## Dependencies

- `anthropic` — Claude API client
- `python-docx` — Word document extraction
- `python-pptx` — PowerPoint extraction
- `pdfplumber` — PDF text extraction
- `tavily-python` — Web search
- `click` — CLI framework
- `rich` — Terminal output
- `pydantic` — Configuration validation
- `pyyaml` — Configuration parsing
