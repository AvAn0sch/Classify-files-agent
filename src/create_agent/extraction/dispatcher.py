"""Document extraction dispatcher — routes file extension to the right extractor."""

from __future__ import annotations

from pathlib import Path


def extract_text(
    file_path: str | Path,
    supported_extensions: list[str] | None = None,
    max_chars: int = 50000,
    pdf_library: str = "pdfplumber",
) -> str:
    """Extract text from a document, dispatching by file extension.

    Args:
        file_path: Path to the document file.
        supported_extensions: List of supported extensions (e.g. ['.docx', '.pptx', '.pdf']).
                              If None, defaults to all supported.
        max_chars: Maximum characters to return (truncates if exceeded).
        pdf_library: PDF extraction library: "pdfplumber" or "pymupdf".

    Returns:
        Extracted text content, truncated to max_chars.

    Raises:
        ValueError: If the file extension is not supported.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if supported_extensions and suffix not in supported_extensions:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            f"Supported: {', '.join(supported_extensions)}"
        )

    if suffix == ".docx":
        from create_agent.extraction.docx_extractor import extract_docx_text

        text = extract_docx_text(path)

    elif suffix == ".pptx":
        from create_agent.extraction.pptx_extractor import extract_pptx_text

        text = extract_pptx_text(path)

    elif suffix == ".pdf":
        from create_agent.extraction.pdf_extractor import extract_pdf_text

        text = extract_pdf_text(path, library=pdf_library)

    else:
        raise ValueError(
            f"Unsupported file type: '{suffix}'. "
            f"Supported: .docx, .pptx, .pdf"
        )

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[... truncated at {max_chars} characters]"

    return text
