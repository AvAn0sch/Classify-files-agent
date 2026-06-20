"""Pydantic models for configuration validation — OpenAI-compatible standard."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider configuration using OpenAI-compatible API standard.

    Works with OpenAI, DeepSeek, Qwen, vLLM, Ollama, and any other
    provider that implements the OpenAI chat/completions API format.
    """

    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible API endpoint. Change to use other providers.",
    )
    api_key: str = Field(
        default="",
        description="API key. Use ${OPENAI_API_KEY} in config.yaml.",
    )
    model: str = Field(
        default="gpt-4o",
        description="Model name (e.g., gpt-4o, deepseek-chat, qwen-max).",
    )
    max_tokens: int = Field(default=16000, ge=1, le=128000)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class ApiKeys(BaseModel):
    """API key configuration. Values resolved from environment variables."""

    openai: str = ""
    tavily: str = ""


class WebSearchConfig(BaseModel):
    """Web search tool configuration."""

    enabled: bool = True
    max_results: int = Field(default=5, ge=1, le=20)
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)


class ClassificationConfig(BaseModel):
    """Classification tool configuration."""

    batch_size: int = Field(default=10, ge=1, le=50)
    max_chars_per_doc: int = Field(default=8000, ge=100, le=100000)


class ToolConfig(BaseModel):
    """All tool configurations."""

    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)


class ExtractionConfig(BaseModel):
    """Document extraction configuration."""

    pdf_library: str = "pdfplumber"
    max_chars_per_doc: int = Field(default=50000, ge=100, le=500000)
    supported_extensions: list[str] = Field(
        default_factory=lambda: [".docx", ".pptx", ".pdf"]
    )


class AgentConfig(BaseModel):
    """Agent runtime behavior configuration."""

    max_iterations: int = Field(default=20, ge=1, le=100)
    verbose: bool = False
    stream_output: bool = True


class AppConfig(BaseModel):
    """Top-level application configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    api_keys: ApiKeys = Field(default_factory=ApiKeys)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
