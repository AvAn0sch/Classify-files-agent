# create-agent

[English](README.md) | **简体中文**

智能文档处理智能体 — 分类、搜索、回答你的文档问题。

## 功能特性

- **📄 文档分类** — 使用 Claude AI 将 Word (.docx)、PowerPoint (.pptx) 和 PDF 文件按用户自定义类别进行分类，自动创建分类文件夹并移动文件。
- **🔍 联网搜索** — 通过 Tavily API 搜索网页，获取 AI 综合整理后的答案。
- **💬 文档问答** — 对文档内容提问，获取带源文件引用的答案。
- **🤖 智能体架构** — 完整的工具调用循环，包含上下文工程、提示词缓存和结构化输出。

## 安装

```bash
# 克隆并安装
cd Create-agent
pip install -e .

# 或开发模式安装
pip install -e ".[dev]"
```

## 配置

1. 复制示例配置：
   ```bash
   cp config.example.yaml config.yaml
   ```

2. 设置 API 密钥为环境变量：
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   export TAVILY_API_KEY="tvly-..."
   ```

3.（可选）编辑 `config.yaml` 自定义模型、批处理大小等。

配置加载优先级：
- 显式指定 `--config` 路径
- `./config.yaml`（当前目录）
- `~/.create-agent/config.yaml`

## 使用方法

### 文档分类

```bash
create-agent classify --folder ./documents --categories "合同,发票,报告"
```

执行流程：
1. 扫描文件夹中的 .docx、.pptx、.pdf 文件
2. 提取每个文档的文本内容
3. 使用 Claude 对每个文档进行分类
4. 创建分类子文件夹并移动文件
5. 显示分类结果汇总表

### 联网搜索

```bash
create-agent search --query "AI 法规最新进展"
create-agent search --query "Python 异步最佳实践" --max-results 3
```

### 文档提问

```bash
create-agent ask --folder ./reports --question "Q4 营收是多少？"
create-agent ask --folder ./contracts --question "哪些合同将在 2026 年到期？"
```

### 交互式对话

```bash
create-agent chat
```

与智能体自然对话 —— 它可以按需进行分类、搜索和问答。

### 详细输出模式

```bash
create-agent --verbose classify --folder ./docs --categories "法务,人事"
```

## 项目结构

```
src/create_agent/
├── main.py              # CLI 入口（click）
├── agent/
│   ├── core.py          # Agent 循环：LLM ↔ 工具编排
│   ├── conversation.py  # 对话历史管理
│   └── prompts.py       # 系统提示词构建
├── tools/
│   ├── base.py          # 抽象基类 BaseTool、ToolResult
│   ├── registry.py      # 工具注册与查找
│   ├── file_scanner.py  # 扫描文件夹发现文档
│   ├── text_extractor.py # 提取文档文本
│   ├── classifier.py    # AI 驱动的文档分类
│   ├── file_organizer.py # 创建文件夹、移动文件
│   ├── web_search.py    # Tavily 联网搜索
│   └── document_qa.py   # 文档问答
├── extraction/
│   ├── dispatcher.py    # 按文件扩展名路由
│   ├── docx_extractor.py
│   ├── pptx_extractor.py
│   └── pdf_extractor.py
├── config/
│   ├── loader.py        # YAML 加载 + 环境变量解析
│   └── models.py        # Pydantic 配置模型
└── cli/
    ├── commands.py      # Click 命令定义
    └── display.py       # Rich 控制台输出
```

## 工作原理

智能体遵循 **工具调用循环**：

1. 用户提供任务 → 连同可用工具一起发送给 Claude
2. Claude 决定调用哪些工具
3. Agent 执行工具，将结果返回给 Claude
4. Claude 可能继续调用工具或给出最终答案
5. 循环直到 Claude 完成任务或达到最大迭代次数

### 工具架构

每个工具继承 `BaseTool` 并定义：
- `name` — 唯一标识符
- `description` — 工具功能及何时使用
- `input_schema` — 参数的 JSON Schema
- `execute()` — 执行工具，返回 `ToolResult`

两个工具采用 **混合模式** — 对 Agent 表现为普通工具，但内部调用 Claude API：
- `classify_documents` 使用 **结构化输出**（JSON Schema）确保格式一致
- `search_documents` 内部调用 Claude 从文档上下文中回答问题

## 运行测试

```bash
pytest tests/ -v
```

## 依赖

| 包 | 用途 |
|---|---|
| `anthropic` | Claude API 客户端 |
| `python-docx` | Word 文档提取 |
| `python-pptx` | PowerPoint 文档提取 |
| `pdfplumber` | PDF 文本提取 |
| `tavily-python` | 联网搜索 |
| `click` | CLI 框架 |
| `rich` | 终端美化输出 |
| `pydantic` | 配置校验 |
| `pyyaml` | 配置文件解析 |
