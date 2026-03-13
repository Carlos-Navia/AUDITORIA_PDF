from __future__ import annotations

from pathlib import Path
import unittest

from auditoria_pdf.audit.document_processing import (
    DocumentRetryPolicy,
    PageLimitResolver,
    RenderFallbackPolicy,
    SinglePdfProcessingEngine,
)
from auditoria_pdf.domain import DocumentType
from auditoria_pdf.parsing.document_parsers import PdeDocumentParser


class StubPdfTextExtractor:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def extract_text_limited(
        self,
        pdf_path: Path,
        max_pages: int | None = None,
        allow_render_fallback: bool = True,
        ocr_psm: int = 6,
        force_render_fallback: bool = False,
    ) -> str:
        self.calls.append(
            {
                "pdf_path": pdf_path,
                "max_pages": max_pages,
                "allow_render_fallback": allow_render_fallback,
                "ocr_psm": ocr_psm,
                "force_render_fallback": force_render_fallback,
            }
        )
        if force_render_fallback:
            return "Numero de identificacion: 12345678\nRegimen: Con tri butivo"
        return "Numero de identificacion: 12345678"


class SinglePdfProcessingEngineTest(unittest.TestCase):
    def test_uses_aggressive_retry_when_pde_regimen_is_missing(self) -> None:
        extractor = StubPdfTextExtractor()
        engine = SinglePdfProcessingEngine(
            extractor=extractor,
            page_limit_resolver=PageLimitResolver({DocumentType.AUTORIZACION: 1}),
            render_fallback_policy=RenderFallbackPolicy({DocumentType.AUTORIZACION}),
            retry_policy=DocumentRetryPolicy(),
        )

        parsed = engine.process(
            source_path=Path("PDE_demo.pdf"),
            document_type=DocumentType.AUTORIZACION,
            prefix="PDE",
            parser=PdeDocumentParser(),
        )

        self.assertEqual(parsed.patient_document, "12345678")
        self.assertEqual(parsed.regimen, "CONTRIBUTIVO")
        self.assertEqual(len(extractor.calls), 3)
        self.assertTrue(extractor.calls[-1]["force_render_fallback"])
        self.assertEqual(extractor.calls[-1]["ocr_psm"], 3)


if __name__ == "__main__":
    unittest.main()
