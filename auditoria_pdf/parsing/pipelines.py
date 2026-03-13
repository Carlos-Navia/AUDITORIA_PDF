from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from auditoria_pdf.parsing.contracts import (
    CupsExtractorContract,
    MetadataExtractorContract,
    PatientDocumentExtractorContract,
    PatientDocumentTypeExtractorContract,
    RegimenExtractorContract,
)


@dataclass(slots=True)
class DocumentFieldExtractionPipeline:
    patient_document_extractor: PatientDocumentExtractorContract
    patient_document_type_extractor: PatientDocumentTypeExtractorContract
    regimen_extractor: RegimenExtractorContract
    cups_extractor: CupsExtractorContract
    metadata_extractor: MetadataExtractorContract

    def extract_fields(self, text: str) -> dict[str, Any]:
        return {
            "patient_document": self.patient_document_extractor.extract(text),
            "patient_document_type": self.patient_document_type_extractor.extract(text),
            "regimen": self.regimen_extractor.extract(text),
            "cups_codes": self.cups_extractor.extract(text),
            "metadata": self.metadata_extractor.extract(text),
        }
