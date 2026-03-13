from __future__ import annotations

from pathlib import Path
from typing import Iterable


class UniquePdfPathCollector:
    def collect(self, pdf_paths: Iterable[Path]) -> list[Path]:
        return [Path(path) for path in dict.fromkeys(pdf_paths)]


class PdfPathValidator:
    def validate(self, pdf_path: Path) -> str | None:
        if not pdf_path.exists():
            return f"No existe archivo: {pdf_path}"
        if pdf_path.suffix.lower() != ".pdf":
            return f"Archivo no PDF ignorado: {pdf_path}"
        return None
