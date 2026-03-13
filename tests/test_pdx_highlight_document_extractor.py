from __future__ import annotations

import unittest

from auditoria_pdf.parsing.patient_document_extractors import (
    PdxHighlightedPatientDocumentExtractor,
    PdxHybridPatientDocumentExtractor,
)


class PdxHighlightedPatientDocumentExtractorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = PdxHighlightedPatientDocumentExtractor()

    def test_extracts_number_when_identification_and_cc_are_split_lines(self) -> None:
        text = """
        Identificacion
        CC
        33221123
        """
        self.assertEqual(self.extractor.extract(text), "33221123")

    def test_extracts_number_when_cc_precedes_identification(self) -> None:
        text = """
        CC
        45472786
        Identificacion
        """
        self.assertEqual(self.extractor.extract(text), "45472786")

    def test_extracts_with_ocr_noise_in_identification_word(self) -> None:
        text = """
        denficacion:
        CC
        1064109166
        """
        self.assertEqual(self.extractor.extract(text), "1064109166")

    def test_returns_none_when_no_digits(self) -> None:
        self.assertIsNone(self.extractor.extract("Identificacion CC"))

    def test_prefers_identification_table_number_over_reference_placeholder(self) -> None:
        text = """
        Edad
        Empresa
        Nombre
        Identificacion
        CANTILLO TAFUR ELOINA
        Tel.
        SALUD HORISOES IPS S A S - COOSALUD UNIDAD MOVIL
        33221123
        01/05/2025 50102185
        Examen Resultado
        *50102185*
        CC 999999999
        REFERENCIA
        """
        self.assertEqual(self.extractor.extract(text), "33221123")


class PdxHybridPatientDocumentExtractorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = PdxHybridPatientDocumentExtractor()

    def test_uses_strict_identification_line_when_available(self) -> None:
        text = """
        Nombre: ELIDA DEL SOCORRO CALDERON MENDOZA
        Identificacion: CC 43694125 Tel: 999999999 Fecha de recepcion: 19/06/2025
        CC 1001167055
        """
        self.assertEqual(self.extractor.extract(text), "43694125")


if __name__ == "__main__":
    unittest.main()
