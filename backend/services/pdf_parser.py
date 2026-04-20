import fitz  # pymupdf
import re


CHAPTER_PATTERNS = [
    r"^\s*(chapter|module|section|part|unit|lesson)\s+([a-z0-9]+)\s*:?\s*(.+)?$",
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    metadata = extract_text_with_metadata(file_bytes)
    return metadata["text"]


def extract_text_with_metadata(file_bytes: bytes) -> dict:
    """
    Extract text with page numbers and chapter detection.

    Returns:
    {
        "text": full text,
        "pages_with_metadata": [
            {
                "page": 1,
                "chapter": "Chapter 1: Introduction" or None,
                "text": "page text content..."
            },
            ...
        ],
        "chapters": ["Chapter 1: Introduction", "Chapter 2: ..."] or [],
        "total_pages": 15
    }
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    pages_with_metadata = []
    detected_chapters = []
    full_text_parts = []
    current_chapter = None

    try:
        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text("text").strip()
            page_chapter = _detect_chapter_in_text(page_text)

            if page_chapter:
                current_chapter = page_chapter
                if page_chapter not in detected_chapters:
                    detected_chapters.append(page_chapter)

            pages_with_metadata.append(
                {
                    "page": page_num,
                    "chapter": current_chapter,
                    "text": page_text,
                }
            )

            if page_text:
                full_text_parts.append(page_text)
    finally:
        doc.close()

    return {
        "text": "\n\n".join(full_text_parts).strip(),
        "pages_with_metadata": pages_with_metadata,
        "chapters": detected_chapters,
        "total_pages": len(pages_with_metadata),
    }


def _detect_chapter_in_text(page_text: str) -> str | None:
    for line in page_text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue

        for pattern in CHAPTER_PATTERNS:
            match = re.match(pattern, candidate, re.IGNORECASE)
            if match:
                label = match.group(1).capitalize()
                number = match.group(2)
                title = (match.group(3) or "").strip(" :-")

                if title:
                    return f"{label} {number}: {title}"
                return f"{label} {number}"

    return None
