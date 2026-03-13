from __future__ import annotations

import unittest

from auditoria_pdf.parsing.patient_document_extractors import CrcHighlightedPatientDocumentExtractor


class CrcHighlightedPatientDocumentExtractorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = CrcHighlightedPatientDocumentExtractor()

    def test_extracts_when_number_appears_before_anchor(self) -> None:
        text = """
        22797044
        Numero de Documento
        """
        self.assertEqual(self.extractor.extract(text), "22797044")

    def test_ignores_noise_and_prefers_valid_document_number(self) -> None:
        text = """
        4
        45472786
        Numero
        Numero de Documento:
        I
        """
        self.assertEqual(self.extractor.extract(text), "45472786")

    def test_prefers_longer_valid_number_over_short_false_positive(self) -> None:
        text = """
        Numero de Documento
        927986
        39279861
        """
        self.assertEqual(self.extractor.extract(text), "39279861")


if __name__ == "__main__":
    unittest.main()
