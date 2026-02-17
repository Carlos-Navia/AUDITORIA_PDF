from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from auditoria_pdf.domain import AuditContext, AuditReport, DocumentType, ParsedDocument
from auditoria_pdf.extractor import PdfTextExtractor
from auditoria_pdf.parsers import BaseDocumentParser, build_default_parser_registry
from auditoria_pdf.rules import (
    AuditRule,
    CupsMatchRule,
    FileSetComplianceRule,
    PatientDocumentConsistencyRule,
    RegimenConsistencyRule,
)


REQUIRED_TYPES = (
    DocumentType.FACTURA,
    DocumentType.AUTORIZACION,
    DocumentType.SOPORTE,
)

PREFIX_TO_TYPE: dict[str, DocumentType] = {
    "FEV": DocumentType.FACTURA,
    "PDE": DocumentType.AUTORIZACION,
    "CRC": DocumentType.SOPORTE,
    "HEV": DocumentType.VALIDADOR,
}


def detect_document_type(pdf_path: Path) -> tuple[DocumentType, str]:
    prefix = pdf_path.name.split("_", 1)[0].upper()
    return PREFIX_TO_TYPE.get(prefix, DocumentType.ADICIONAL), prefix


class PdfAuditService:
    def __init__(
        self,
        extractor: PdfTextExtractor | None = None,
        parser_registry: dict[DocumentType, BaseDocumentParser] | None = None,
        rules: list[AuditRule] | None = None,
        min_pdfs: int = 4,
        max_pdfs: int = 6,
    ) -> None:
        self.extractor = extractor or PdfTextExtractor()
        self.parser_registry = parser_registry or build_default_parser_registry()
        self.min_pdfs = min_pdfs
        self.max_pdfs = max_pdfs
        self.rules = rules or [
            FileSetComplianceRule(),
            CupsMatchRule(),
            PatientDocumentConsistencyRule(),
            RegimenConsistencyRule(),
        ]
        self.page_limits: dict[DocumentType, int] = {
            DocumentType.FACTURA: 2,
            DocumentType.AUTORIZACION: 2,
            DocumentType.SOPORTE: 2,
            DocumentType.VALIDADOR: 3,
            DocumentType.ADICIONAL: 2,
        }
        self.render_fallback_types: set[DocumentType] = {
            DocumentType.FACTURA,
            DocumentType.AUTORIZACION,
            DocumentType.SOPORTE,
        }

    def audit(self, pdf_paths: Iterable[Path]) -> AuditReport:
        unique_paths = [Path(path) for path in dict.fromkeys(pdf_paths)]
        mandatory_documents = {}
        additional_documents = []
        errors: list[str] = []

        for path in unique_paths:
            if not path.exists():
                errors.append(f"No existe archivo: {path}")
                continue

            if path.suffix.lower() != ".pdf":
                errors.append(f"Archivo no PDF ignorado: {path}")
                continue

            document_type, prefix = detect_document_type(path)
            parser = self.parser_registry.get(document_type)
            if not parser:
                errors.append(
                    f"No hay parser configurado para tipo {document_type.value} ({path.name})."
                )
                continue

            try:
                page_limit = self.page_limits.get(document_type)
                allow_render_fallback = document_type in self.render_fallback_types
                raw_text = self.extractor.extract_text_limited(
                    path,
                    max_pages=page_limit,
                    allow_render_fallback=allow_render_fallback,
                )
                parsed = parser.parse(path, raw_text, prefix=prefix)

                if self._needs_full_retry(document_type, parsed):
                    raw_text_full = self.extractor.extract_text_limited(
                        path,
                        max_pages=None,
                        allow_render_fallback=allow_render_fallback,
                    )
                    parsed = parser.parse(path, raw_text_full, prefix=prefix)
            except Exception as exc:  # pragma: no cover
                errors.append(f"Error procesando {path.name}: {exc}")
                continue

            if document_type in REQUIRED_TYPES:
                if document_type in mandatory_documents:
                    errors.append(
                        f"Documento obligatorio duplicado ({document_type.value}): {path.name}"
                    )
                    continue
                mandatory_documents[document_type] = parsed
            else:
                additional_documents.append(parsed)

        context = AuditContext(
            mandatory_documents=mandatory_documents,
            additional_documents=additional_documents,
            total_input_pdfs=len(unique_paths),
            min_pdfs=self.min_pdfs,
            max_pdfs=self.max_pdfs,
        )
        rule_results = [rule.evaluate(context) for rule in self.rules]

        return AuditReport(
            generated_at=datetime.now(),
            context=context,
            rule_results=rule_results,
            errors=errors,
        )

    def _needs_full_retry(self, document_type: DocumentType, parsed: ParsedDocument) -> bool:
        if document_type in {DocumentType.FACTURA, DocumentType.AUTORIZACION}:
            return not parsed.patient_document or not parsed.regimen
        if document_type in {DocumentType.SOPORTE, DocumentType.VALIDADOR, DocumentType.ADICIONAL}:
            return not parsed.patient_document
        return False
