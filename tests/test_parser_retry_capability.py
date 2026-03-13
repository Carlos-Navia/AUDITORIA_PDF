from __future__ import annotations

import unittest

from auditoria_pdf.parsing.document_parsers import (
    CrcDocumentParser,
    FevDocumentParser,
    HevDocumentParser,
    PdeDocumentParser,
    PdxDocumentParser,
)


class ParserRetryCapabilityTest(unittest.TestCase):
    def test_all_active_parsers_keep_raw_text_retry(self) -> None:
        self.assertTrue(CrcDocumentParser().allows_raw_text_retry())
        self.assertTrue(PdeDocumentParser().allows_raw_text_retry())
        self.assertTrue(HevDocumentParser().allows_raw_text_retry())
        self.assertTrue(PdxDocumentParser().allows_raw_text_retry())
        self.assertTrue(FevDocumentParser().allows_raw_text_retry())


if __name__ == "__main__":
    unittest.main()
