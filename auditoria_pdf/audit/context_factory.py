from __future__ import annotations

from dataclasses import dataclass

from auditoria_pdf.domain import AuditContext, DocumentType, ParsedDocument


@dataclass(slots=True)
class AuditContextFactory:
    min_pdfs: int
    max_pdfs: int

    def build(
        self,
        mandatory_documents: dict[DocumentType, ParsedDocument],
        additional_documents: list[ParsedDocument],
        total_input_pdfs: int,
    ) -> AuditContext:
        return AuditContext(
            mandatory_documents=mandatory_documents,
            additional_documents=additional_documents,
            total_input_pdfs=total_input_pdfs,
            min_pdfs=self.min_pdfs,
            max_pdfs=self.max_pdfs,
        )
