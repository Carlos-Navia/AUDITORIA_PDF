from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auditoria_pdf.domain import DocumentType


REQUIRED_TYPES = (
    DocumentType.FACTURA,
)

PREFIX_TO_TYPE: dict[str, DocumentType] = {
    "FEV": DocumentType.FACTURA,
    "PDE": DocumentType.AUTORIZACION,
    "CRC": DocumentType.SOPORTE,
    "HEV": DocumentType.VALIDADOR,
    "PDX": DocumentType.ADICIONAL,
    "HAO": DocumentType.ADICIONAL,
}


@dataclass(slots=True)
class DetectedDocument:
    source_path: Path
    doc_type: DocumentType
    prefix: str


class DocumentTypeResolver:
    def __init__(self, prefix_to_type: dict[str, DocumentType] | None = None) -> None:
        self._prefix_to_type = prefix_to_type or PREFIX_TO_TYPE

    def detect(self, pdf_path: Path) -> DetectedDocument:
        prefix = pdf_path.name.split("_", 1)[0].upper()
        doc_type = self._prefix_to_type.get(prefix, DocumentType.ADICIONAL)
        return DetectedDocument(
            source_path=pdf_path,
            doc_type=doc_type,
            prefix=prefix,
        )
