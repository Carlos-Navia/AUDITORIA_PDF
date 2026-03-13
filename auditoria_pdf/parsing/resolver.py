from __future__ import annotations

from dataclasses import dataclass

from auditoria_pdf.domain import DocumentType
from auditoria_pdf.parsing.document_parsers import (
    AdditionalDocumentParser,
    BaseDocumentParser,
    CrcDocumentParser,
    FevDocumentParser,
    HaoDocumentParser,
    HevDocumentParser,
    PdeDocumentParser,
    PdxDocumentParser,
)


@dataclass(slots=True)
class PrefixAwareDocumentParserResolver:
    prefix_parsers: dict[str, BaseDocumentParser]
    type_parsers: dict[DocumentType, BaseDocumentParser]

    def resolve(self, document_type: DocumentType, prefix: str) -> BaseDocumentParser | None:
        normalized_prefix = prefix.upper()
        parser = self.prefix_parsers.get(normalized_prefix)
        if parser:
            return parser
        return self.type_parsers.get(document_type)


def build_default_parser_registry() -> dict[DocumentType, BaseDocumentParser]:
    return {
        DocumentType.FACTURA: FevDocumentParser(),
        DocumentType.AUTORIZACION: PdeDocumentParser(),
        DocumentType.SOPORTE: CrcDocumentParser(),
        DocumentType.VALIDADOR: HevDocumentParser(),
        DocumentType.ADICIONAL: AdditionalDocumentParser(),
    }


def build_default_parser_resolver() -> PrefixAwareDocumentParserResolver:
    type_parsers = build_default_parser_registry()
    prefix_parsers: dict[str, BaseDocumentParser] = {
        "FEV": type_parsers[DocumentType.FACTURA],
        "PDE": type_parsers[DocumentType.AUTORIZACION],
        "CRC": type_parsers[DocumentType.SOPORTE],
        "HEV": type_parsers[DocumentType.VALIDADOR],
        "PDX": PdxDocumentParser(),
        "HAO": HaoDocumentParser(),
    }
    return PrefixAwareDocumentParserResolver(
        prefix_parsers=prefix_parsers,
        type_parsers=type_parsers,
    )
