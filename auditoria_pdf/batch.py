from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auditoria_pdf.domain import AuditReport
from auditoria_pdf.service import PdfAuditService


@dataclass(slots=True)
class CaseAuditResult:
    case_folder: Path
    pdf_paths: list[Path]
    report: AuditReport

    @property
    def success(self) -> bool:
        return self.report.success


class PdfCaseScanner:
    def find_case_folders(self, root_dir: Path) -> dict[Path, list[Path]]:
        grouped: dict[Path, list[Path]] = {}
        for pdf_path in sorted(root_dir.rglob("*.pdf")):
            grouped.setdefault(pdf_path.parent, []).append(pdf_path)

        return dict(sorted(grouped.items(), key=lambda item: str(item[0]).upper()))


class BatchAuditRunner:
    def __init__(
        self, audit_service: PdfAuditService, scanner: PdfCaseScanner | None = None
    ) -> None:
        self.audit_service = audit_service
        self.scanner = scanner or PdfCaseScanner()

    def run(self, root_dir: Path) -> list[CaseAuditResult]:
        folder_map = self.scanner.find_case_folders(root_dir)
        results: list[CaseAuditResult] = []
        for folder, pdf_paths in folder_map.items():
            report = self.audit_service.audit(pdf_paths)
            results.append(
                CaseAuditResult(
                    case_folder=folder,
                    pdf_paths=pdf_paths,
                    report=report,
                )
            )
        return results
