from __future__ import annotations

from typing import Any

from auditoria_pdf.parsing.common import extract_first_match
from auditoria_pdf.parsing.contracts import MetadataExtractorContract


class EmptyMetadataExtractor(MetadataExtractorContract):
    def extract(self, text: str) -> dict[str, Any]:
        return {}


class FevMetadataExtractor(MetadataExtractorContract):
    def extract(self, text: str) -> dict[str, Any]:
        numero_autorizacion = extract_first_match(
            [r"N[UUM]MERO\s+AUTORIZA\.?\s*([A-Z0-9\-]+)"],
            text,
        )
        return {"numero_autorizacion": numero_autorizacion}


class PdeMetadataExtractor(MetadataExtractorContract):
    def extract(self, text: str) -> dict[str, Any]:
        numero_autorizacion = extract_first_match(
            [r"N\W*AUTORIZACI\w*N:\s*(?:\(POS\)\s*)?([A-Z0-9\-]+)"],
            text,
        )
        return {"numero_autorizacion": numero_autorizacion}


class CrcMetadataExtractor(EmptyMetadataExtractor):
    pass


class HevMetadataExtractor(EmptyMetadataExtractor):
    pass


class PdxMetadataExtractor(EmptyMetadataExtractor):
    pass


class HaoMetadataExtractor(EmptyMetadataExtractor):
    pass


class AdditionalMetadataExtractor(EmptyMetadataExtractor):
    pass
