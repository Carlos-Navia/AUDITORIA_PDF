from __future__ import annotations

from datetime import datetime
from pathlib import Path
import unittest

from auditoria_pdf.domain import AuditContext, AuditReport, DocumentType, ParsedDocument, RuleResult
from auditoria_pdf.excel_exporter import AuditExcelExporter


def _build_document(
    doc_type: DocumentType,
    prefix: str,
    source_name: str,
    *,
    patient_document: str,
    regimen: str | None,
) -> ParsedDocument:
    return ParsedDocument(
        doc_type=doc_type,
        source_path=Path(source_name),
        raw_text="",
        prefix=prefix,
        patient_document=patient_document,
        regimen=regimen,
    )


class AuditExcelExporterTest(unittest.TestCase):
    def test_exports_regimen_detectado_from_optional_pde_document(self) -> None:
        factura = _build_document(
            DocumentType.FACTURA,
            "FEV",
            "FEV_demo.pdf",
            patient_document="12345678",
            regimen="SUBSIDIADO",
        )
        autorizacion = _build_document(
            DocumentType.AUTORIZACION,
            "PDE",
            "PDE_demo.pdf",
            patient_document="12345678",
            regimen="CONTRIBUTIVO",
        )
        report = AuditReport(
            generated_at=datetime(2026, 3, 13, 10, 0, 0),
            context=AuditContext(
                mandatory_documents={DocumentType.FACTURA: factura},
                additional_documents=[autorizacion],
                total_input_pdfs=2,
                min_pdfs=2,
                max_pdfs=6,
            ),
            rule_results=[
                RuleResult(
                    rule_id="R3_REGIMEN_FEV_VS_PDE",
                    description="",
                    passed=False,
                    expected="CONTRIBUTIVO",
                    actual="SUBSIDIADO",
                    details=["Regimen inconsistente entre FEV y PDE."],
                )
            ],
            errors=[],
        )

        rows = AuditExcelExporter()._build_rows(report, folder_label="demo")

        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["regimen_detectado"] == "CONTRIBUTIVO" for row in rows))
        self.assertTrue(all(row["estado_regimen"] == "NO_COINCIDE" for row in rows))


if __name__ == "__main__":
    unittest.main()
