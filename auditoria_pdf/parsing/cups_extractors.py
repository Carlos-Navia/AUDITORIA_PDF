from __future__ import annotations

import re

from auditoria_pdf.parsing.contracts import CupsExtractorContract


class ContextAwareCupsExtractor(CupsExtractorContract):
    def extract(self, text: str) -> set[str]:
        cups_codes: set[str] = set()
        candidate_pattern = re.compile(r"\b([89]\d{5})\b")

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            normalized_line = line.upper()
            has_context = any(
                token in normalized_line
                for token in ("CODIGO", "CUPS", "SERVICIO", "CONSULTA", "PROCEDIMIENTO")
            )
            if has_context:
                cups_codes.update(candidate_pattern.findall(line))
                if idx + 1 < len(lines):
                    cups_codes.update(candidate_pattern.findall(lines[idx + 1]))

            if re.search(r"^\s*[89]\d{5}(?:\s*,\s*[89]\d{5})+\s*$", line):
                cups_codes.update(candidate_pattern.findall(line))

        if not cups_codes:
            cups_codes.update(candidate_pattern.findall(text))

        return cups_codes


class NoCupsExtractor(CupsExtractorContract):
    def extract(self, text: str) -> set[str]:
        return set()


class FevCupsExtractor(ContextAwareCupsExtractor):
    pass


class PdeCupsExtractor(ContextAwareCupsExtractor):
    pass


class CrcCupsExtractor(NoCupsExtractor):
    pass


class HevCupsExtractor(NoCupsExtractor):
    pass


class PdxCupsExtractor(NoCupsExtractor):
    pass


class HaoCupsExtractor(NoCupsExtractor):
    pass


class AdditionalCupsExtractor(NoCupsExtractor):
    pass
