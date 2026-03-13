from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
import pytesseract
from pytesseract import TesseractNotFoundError

from auditoria_pdf.mupdf_runtime import configure_mupdf_logging
from auditoria_pdf.parsing.common import normalize_whitespace

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None
else:
    configure_mupdf_logging(fitz)


class PdfHighlightTextExtractor:
    _DEFAULT_ANNOTATION_TYPES = frozenset({"Highlight"})

    def __init__(
        self,
        annotation_types: set[str] | None = None,
        allow_ocr_fallback: bool = False,
        ocr_lang: str = "eng",
        ocr_psm: int = 6,
        render_zoom: float = 3.0,
        ink_vertical_expand: float = 40.0,
    ) -> None:
        self._annotation_types = (
            frozenset(annotation_types) if annotation_types else self._DEFAULT_ANNOTATION_TYPES
        )
        self._allow_ocr_fallback = allow_ocr_fallback
        self._ocr_lang = ocr_lang
        self._ocr_psm = ocr_psm
        self._render_zoom = render_zoom
        self._ink_vertical_expand = ink_vertical_expand

    def extract(self, pdf_path: Path, max_pages: int | None = None) -> str:
        if fitz is None:
            return ""

        try:
            document = fitz.open(str(pdf_path))
        except Exception:
            return ""

        snippets: list[str] = []
        try:
            for page_index, page in enumerate(document):
                if max_pages is not None and page_index >= max_pages:
                    break

                annotation = page.first_annot
                while annotation:
                    annotation_type = self._annotation_type(annotation)
                    if annotation_type not in self._annotation_types:
                        annotation = annotation.next
                        continue

                    snippet = self._extract_annotation_text(
                        page=page,
                        annotation=annotation,
                        annotation_type=annotation_type,
                    )
                    if snippet:
                        snippets.append(snippet)

                    annotation = annotation.next
        finally:
            document.close()

        unique_snippets = list(dict.fromkeys(snippets))
        return "\n".join(unique_snippets).strip()

    def has_supported_annotations(self, pdf_path: Path, max_pages: int | None = None) -> bool:
        if fitz is None:
            return False

        try:
            document = fitz.open(str(pdf_path))
        except Exception:
            return False

        try:
            for page_index, page in enumerate(document):
                if max_pages is not None and page_index >= max_pages:
                    break
                annotation = page.first_annot
                while annotation:
                    if self._annotation_type(annotation) in self._annotation_types:
                        return True
                    annotation = annotation.next
        finally:
            document.close()

        return False

    def _annotation_type(self, annotation) -> str:
        annotation_type = annotation.type
        if isinstance(annotation_type, tuple) and len(annotation_type) > 1:
            return str(annotation_type[1])
        return str(annotation_type)

    def _extract_annotation_text(self, page, annotation, annotation_type: str) -> str:
        target_rects = self._build_annotation_rects(
            annotation=annotation,
            annotation_type=annotation_type,
        )

        blocks: list[str] = []
        if target_rects:
            for rect in target_rects:
                block = self._extract_rect_text(page, rect)
                if block:
                    blocks.append(block)
        else:
            block = self._extract_rect_text(page, annotation.rect)
            if block:
                blocks.append(block)

        if not blocks:
            return ""
        return " ".join(dict.fromkeys(blocks))

    def _build_annotation_rects(self, annotation, annotation_type: str) -> list:
        if annotation_type == "Ink":
            return [self._expand_ink_rect(annotation.rect)]

        quadrilateral_rects = self._build_quadrilateral_rects(annotation)
        if quadrilateral_rects:
            return quadrilateral_rects
        return [annotation.rect]

    def _expand_ink_rect(self, rect):
        x_padding = 8.0
        return fitz.Rect(
            max(0.0, rect.x0 - x_padding),
            max(0.0, rect.y0 - self._ink_vertical_expand),
            rect.x1 + x_padding,
            rect.y1 + 6.0,
        )

    def _build_quadrilateral_rects(self, annotation) -> list:
        vertices = annotation.vertices or []
        if not vertices:
            return []

        points = self._flatten_vertices(vertices)

        if len(points) < 4:
            return []

        rects = []
        for index in range(0, len(points), 4):
            quad = points[index : index + 4]
            if len(quad) < 4:
                continue
            xs = [point[0] for point in quad]
            ys = [point[1] for point in quad]
            rects.append(fitz.Rect(min(xs), min(ys), max(xs), max(ys)))
        return rects

    def _flatten_vertices(self, vertices) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for vertex in vertices:
            if hasattr(vertex, "x"):
                points.append((vertex.x, vertex.y))
                continue

            if isinstance(vertex, (list, tuple)):
                if len(vertex) == 2 and all(isinstance(item, (int, float)) for item in vertex):
                    points.append((float(vertex[0]), float(vertex[1])))
                    continue

                for nested in vertex:
                    if isinstance(nested, (list, tuple)) and len(nested) == 2:
                        x_value, y_value = nested
                        if isinstance(x_value, (int, float)) and isinstance(y_value, (int, float)):
                            points.append((float(x_value), float(y_value)))
        return points

    def _extract_rect_text(self, page, rect) -> str:
        try:
            words = page.get_text("words", clip=rect)
        except Exception:
            words = []

        if words:
            ordered_words = sorted(words, key=lambda item: (item[5], item[6], item[7], item[0]))
            text = " ".join(word[4] for word in ordered_words if word[4].strip())
            return normalize_whitespace(text) if text else ""

        try:
            text = page.get_text("text", clip=rect)
        except Exception:
            text = ""

        normalized_text = normalize_whitespace(text) if text else ""
        if normalized_text:
            return normalized_text

        if not self._allow_ocr_fallback:
            return ""

        return self._ocr_rect(page, rect)

    def _ocr_rect(self, page, rect) -> str:
        if fitz is None:
            return ""

        try:
            matrix = fitz.Matrix(self._render_zoom, self._render_zoom)
            pixmap = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
            with Image.open(BytesIO(pixmap.tobytes("png"))) as image:
                grayscale = image.convert("L")
                text = pytesseract.image_to_string(
                    grayscale,
                    lang=self._ocr_lang,
                    config=f"--psm {self._ocr_psm}",
                )
        except TesseractNotFoundError:
            return ""
        except Exception:
            return ""

        return normalize_whitespace(text) if text else ""
