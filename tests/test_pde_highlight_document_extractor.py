from __future__ import annotations

import unittest

from auditoria_pdf.parsing.patient_document_extractors import PdeHighlightedPatientDocumentExtractor


class PdeHighlightedPatientDocumentExtractorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = PdeHighlightedPatientDocumentExtractor()

    def test_extracts_document_from_plain_highlighted_number(self) -> None:
        text = """
        33221123
        CONTRIBUITVO
        """
        self.assertEqual(self.extractor.extract(text), "33221123")

    def test_prefers_identification_number_over_mobile(self) -> None:
        text = """
        Numero de identificacion:
        43692758
        Cel: 3012327124
        """
        self.assertEqual(self.extractor.extract(text), "43692758")

    def test_returns_none_when_highlight_has_no_number(self) -> None:
        self.assertIsNone(self.extractor.extract("Contributivo"))


if __name__ == "__main__":
    unittest.main()
