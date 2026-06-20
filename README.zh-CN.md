# Classify-files-agent

[English](README.md) | **简体中文**

智能文档处理智能体 — 分类、搜索、回答你的文档问题。

## 功能特性

- **📄 文档分类** — 使用 AI 将 Word (.docx)、PowerPoint (.pptx) 和 PDF 文件按用户自定义类别进行分类，自动创建分类文件夹并移动文件。
- **🔍 联网搜索** — 通过 Tavily API 搜索网页，获取 AI 综合整理后的答案。
- **💬 文档问答** — 对文档内容提问，获取带源文件引用的答案。
- **🤖 智能体架构** — 完整的工具调用循环，包含上下文工程和结构化输出。
- **🔌 多厂商兼容** — OpenAI 兼容 API 标准，支持 OpenAI、DeepSeek、通义千问、智谱、Ollama 等。

## 快速开始

```bash
# 1. 安装
cd Classify-files-agent
pip install -e .

# 2. 配置 — 复制并编辑 config.yaml
cp config.example.yaml config.yaml

# 3. 启动
python run.py
```

然后用自然语言输入你想做的事：
```
帮我把 ./documents 里的文件按合同、报告、发票分类
搜索最新的 AI 法规进展
Q4 营收报告里关于成本的内容是什么？
```

## 配置

编辑 `config.yaml` — 采用 OpenAI 兼容 API 标准：

```yaml
llm:
  base_url: https://api.deepseek.com/v1   # 替换为你的服务商
  api_key: sk-...                          # API 密钥
  model: deepseek-chat
  max_tokens: 16000
  temperature: 0.0

api_keys:
  tavily: tvly-...                         # 联网搜索密钥
```

### 支持的大模型厂商

| 厂商 | base_url |
|------|----------|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` |
| 月之暗面 | `https://api.moonshot.cn/v1` |
| Ollama (本地) | `http://localhost:11434/v1` |
| vLLM (本地) | `http://localhost:8000/v1` |

配置查找顺序：`--config 路径` → `./config.yaml` → 项目根目录 → `~/.create-agent/config.yaml`

## 使用方法

运行智能体，自然对话：

```
You: 帮我把 ./documents 里的文件按合同、报告、发票分类

Agent: [扫描文件夹 → 提取文本 → 分类 → 移动文件]
       分类完成：
       | 文件 | 类别 | 置信度 |
       | ...  | ...  | ...    |

You: 搜索 2026 年 AI 领域最重要的进展

Agent: [调用联网搜索 → 综合结果]
       以下是 2026 年 AI 领域的主要进展...

You: exit
```

## 项目结构

```
Classify-files-agent/
├── run.py                 # 快速启动脚本
├── config.yaml            # 你的配置文件
├── config.example.yaml    # 配置模板（带注释）
├── src/create_agent/
│   ├── main.py            # 入口文件
│   ├── agent/
│   │   ├── core.py        # Agent 循环：LLM ↔ 工具编排
│   │   ├── conversation.py
│   │   └── prompts.py     # 系统提示词构建
│   ├── tools/
│   │   ├── base.py        # 抽象基类 BaseTool
│   │   ├── registry.py    # 工具注册中心
│   │   ├── file_scanner.py
│   │   ├── text_extractor.py
│   │   ├── classifier.py  # AI 分类（结构化输出）
│   │   ├── file_organizer.py
│   │   ├── web_search.py  # Tavily 联网搜索
│   │   └── document_qa.py # 文档问答
│   ├── extraction/
│   │   ├── dispatcher.py
│   │   ├── docx_extractor.py
│   │   ├── pptx_extractor.py
│   │   └── pdf_extractor.py
│   ├── config/
│   │   ├── loader.py
│   │   └── models.py
│   └── cli/
│       ├── commands.py    # Agent 初始化 + 对话循环
│       └── display.py     # Rich 终端输出
└── tests/
```

## 工作原理

智能体遵循 **工具调用循环**：

1. 用户发送消息 → 连同可用工具一起发送给 LLM
2. LLM 决定直接回复还是调用工具
3. Agent 执行工具，将结果返回给 LLM
4. 循环直到 LLM 给出最终答案

### 工具架构

每个工具继承 `BaseTool` 并定义 `name`、`description`、`input_schema` 和 `execute()`。

两个工具采用 **混合模式** — 对 Agent 表现为普通工具，但内部调用 LLM API：
- `classify_documents` 使用 **结构化输出**（JSON Schema）确保格式一致
- `search_documents` 内部调用 LLM 从文档上下文中回答问题

## 运行测试

```bash
pytest tests/ -v
```

## 依赖

| 包 | 用途 |
|---|---|
| `openai` | OpenAI 兼容 API 客户端 |
| `python-docx` | Word 文档提取 |
| `python-pptx` | PowerPoint 文档提取 |
| `pdfplumber` | PDF 文本提取 |
| `tavily-python` | 联网搜索 |
| `rich` | 终端美化输出 |
| `pydantic` | 配置校验 |
| `pyyaml` | 配置文件解析 |
