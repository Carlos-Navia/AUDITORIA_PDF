from __future__ import annotations

import unittest
from pathlib import Path

from auditoria_pdf.audit.hev_patient_document_resolver import HevPatientDocumentResolver
from auditoria_pdf.domain import DocumentType, ParsedDocument


def _parsed_document(
    *,
    doc_type: DocumentType,
    prefix: str,
    patient_document: str | None,
    raw_text: str = "",
    source_name: str = "sample.pdf",
) -> ParsedDocument:
    return ParsedDocument(
        doc_type=doc_type,
        source_path=Path(source_name),
        raw_text=raw_text,
        prefix=prefix,
        patient_document=patient_document,
    )


class HevPatientDocumentResolverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = HevPatientDocumentResolver()
        self.reference_document = "26947045"
        self.fev = _parsed_document(
            doc_type=DocumentType.FACTURA,
            prefix="FEV",
            patient_document=self.reference_document,
            source_name="FEV_901011395_case.pdf",
        )

    def test_backfills_when_hev_document_is_missing(self) -> None:
        hev = _parsed_document(
            doc_type=DocumentType.VALIDADOR,
            prefix="HEV",
            patient_document=None,
            source_name="HEV_901011395_case.pdf",
        )

        self.resolver.reconcile(
            mandatory_documents={DocumentType.FACTURA: self.fev, DocumentType.VALIDADOR: hev},
            additional_documents=[],
        )

        self.assertEqual(hev.patient_document, self.reference_document)
        self.assertEqual(
            hev.metadata.get("patient_document_source"),
            "FEV_REFERENCE_FALLBACK_HEV",
        )

    def test_backfills_when_hev_document_length_differs_from_reference(self) -> None:
        hev = _parsed_document(
            doc_type=DocumentType.VALIDADOR,
            prefix="HEV",
            patient_document="335232",
            raw_text="Tipo de Identificacion: CC Numero de identificacion 335232",
            source_name="HEV_901011395_case.pdf",
        )

        self.resolver.reconcile(
            mandatory_documents={DocumentType.FACTURA: self.fev, DocumentType.VALIDADOR: hev},
            additional_documents=[],
        )

        self.assertEqual(hev.patient_document, self.reference_document)
        self.assertEqual(hev.metadata.get("patient_document_original"), "335232")

    def test_backfills_when_hev_document_has_small_hamming_distance(self) -> None:
        hev = _parsed_document(
            doc_type=DocumentType.VALIDADOR,
            prefix="HEV",
            patient_document="22947045",
            raw_text="Tipo de Identificacion: CC Numero de identificacion 22947045",
            source_name="HEV_901011395_case.pdf",
        )

        self.resolver.reconcile(
            mandatory_documents={DocumentType.FACTURA: self.fev, DocumentType.VALIDADOR: hev},
            additional_documents=[],
        )

        self.assertEqual(hev.patient_document, self.reference_document)
        self.assertEqual(hev.metadata.get("patient_document_original"), "22947045")

    def test_keeps_hev_document_when_mismatch_is_strong_and_high_confidence(self) -> None:
        hev = _parsed_document(
            doc_type=DocumentType.VALIDADOR,
            prefix="HEV",
            patient_document="12345678",
            raw_text="Tipo de Identificacion: CC Numero de identificacion 12345678",
            source_name="HEV_901011395_case.pdf",
        )

        self.resolver.reconcile(
            mandatory_documents={DocumentType.FACTURA: self.fev, DocumentType.VALIDADOR: hev},
            additional_documents=[],
        )

        self.assertEqual(hev.patient_document, "12345678")
        self.assertIsNone(hev.metadata.get("patient_document_source"))

    def test_does_not_touch_non_hev_documents(self) -> None:
        crc = _parsed_document(
            doc_type=DocumentType.SOPORTE,
            prefix="CRC",
            patient_document=None,
            source_name="CRC_901011395_case.pdf",
        )

        self.resolver.reconcile(
            mandatory_documents={DocumentType.FACTURA: self.fev, DocumentType.SOPORTE: crc},
            additional_documents=[],
        )

        self.assertIsNone(crc.patient_document)


if __name__ == "__main__":
    unittest.main()
