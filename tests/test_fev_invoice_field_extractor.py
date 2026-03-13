from __future__ import annotations

import unittest

from auditoria_pdf.parsing.document_parsers import FevDocumentParser
from auditoria_pdf.parsing.fev_invoice_field_extractor import FevInvoiceFieldExtractor


class FevInvoiceFieldExtractorTest(unittest.TestCase):
    def test_extracts_patient_document_from_highlighted_paciente_line(self) -> None:
        text = """
        CLIENTE NIT 900226715
        PACIENTE CC 43119191 - ROMERO RUIZ LUZ MARYS
        TIPO DOCUMENTO Cedula Ciudadania
        NUMERO DOCUMENTO 43119191
        """
        extractor = FevInvoiceFieldExtractor()
        self.assertEqual(extractor.extract_patient_document(text), "43119191")

    def test_extracts_regimen_from_tipo_usuario_with_suffix(self) -> None:
        text = """
        DATOS SALUD
        TIPO USUARIO Contributivo beneficiario
        COBERTURA Plan de beneficios
        """
        extractor = FevInvoiceFieldExtractor()
        self.assertEqual(extractor.extract_regimen(text), "CONTRIBUTIVO")

    def test_fev_parser_reuses_single_extractor_instance_for_both_tasks(self) -> None:
        parser = FevDocumentParser()
        pipeline = parser._extraction_pipeline
        self.assertIs(
            pipeline.patient_document_extractor._fev_field_extractor,
            pipeline.regimen_extractor._fev_field_extractor,
        )


if __name__ == "__main__":
    unittest.main()
