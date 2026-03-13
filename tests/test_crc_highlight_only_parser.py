from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auditoria_pdf.parsing.document_parsers import CrcDocumentParser
from auditoria_pdf.parsing.highlight_text_extractors import fitz


@unittest.skipIf(fitz is None, "PyMuPDF no disponible")
class CrcHighlightOnlyParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CrcDocumentParser()

    def test_extracts_crc_from_raw_text(self) -> None:
        pdf_path = self._build_pdf(
            body_text="Numero de Documento: 12345678",
            highlighted_terms=["Numero de Documento:", "12345678"],
        )
        parsed = self.parser.parse(
            source_path=pdf_path,
            raw_text="Numero de Documento: 12345678",
            prefix="CRC",
        )

        self.assertEqual(parsed.patient_document, "12345678")
        self.assertIn("12345678", parsed.raw_text)

    def test_falls_back_to_raw_text_when_no_supported_highlight_annotations(self) -> None:
        pdf_path = self._build_pdf(
            body_text="Numero de Documento: 12345678",
            highlighted_terms=[],
        )
        parsed = self.parser.parse(
            source_path=pdf_path,
            raw_text="Numero de Documento: 12345678",
            prefix="CRC",
        )

        self.assertEqual(parsed.patient_document, "12345678")
        self.assertIn("12345678", parsed.raw_text)

    def _build_pdf(self, body_text: str, highlighted_terms: list[str]) -> Path:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.close()
        pdf_path = Path(temp_file.name)

        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), body_text)

        for term in highlighted_terms:
            for rect in page.search_for(term):
                page.add_highlight_annot(rect)

        document.save(str(pdf_path))
        document.close()
        self.addCleanup(lambda: self._safe_unlink(pdf_path))
        return pdf_path

    def _safe_unlink(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except PermissionError:
            pass


if __name__ == "__main__":
    unittest.main()
