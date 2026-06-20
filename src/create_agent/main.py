"""create-agent — Intelligent document processing agent.

Run this file directly to start an interactive chat session:
    python main.py

The agent can classify documents, search the web, and answer questions
about your files through natural conversation.
"""

from __future__ import annotations

from create_agent.cli.commands import start_chat

if __name__ == "__main__":
    start_chat()
