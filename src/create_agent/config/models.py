"""Pydantic models for configuration validation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ThinkingConfig(BaseModel):
    """Extended thinking configuration."""

    type: Literal["adaptive", "enabled", "disabled"] = "adaptive"


class OutputConfig(BaseModel):
    """Output configuration for structured output."""

    effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: Literal["anthropic"] = "anthropic"
    model: str = "claude-opus-4-8"
    max_tokens: int = Field(default=16000, ge=1, le=64000)
    thinking: ThinkingConfig = Field(default_factory=ThinkingConfig)
    output_config: OutputConfig = Field(default_factory=OutputConfig)


class ApiKeys(BaseModel):
    """API key configuration. Values are resolved from environment variables."""

    anthropic: str = ""
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
    confidence_threshold: Literal["low", "medium", "high"] = "low"
    max_chars_per_doc: int = Field(default=8000, ge=100, le=100000)


class ToolConfig(BaseModel):
    """All tool configurations."""

    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)


class ExtractionConfig(BaseModel):
    """Document extraction configuration."""

    pdf_library: Literal["pdfplumber", "pymupdf"] = "pdfplumber"
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
