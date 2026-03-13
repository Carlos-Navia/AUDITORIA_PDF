from __future__ import annotations

import re

from auditoria_pdf.parsing.common import (
    extract_first_match,
    extract_literal_regimen,
    is_probable_mobile_number,
    normalize_document_number,
    normalize_regimen,
    normalize_whitespace,
)
from auditoria_pdf.parsing.contracts import PatientDocumentExtractorContract


class FevInvoiceFieldExtractor:
    _PATIENT_PATTERNS: tuple[str, ...] = (
        r"PACIENTE[^\n]{0,100}\b(?:CC|TI|CE|RC|PA)\b\W{0,6}(\d[\d\.\-\s]{5,24})",
        r"PACIENTE[^\n]{0,70}?(\d[\d\.\-\s]{5,24})",
        r"TIPO\s+DOCUMENTO[^\n]{0,90}?NUMERO\s+DOCUMENTO\s*[:=\-]?\s*(\d[\d\.\-\s]{5,24})",
        r"(?:NUMERO|N[UUM]MERO)\s+DOCUMENTO\s*[:=\-]?\s*(\d[\d\.\-\s]{5,24})",
        r"IDENTIFIC(?:ACION)?\s*[:=\-]?\s*(?:CC|TI|CE|RC|PA)?[\s\-\.:]*(\d[\d\.\-\s]{5,24})",
    )
    _REGIMEN_ANCHOR_PATTERNS: tuple[str, ...] = (
        r"TIPO\s+USUARIO\s*[:=\-]?\s*(SUBSIDIADO|CONTRIBUTIVO)\b",
        r"TIPO\s+USUARIO\s*[:=\-]?\s*([A-ZA-Za-z ]{8,40})",
    )

    def __init__(
        self,
        fallback_patient_document_extractor: PatientDocumentExtractorContract | None = None,
    ) -> None:
        self._fallback_patient_document_extractor = fallback_patient_document_extractor

    def extract_patient_document(self, text: str) -> str | None:
        if not text:
            return None

        for pattern in self._PATIENT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                candidate = normalize_document_number(
                    normalize_whitespace(self._pick_match_group(match))
                )
                if candidate and not is_probable_mobile_number(candidate):
                    return candidate

        if self._fallback_patient_document_extractor is None:
            return None

        candidate = self._fallback_patient_document_extractor.extract(text)
        if candidate and not is_probable_mobile_number(candidate):
            return candidate
        return None

    def extract_regimen(self, text: str) -> str | None:
        if not text:
            return None

        for pattern in self._REGIMEN_ANCHOR_PATTERNS:
            anchored = extract_first_match([pattern], text)
            normalized = normalize_regimen(anchored)
            if normalized:
                return normalized

        return extract_literal_regimen(text, [r"\b(SUBSIDIADO|CONTRIBUTIVO)\b"])

    def _pick_match_group(self, match: re.Match[str]) -> str:
        if match.lastindex is None:
            return match.group(0)
        for index in range(1, match.lastindex + 1):
            value = match.group(index)
            if value:
                return value
        return match.group(0)
