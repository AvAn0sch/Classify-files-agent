# Classify-files-agent

**English** | [简体中文](README.zh-CN.md)

Intelligent document processing agent — classify, search, and answer questions about your documents.

## Features

- **📄 Document Classification** — Classify Word (.docx), PowerPoint (.pptx), and PDF files into user-defined categories using AI. Automatically creates category folders and moves files.
- **🔍 Web Search** — Search the web via Tavily API and get AI-synthesized answers.
- **💬 Document Q&A** — Ask questions about your documents and get answers with source references.
- **🤖 Agent Architecture** — Full tool-use loop with context engineering, prompt caching, and structured output.
- **🔌 Multi-Provider** — OpenAI-compatible API standard. Works with OpenAI, DeepSeek, Qwen, Zhipu, Ollama, and more.

## Quick Start

```bash
# 1. Install
cd Classify-files-agent
pip install -e .

# 2. Configure — copy and edit config.yaml
cp config.example.yaml config.yaml

# 3. Start
python run.py
```

Then just type what you want in natural language:
```
帮我把 ./documents 里的文件按合同、报告、发票分类
搜索最新的 AI 法规进展
Q4 营收报告里关于成本的内容是什么？
```

## Configuration

Edit `config.yaml` — OpenAI-compatible API standard:

```yaml
llm:
  base_url: https://api.deepseek.com/v1   # Change to your provider
  api_key: sk-...                          # Your API key
  model: deepseek-chat
  max_tokens: 16000
  temperature: 0.0

api_keys:
  tavily: tvly-...                         # For web search
```

### Supported LLM Providers

| Provider | base_url |
|----------|----------|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| Qwen (阿里云) | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Zhipu (智谱) | `https://open.bigmodel.cn/api/paas/v4` |
| Moonshot | `https://api.moonshot.cn/v1` |
| Ollama (local) | `http://localhost:11434/v1` |
| vLLM (local) | `http://localhost:8000/v1` |

Config search order: `--config path` → `./config.yaml` → project root → `~/.create-agent/config.yaml`

## Usage

Run the agent and chat naturally:

```
You: 帮我把 ./documents 里的文件按合同、报告、发票分类

Agent: [scans folder → extracts text → classifies → moves files]
       Classification complete:
       | File | Category | Confidence |
       | ...  | ...      | ...        |

You: 搜索 2026 年 AI 领域最重要的进展

Agent: [calls web_search → synthesizes results]
       Here are the key AI developments in 2026...

You: exit
```

## Project Structure

```
Classify-files-agent/
├── run.py                 # Quick launcher
├── config.yaml            # Your configuration
├── config.example.yaml    # Annotated template
├── src/create_agent/
│   ├── main.py            # Entry point
│   ├── agent/
│   │   ├── core.py        # Agent loop: LLM ↔ Tools
│   │   ├── conversation.py
│   │   └── prompts.py     # System prompt builder
│   ├── tools/
│   │   ├── base.py        # Abstract BaseTool
│   │   ├── registry.py    # Tool registration
│   │   ├── file_scanner.py
│   │   ├── text_extractor.py
│   │   ├── classifier.py  # AI classification (structured output)
│   │   ├── file_organizer.py
│   │   ├── web_search.py  # Tavily search
│   │   └── document_qa.py # Document Q&A
│   ├── extraction/
│   │   ├── dispatcher.py
│   │   ├── docx_extractor.py
│   │   ├── pptx_extractor.py
│   │   └── pdf_extractor.py
│   ├── config/
│   │   ├── loader.py
│   │   └── models.py
│   └── cli/
│       ├── commands.py    # Agent init + chat loop
│       └── display.py     # Rich terminal output
└── tests/
```

## How It Works

The agent follows a **tool-use loop**:

1. User sends a message → sent to LLM with available tools
2. LLM decides whether to respond directly or call a tool
3. Agent executes tool calls, returns results to LLM
4. Loop continues until LLM provides a final answer

### Tool Architecture

Each tool extends `BaseTool` and defines `name`, `description`, `input_schema`, and `execute()`.

Two tools use the **hybrid pattern** — they appear as normal tools to the agent but make internal LLM API calls:
- `classify_documents` uses **structured output** (JSON schema) for guaranteed format
- `search_documents` makes an internal call to answer questions from document context

## Running Tests

```bash
pytest tests/ -v
```

## Dependencies

- `openai` — OpenAI-compatible API client
- `python-docx` — Word document extraction
- `python-pptx` — PowerPoint extraction
- `pdfplumber` — PDF text extraction
- `tavily-python` — Web search
- `rich` — Terminal output
- `pydantic` — Configuration validation
- `pyyaml` — Configuration parsing
