from __future__ import annotations

from auditoria_pdf.parsing.common import extract_first_match, normalize_document_type
from auditoria_pdf.parsing.contracts import PatientDocumentTypeExtractorContract


class GenericPatientDocumentTypeExtractor(PatientDocumentTypeExtractorContract):
    _PATTERNS = [
        r"TIPO\s+DOCUMENTO\s+([A-ZA-Za-z ]{2,40})\s+N[UUM]MERO\s+DOCUMENTO",
        r"TIPO\s+IDENTIFIC\w*\s*[:=\-]?\s*([A-Z]{1,4})\b",
        r"IDENTIFIC\w*\s*[:=\-]?\s*([A-Z]{1,4})[-\s]*\d{6,15}",
        r"AFILIADO\s*[:=\-]?\s*([A-Z]{1,4})\s+\d{6,15}",
    ]

    def extract(self, text: str) -> str | None:
        return normalize_document_type(extract_first_match(self._PATTERNS, text))


class DelegatingPatientDocumentTypeExtractor(PatientDocumentTypeExtractorContract):
    def __init__(
        self,
        delegate: PatientDocumentTypeExtractorContract | None = None,
    ) -> None:
        self._delegate = delegate or GenericPatientDocumentTypeExtractor()

    def extract(self, text: str) -> str | None:
        return self._delegate.extract(text)


class FevPatientDocumentTypeExtractor(DelegatingPatientDocumentTypeExtractor):
    pass


class PdePatientDocumentTypeExtractor(DelegatingPatientDocumentTypeExtractor):
    pass


class CrcPatientDocumentTypeExtractor(DelegatingPatientDocumentTypeExtractor):
    pass


class HevPatientDocumentTypeExtractor(DelegatingPatientDocumentTypeExtractor):
    pass


class PdxPatientDocumentTypeExtractor(DelegatingPatientDocumentTypeExtractor):
    pass


class HaoPatientDocumentTypeExtractor(DelegatingPatientDocumentTypeExtractor):
    pass


class AdditionalPatientDocumentTypeExtractor(DelegatingPatientDocumentTypeExtractor):
    pass
