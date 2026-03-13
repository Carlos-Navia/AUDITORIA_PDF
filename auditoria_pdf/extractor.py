from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import unicodedata

from PIL import Image
from pypdf import PdfReader
import pytesseract
from pytesseract import TesseractNotFoundError

from auditoria_pdf.mupdf_runtime import configure_mupdf_logging

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None
else:
    configure_mupdf_logging(fitz)


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
    OCR_CONTEXT_ANCHORS = (
        "documento",
        "identific",
        "afili",
        "regimen",
        "tipo usuario",
        "paciente",
        "nombres",
        "numero",
        "coosalud",
        "sanitas",
        "cedula",
        "subsidiado",
    )
    OCR_ROTATION_ANGLES = (90, 180, 270)
    MIN_OCR_IMAGE_BYTES = 30_000

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
        ocr_psm: int = 6,
        force_render_fallback: bool = False,
    ) -> str:
        reader = PdfReader(str(pdf_path))
        render_doc = None
        render_doc_attempted = False
        chunks: list[str] = []

        try:
            for page_index, page in enumerate(reader.pages):
                if max_pages is not None and page_index >= max_pages:
                    break

                native_text = (page.extract_text() or "").strip()
                image_ocr_text = self._ocr_page_images(page, ocr_psm=ocr_psm)
                merged_text = self._merge_texts(native_text, image_ocr_text)

                if (
                    allow_render_fallback
                    and (
                        force_render_fallback
                        or self._should_use_render_ocr(merged_text)
                    )
                ):
                    if render_doc is None and not render_doc_attempted:
                        render_doc = self._open_render_doc(pdf_path)
                        render_doc_attempted = True
                    if render_doc is not None:
                        render_ocr_text = self._ocr_rendered_page(
                            render_doc,
                            page_index,
                            ocr_psm=ocr_psm,
                        )
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

    def _ocr_page_images(self, page, ocr_psm: int = 6) -> str:
        images = list(page.images)
        if not images:
            return ""

        large_images = [
            image_file
            for image_file in images
            if len(image_file.data) >= self.MIN_OCR_IMAGE_BYTES
        ]

        ocr_blocks = self._ocr_image_collection(large_images, ocr_psm=ocr_psm)
        if ocr_blocks:
            return "\n".join(ocr_blocks)

        # Fallback to every image when large-image OCR produced nothing.
        ocr_blocks = self._ocr_image_collection(images, ocr_psm=ocr_psm)
        if not ocr_blocks:
            return ""

        return "\n".join(ocr_blocks)

    def _ocr_image_collection(self, images, ocr_psm: int = 6) -> list[str]:
        ocr_blocks: list[str] = []
        for image_file in images:
            try:
                with Image.open(BytesIO(image_file.data)) as image:
                    processed = image.convert("L")
                    text = self._ocr_with_orientation_candidates(
                        processed,
                        psm=ocr_psm,
                        always_try_rotations=ocr_psm == 3,
                    )
                    stripped = text.strip()
                    if stripped:
                        ocr_blocks.append(stripped)
            except Exception:
                # Ignore malformed image resources and continue.
                continue
        return ocr_blocks

    def _open_render_doc(self, pdf_path: Path):
        if fitz is None:
            return None
        try:
            return fitz.open(str(pdf_path))
        except Exception:
            return None

    def _ocr_rendered_page(self, render_doc, page_index: int, ocr_psm: int = 6) -> str:
        try:
            page = render_doc[page_index]
            matrix = fitz.Matrix(self.render_zoom, self.render_zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            with Image.open(BytesIO(pix.tobytes("png"))) as image:
                processed = image.convert("L")
                text = self._ocr_with_orientation_candidates(
                    processed,
                    psm=ocr_psm,
                    always_try_rotations=ocr_psm == 3,
                )
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

    def _ocr_with_orientation_candidates(
        self,
        image: Image.Image,
        psm: int,
        always_try_rotations: bool = False,
    ) -> str:
        baseline_text = self._safe_ocr(image, psm=psm).strip()
        best_text = baseline_text
        best_score = self._score_ocr_text(baseline_text)

        if not always_try_rotations and not self._needs_rotation_retry(baseline_text):
            return baseline_text

        for angle in self.OCR_ROTATION_ANGLES:
            rotated = image.rotate(angle, expand=True)
            candidate_text = self._safe_ocr(rotated, psm=psm).strip()
            candidate_score = self._score_ocr_text(candidate_text)
            if candidate_score > best_score:
                best_score = candidate_score
                best_text = candidate_text

        return best_text

    def _needs_rotation_retry(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return True
        return self._score_ocr_text(stripped) < 70

    def _score_ocr_text(self, text: str) -> int:
        stripped = text.strip()
        if not stripped:
            return 0

        normalized = self._normalize_text_for_scoring(stripped)
        anchor_hits = sum(normalized.count(anchor) for anchor in self.OCR_CONTEXT_ANCHORS)
        strong_digit_hits = len(re.findall(r"\b\d{6,12}\b", normalized))
        alpha_chars = sum(1 for char in normalized if "a" <= char <= "z")

        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        line_count = max(1, len(lines))
        short_lines = sum(1 for line in lines if len(line) <= 2)
        short_line_penalty = int((short_lines / line_count) * 60)

        score = 0
        score += anchor_hits * 18
        score += strong_digit_hits * 10
        score += min(alpha_chars, 900) // 25
        score -= short_line_penalty
        return score

    def _normalize_text_for_scoring(self, text: str) -> str:
        normalized = unicodedata.normalize("NFD", text)
        without_accents = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
        return without_accents.lower()

    def _should_use_render_ocr(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return True
        if len(stripped) < self.min_native_chars:
            return True
        if self._score_ocr_text(stripped) < 45:
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
