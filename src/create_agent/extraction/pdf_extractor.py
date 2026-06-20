"""Extract text from PDF files using pdfplumber."""

from __future__ import annotations

from pathlib import Path


def extract_pdf_text(file_path: str | Path, library: str = "pdfplumber") -> str:
    """Extract all text from a PDF file.

    Args:
        file_path: Path to the PDF file.
        library: Extraction library: "pdfplumber" (default) or "pymupdf".

    Returns:
        Extracted text content with page separators.

    Raises:
        ImportError: If the required library is not installed.
        ValueError: If the file is not a valid PDF.
    """
    path = Path(file_path)
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Not a PDF file: {path}")

    if library == "pymupdf":
        return _extract_with_pymupdf(path)
    return _extract_with_pdfplumber(path)


def _extract_with_pdfplumber(path: Path) -> str:
    """Extract PDF text using pdfplumber."""
    import pdfplumber

    parts: list[str] = []

    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                parts.append(f"[Page {page_num}]\n{text.strip()}")

    return "\n\n".join(parts)


def _extract_with_pymupdf(path: Path) -> str:
    """Extract PDF text using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    parts: list[str] = []
    doc = fitz.open(str(path))

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text and text.strip():
            parts.append(f"[Page {page_num + 1}]\n{text.strip()}")

    doc.close()
    return "\n\n".join(parts)
