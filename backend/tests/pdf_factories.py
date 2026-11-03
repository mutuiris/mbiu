"""In-memory synthetic PDF factories for tests.

Strictly creates synthetic, dummy music contracts in memory using PyMuPDF.
Enforces non-negotiable invariants: never uses real contracts or writes to disk.
"""

import pymupdf


def create_synthetic_text_pdf(pages_text: list[str]) -> bytes:
    """Create a synthetic PDF in memory with specified text per page.

    Args:
        pages_text: List of text strings, one per page.

    Returns:
        Raw PDF file bytes.
    """
    doc = pymupdf.open()
    try:
        for text in pages_text:
            page = doc.new_page()
            page.insert_text((50, 72), text)
        return bytes(doc.tobytes())
    finally:
        doc.close()


def create_synthetic_scanned_pdf(page_count: int = 1) -> bytes:
    """Create a synthetic image-only/scanned PDF in memory without a text layer.

    Args:
        page_count: Number of scanned pages to generate.

    Returns:
        Raw PDF file bytes.
    """
    doc = pymupdf.open()
    try:
        for _ in range(page_count):
            page = doc.new_page()
            rect = pymupdf.Rect(50, 50, 400, 600)
            page.draw_rect(rect, color=(0.2, 0.2, 0.2), fill=(0.9, 0.9, 0.9))
        return bytes(doc.tobytes())
    finally:
        doc.close()


def create_synthetic_encrypted_pdf(
    password: str = "secret",
    text: str = "Synthetic Music Agreement",
) -> bytes:
    """Create a synthetic password-protected PDF in memory.

    Args:
        password: User password for encryption.
        text: Text to include inside the encrypted document.

    Returns:
        Raw encrypted PDF file bytes.
    """
    doc = pymupdf.open()
    try:
        page = doc.new_page()
        page.insert_text((50, 72), text)
        perm_acc = int(getattr(pymupdf, "PDF_PERM_ACCESSIBILITY", 0))
        perm_print = int(getattr(pymupdf, "PDF_PERM_PRINT", 0))
        perm = perm_acc | perm_print
        enc_aes = int(getattr(pymupdf, "PDF_ENCRYPT_AES_256", 4))
        return bytes(
            doc.tobytes(
                encryption=enc_aes,
                owner_pw="owner_pass",
                user_pw=password,
                permissions=perm,
            )
        )
    finally:
        doc.close()


def create_synthetic_multipage_pdf(
    page_count: int,
    text_prefix: str = "Clause Section",
) -> bytes:
    """Create a multi-page synthetic PDF in memory.

    Args:
        page_count: Number of pages to create.
        text_prefix: Prefix string for page body text.

    Returns:
        Raw PDF file bytes.
    """
    pages = [f"{text_prefix} on page {i + 1}\nSynthetic terms here." for i in range(page_count)]
    return create_synthetic_text_pdf(pages)
