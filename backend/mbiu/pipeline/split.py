"""Split parsed templates with the existing MB-03 clause segmenter."""

from mbiu.documents.segment import segment_text
from mbiu.pipeline.models import ParsedDocument, StorageMetadata, TemplateClause


def split_document(
    parsed: ParsedDocument,
    metadata: StorageMetadata,
    *,
    document_sha256: str,
) -> list[TemplateClause]:
    """Produce clean, numbered template clauses from parsed document text.

    Args:
        parsed: Structured text emitted by the parser.
        metadata: Source and licence metadata copied onto every clause.
        document_sha256: Content hash of the stored raw template.

    Returns:
        Numbered clauses in document order, with empty text removed.
    """
    segmented = segment_text(parsed.text, page_count=max(1, parsed.page_count))
    clauses: list[TemplateClause] = []
    for clause in segmented.clauses:
        text = clause.text.strip()
        if not text:
            continue
        title = clause.title.strip() if clause.title else None
        clauses.append(
            TemplateClause(
                clause_id=clause.clause_id,
                section=clause.section,
                title=title or None,
                text=text,
                pages=list(clause.pages),
                source_url=metadata.source_url,
                contract_type=metadata.contract_type,
                jurisdiction=metadata.jurisdiction,
                licence=metadata.licence,
                reviewing_body=metadata.reviewing_body,
                template_version=metadata.template_version,
                document_sha256=document_sha256,
            )
        )
    return clauses
