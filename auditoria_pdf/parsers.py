from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import re

from auditoria_pdf.domain import DocumentType, ParsedDocument


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _normalize_document_number(value: str | None) -> str | None:
    if not value:
        return None
    chunks = re.findall(r"\d+", value)
    for chunk in chunks:
        if 6 <= len(chunk) <= 15:
            return chunk

    digits = "".join(chunks)
    if 6 <= len(digits) <= 15:
        return digits
    return None


def _extract_first_match(
    patterns: list[str],
    text: str,
    flags: int = re.IGNORECASE | re.MULTILINE,
) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return _normalize_whitespace(match.group(1))
    return None


def _extract_patient_document_generic(text: str) -> str | None:
    patterns = [
        r"NUMERO\s+DOCUMENTO\s*[:=\-]?\s*(\d{6,15})",
        r"N[UUM]MERO\s+DOCUMENTO\s*[:=\-]?\s*(\d{6,15})",
        r"Numero\s+de\s+Documento:\s*(\d{6,15})",
        r"Numero\s+de\s+Documento:[^\n]*(?:\r?\n[^\n]*){0,4}\r?\n\s*(\d{6,15})",
        r"identific\w*[^\d\n]*((?:\d[^\d\n]*){6,15})",
        r"N[Uu]mero\s+de\s+identificaci[oó]n\s*[:\-]?\s*(\d{6,15})",
        r"N\w*ro\s+de\s+identific\w*\s*[:\-]?\s*(\d{6,15})",
        r"identificaci[oó]n\s*[:\-]?\s*(\d{6,15})",
        r"Identificaci[oó]n:\s*[A-Z]{0,4}[-\s]*(\d{6,15})",
        r"Iden\w*:\s*[A-Z]{0,4}[-\s]*(\d{6,15})",
        r"Afiliado:\s*[A-Z]{0,4}\s*(\d{6,15})",
        r"PACIENTE[^\n]{0,100}\b(?:CC|TI|CE|RC|PA)\s+(\d{6,15})",
        r"DocumentNumber=(\d{6,15})",
        r"\b(?:CC|TI|CE|RC|PA)[\s\-\.:]+(\d{6,15})\b",
    ]
    return _extract_first_match(patterns, text)


def _extract_patient_document_type_generic(text: str) -> str | None:
    patterns = [
        r"TIPO\s+DOCUMENTO\s+([A-ZA-Za-z ]{2,40})\s+N[UUM]MERO\s+DOCUMENTO",
        r"Identificaci[oó]n:\s*([A-Z]{1,4})[-\s]*\d{6,15}",
        r"Afiliado:\s*([A-Z]{1,4})\s+\d{6,15}",
    ]
    return _extract_first_match(patterns, text)


def _normalize_regimen(value: str | None) -> str | None:
    if not value:
        return None
    token = value.upper().strip()
    if "SUBSIDI" in token:
        return "SUBSIDIADO"
    if "CONTRIBUT" in token:
        return "CONTRIBUTIVO"
    return None


def _extract_regimen_literal(text: str, anchor_patterns: list[str]) -> str | None:
    anchored = _extract_first_match(anchor_patterns, text)
    normalized = _normalize_regimen(anchored)
    if normalized:
        return normalized

    # Fallback literal: only accepted words requested by business rule.
    fallback = _extract_first_match([r"\b(SUBSIDIADO|CONTRIBUTIVO)\b"], text)
    return _normalize_regimen(fallback)


def _extract_cups_codes(text: str) -> set[str]:
    cups_codes: set[str] = set()
    candidate_pattern = re.compile(r"\b([89]\d{5})\b")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        lower = line.lower()
        has_context = any(
            token in lower
            for token in ("codigo", "código", "cups", "servicio", "consulta", "procedimiento")
        )
        if has_context:
            cups_codes.update(candidate_pattern.findall(line))
            if idx + 1 < len(lines):
                cups_codes.update(candidate_pattern.findall(lines[idx + 1]))

        if re.search(r"^\s*[89]\d{5}(?:\s*,\s*[89]\d{5})+\s*$", line):
            cups_codes.update(candidate_pattern.findall(line))

    if not cups_codes:
        # Last resort for heavily noisy OCR.
        cups_codes.update(candidate_pattern.findall(text))

    return cups_codes


class BaseDocumentParser(ABC):
    doc_type: DocumentType

    def parse(self, source_path: Path, raw_text: str, prefix: str) -> ParsedDocument:
        normalized_text = raw_text.replace("\x00", "")
        fields = self._parse_fields(normalized_text)

        return ParsedDocument(
            doc_type=self.doc_type,
            source_path=source_path,
            raw_text=normalized_text,
            prefix=prefix.upper(),
            patient_document=_normalize_document_number(fields.get("patient_document")),
            patient_document_type=fields.get("patient_document_type"),
            cups_codes=fields.get("cups_codes", set()),
            regimen=_normalize_regimen(fields.get("regimen")),
            metadata=fields.get("metadata", {}),
        )

    @abstractmethod
    def _parse_fields(self, text: str) -> dict:
        raise NotImplementedError


class FevParser(BaseDocumentParser):
    doc_type = DocumentType.FACTURA

    def _parse_fields(self, text: str) -> dict:
        patient_document = _extract_patient_document_generic(text)
        patient_document_type = _extract_patient_document_type_generic(text)
        regimen = _extract_regimen_literal(
            text,
            [r"TIPO\s+USUARIO\s+(SUBSIDIADO|CONTRIBUTIVO)"],
        )
        numero_autorizacion = _extract_first_match(
            [r"N[UUM]MERO\s+AUTORIZA\.?\s*([A-Z0-9\-]+)"],
            text,
        )

        return {
            "patient_document": patient_document,
            "patient_document_type": patient_document_type,
            "cups_codes": _extract_cups_codes(text),
            "regimen": regimen,
            "metadata": {"numero_autorizacion": numero_autorizacion},
        }


class PdeParser(BaseDocumentParser):
    doc_type = DocumentType.AUTORIZACION

    def _parse_fields(self, text: str) -> dict:
        patient_document = _extract_patient_document_generic(text)
        patient_document_type = _extract_patient_document_type_generic(text)
        regimen = _extract_regimen_literal(
            text,
            [
                r"IPS\s+Primaria:\s*(SUBSIDIADO|CONTRIBUTIVO)",
                r"R[ée]gimen\s+de\s+Afiliaci[oó]n:\s*(SUBSIDIADO|CONTRIBUTIVO)",
                r"R[ée]gimen\s*[:\-]\s*(SUBSIDIADO|CONTRIBUTIVO)",
            ],
        )
        numero_autorizacion = _extract_first_match(
            [r"N[°º]?\s*Autorizaci[oó]n:\s*(?:\(POS\)\s*)?([A-Z0-9\-]+)"],
            text,
        )

        return {
            "patient_document": patient_document,
            "patient_document_type": patient_document_type,
            "cups_codes": _extract_cups_codes(text),
            "regimen": regimen,
            "metadata": {"numero_autorizacion": numero_autorizacion},
        }


class CrcParser(BaseDocumentParser):
    doc_type = DocumentType.SOPORTE

    def _parse_fields(self, text: str) -> dict:
        return {
            "patient_document": _extract_patient_document_generic(text),
            "patient_document_type": _extract_patient_document_type_generic(text),
            "cups_codes": set(),
            "regimen": None,
            "metadata": {},
        }


class HevParser(BaseDocumentParser):
    doc_type = DocumentType.VALIDADOR

    def _parse_fields(self, text: str) -> dict:
        return {
            "patient_document": _extract_patient_document_generic(text),
            "patient_document_type": _extract_patient_document_type_generic(text),
            "cups_codes": set(),
            "regimen": None,
            "metadata": {},
        }


class AdditionalDocumentParser(BaseDocumentParser):
    doc_type = DocumentType.ADICIONAL

    def _parse_fields(self, text: str) -> dict:
        return {
            "patient_document": _extract_patient_document_generic(text),
            "patient_document_type": _extract_patient_document_type_generic(text),
            "cups_codes": set(),
            "regimen": None,
            "metadata": {},
        }


def build_default_parser_registry() -> dict[DocumentType, BaseDocumentParser]:
    return {
        DocumentType.FACTURA: FevParser(),
        DocumentType.AUTORIZACION: PdeParser(),
        DocumentType.SOPORTE: CrcParser(),
        DocumentType.VALIDADOR: HevParser(),
        DocumentType.ADICIONAL: AdditionalDocumentParser(),
    }
