from __future__ import annotations

import re

from auditoria_pdf.domain import DocumentType, ParsedDocument
from auditoria_pdf.parsing.common import normalize_search_text


class HevPatientDocumentResolver:
    """Backfill noisy/missing HEV patient documents with FEV reference."""

    _IDENTIFICATION_TOKENS: tuple[str, ...] = (
        "IDENTIFIC",
        "DOCUMENTO",
        "CEDULA",
        "PACIENTE",
        "USUARIO",
        "AFILIADO",
    )

    def reconcile(
        self,
        mandatory_documents: dict[DocumentType, ParsedDocument],
        additional_documents: list[ParsedDocument],
    ) -> None:
        factura = mandatory_documents.get(DocumentType.FACTURA)
        reference_document = factura.patient_document if factura else None
        if not reference_document:
            return

        for parsed in [*mandatory_documents.values(), *additional_documents]:
            if parsed.prefix != "HEV":
                continue

            if not self._needs_reference_fallback(parsed, reference_document):
                continue

            original_document = parsed.patient_document
            parsed.patient_document = reference_document
            parsed.metadata["patient_document_source"] = "FEV_REFERENCE_FALLBACK_HEV"
            if original_document and original_document != reference_document:
                parsed.metadata["patient_document_original"] = original_document

    def _needs_reference_fallback(
        self,
        parsed: ParsedDocument,
        reference_document: str,
    ) -> bool:
        value = parsed.patient_document
        if not value:
            return True
        if value == reference_document:
            return False
        if len(value) != len(reference_document):
            return True

        if not self._has_strong_identification_number(parsed.raw_text):
            return True

        return self._hamming_distance(value, reference_document) <= 2

    def _has_strong_identification_number(self, text: str) -> bool:
        for line in text.splitlines()[:220]:
            normalized_line = normalize_search_text(line)
            if not any(token in normalized_line for token in self._IDENTIFICATION_TOKENS):
                continue

            compact_digits = re.sub(r"\D", "", line)
            if re.search(r"\d{7,12}", compact_digits):
                return True

        return False

    def _hamming_distance(self, left: str, right: str) -> int:
        if len(left) != len(right):
            return max(len(left), len(right))
        return sum(1 for l_char, r_char in zip(left, right) if l_char != r_char)
