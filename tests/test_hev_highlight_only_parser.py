from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auditoria_pdf.parsing.document_parsers import HevDocumentParser
from auditoria_pdf.parsing.highlight_text_extractors import fitz


@unittest.skipIf(fitz is None, "PyMuPDF no disponible")
class HevHighlightOnlyParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = HevDocumentParser()

    def test_extracts_hev_from_raw_text(self) -> None:
        pdf_path = self._build_pdf(
            body_text="Datos del paciente Identificacion: CC-12345678",
            highlighted_terms=["Identificacion: CC-12345678"],
        )
        parsed = self.parser.parse(
            source_path=pdf_path,
            raw_text="Identificacion: CC-12345678",
            prefix="HEV",
        )

        self.assertEqual(parsed.patient_document, "12345678")
        self.assertIn("12345678", parsed.raw_text)

    def test_falls_back_to_raw_text_when_no_supported_highlight_annotations(self) -> None:
        pdf_path = self._build_pdf(
            body_text="Datos del paciente Identificacion: CC-12345678",
            highlighted_terms=[],
        )
        parsed = self.parser.parse(
            source_path=pdf_path,
            raw_text="Identificacion: CC-12345678",
            prefix="HEV",
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
