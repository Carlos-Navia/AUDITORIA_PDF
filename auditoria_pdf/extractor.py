from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
import pytesseract
from pytesseract import TesseractNotFoundError

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None


class PdfTextExtractor:
    DEFAULT_TESSERACT_PATHS = (
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Users\Horisoes\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    )

    SIGNAL_ANCHORS = (
        "documento",
        "identific",
        "afili",
        "regimen",
        "régimen",
        "tipo usuario",
        "paciente",
        "nombres",
    )

    def __init__(
        self,
        tesseract_cmd: str | None = None,
        ocr_lang: str = "eng",
        min_native_chars: int = 40,
        render_zoom: float = 2.5,
    ) -> None:
        self.ocr_lang = ocr_lang
        self.min_native_chars = min_native_chars
        self.render_zoom = render_zoom
        self._configure_tesseract(tesseract_cmd)

    def extract_text(self, pdf_path: Path) -> str:
        return self.extract_text_limited(pdf_path)

    def extract_text_limited(
        self,
        pdf_path: Path,
        max_pages: int | None = None,
        allow_render_fallback: bool = True,
    ) -> str:
        reader = PdfReader(str(pdf_path))
        render_doc = self._open_render_doc(pdf_path)
        chunks: list[str] = []

        try:
            for page_index, page in enumerate(reader.pages):
                if max_pages is not None and page_index >= max_pages:
                    break

                native_text = (page.extract_text() or "").strip()
                image_ocr_text = self._ocr_page_images(page)
                merged_text = self._merge_texts(native_text, image_ocr_text)

                if (
                    allow_render_fallback
                    and self._should_use_render_ocr(merged_text)
                    and render_doc is not None
                ):
                    render_ocr_text = self._ocr_rendered_page(render_doc, page_index)
                    merged_text = self._merge_texts(merged_text, render_ocr_text)

                if merged_text:
                    chunks.append(merged_text)
        finally:
            if render_doc is not None:
                render_doc.close()

        return "\n".join(part for part in chunks if part).strip()

    def _configure_tesseract(self, tesseract_cmd: str | None) -> None:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            return

        for candidate in self.DEFAULT_TESSERACT_PATHS:
            if candidate.exists():
                pytesseract.pytesseract.tesseract_cmd = str(candidate)
                return

    def _ocr_page_images(self, page) -> str:
        images = list(page.images)
        if not images:
            return ""

        ocr_blocks: list[str] = []
        for image_file in images:
            try:
                with Image.open(BytesIO(image_file.data)) as image:
                    processed = image.convert("L")
                    text = self._safe_ocr(processed, psm=6)
                    stripped = text.strip()
                    if stripped:
                        ocr_blocks.append(stripped)
            except Exception:
                # Ignore malformed image resources and continue.
                continue

        return "\n".join(ocr_blocks)

    def _open_render_doc(self, pdf_path: Path):
        if fitz is None:
            return None
        try:
            return fitz.open(str(pdf_path))
        except Exception:
            return None

    def _ocr_rendered_page(self, render_doc, page_index: int) -> str:
        try:
            page = render_doc[page_index]
            matrix = fitz.Matrix(self.render_zoom, self.render_zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            with Image.open(BytesIO(pix.tobytes("png"))) as image:
                processed = image.convert("L")
                text = self._safe_ocr(processed, psm=6)
                return text.strip()
        except Exception:
            return ""

    def _safe_ocr(self, image: Image.Image, psm: int) -> str:
        try:
            return pytesseract.image_to_string(
                image,
                lang=self.ocr_lang,
                config=f"--psm {psm}",
            )
        except TesseractNotFoundError as exc:
            raise RuntimeError(
                "No se encontro Tesseract. Configura --tesseract-cmd o instala Tesseract OCR."
            ) from exc

    def _should_use_render_ocr(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return True
        if len(stripped) < self.min_native_chars:
            return True

        lower = stripped.lower()
        if any(anchor in lower for anchor in self.SIGNAL_ANCHORS):
            return False

        short_lines = sum(
            1 for line in stripped.splitlines() if 1 <= len(line.strip()) <= 2
        )
        if short_lines >= 6:
            return True

        return False

    def _merge_texts(self, first: str, second: str) -> str:
        first_clean = first.strip()
        second_clean = second.strip()
        if first_clean and second_clean:
            if first_clean == second_clean:
                return first_clean
            return f"{first_clean}\n{second_clean}"
        return first_clean or second_clean
