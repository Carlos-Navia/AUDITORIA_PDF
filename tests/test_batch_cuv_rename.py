from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auditoria_pdf.batch import rename_cuv_file


class RenameCuvFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.addCleanup(self.temp_dir.cleanup)

    def test_renames_cuv_file_preserving_middle_tokens(self) -> None:
        source = self._create_file("CUV_901011395_FVEP1001.pdf")

        renamed = rename_cuv_file(source, "fvep1002")

        self.assertEqual(renamed.name, "CUV_901011395_FVEP1002.pdf")
        self.assertFalse(source.exists())
        self.assertTrue(renamed.exists())

    def test_renames_simple_cuv_name(self) -> None:
        source = self._create_file("CUV_FVEP1001.pdf")

        renamed = rename_cuv_file(source, " fvep-2002 ")

        self.assertEqual(renamed.name, "CUV_FVEP-2002.pdf")

    def test_rejects_non_cuv_prefix(self) -> None:
        source = self._create_file("FEV_901011395_FVEP1001.pdf")

        with self.assertRaisesRegex(ValueError, "prefijo CUV"):
            rename_cuv_file(source, "FVEP1002")

    def test_rejects_when_target_exists(self) -> None:
        source = self._create_file("CUV_901011395_FVEP1001.pdf")
        self._create_file("CUV_901011395_FVEP1002.pdf")

        with self.assertRaises(FileExistsError):
            rename_cuv_file(source, "FVEP1002")

    def test_rejects_non_pdf_file(self) -> None:
        source = self._create_file("CUV_901011395_FVEP1001.txt")

        with self.assertRaisesRegex(ValueError, "debe ser PDF"):
            rename_cuv_file(source, "FVEP1002")

    def _create_file(self, name: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4")
        return path


if __name__ == "__main__":
    unittest.main()
