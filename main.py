from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from auditoria_pdf.batch import BatchAuditRunner
from auditoria_pdf.domain import AuditReport
from auditoria_pdf.excel_exporter import AuditExcelExporter
from auditoria_pdf.extractor import PdfTextExtractor
from auditoria_pdf.service import PdfAuditService


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auditoria OOP de PDFs de facturacion en salud."
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        help="Carpeta con PDFs del mismo caso (se esperan 4 a 6 PDFs).",
    )
    parser.add_argument(
        "--root-dir",
        type=Path,
        help="Carpeta principal para modo masivo (busca subcarpetas con PDFs).",
    )
    parser.add_argument("--fev", type=Path, help="Ruta PDF factura (FEV_*.pdf).")
    parser.add_argument("--pde", type=Path, help="Ruta PDF autorizacion (PDE_*.pdf).")
    parser.add_argument("--crc", type=Path, help="Ruta PDF soporte (CRC_*.pdf).")
    parser.add_argument(
        "--hev",
        type=Path,
        help="Ruta PDF adicional HEV (opcional, se trata como documento adicional).",
    )
    parser.add_argument(
        "--extra",
        type=Path,
        nargs="*",
        default=[],
        help="Rutas de PDFs adicionales (HAO, PDX, HEV u otros).",
    )
    parser.add_argument(
        "--tesseract-cmd",
        type=str,
        default=None,
        help="Ruta de tesseract.exe si no se detecta automaticamente.",
    )
    parser.add_argument(
        "--min-pdfs",
        type=int,
        default=4,
        help="Cantidad minima de PDFs permitida por lote (default: 4).",
    )
    parser.add_argument(
        "--max-pdfs",
        type=int,
        default=6,
        help="Cantidad maxima de PDFs permitida por lote (default: 6).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Archivo de salida para guardar reporte completo en JSON.",
    )
    parser.add_argument(
        "--output-excel",
        type=Path,
        default=None,
        help="Archivo Excel de salida (.xlsx). Si no se indica, se genera automaticamente en ./salidas.",
    )
    return parser


def _collect_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []

    if args.pdf_dir:
        paths.extend(sorted(args.pdf_dir.glob("*.pdf")))

    explicit_paths = [args.fev, args.pde, args.crc, args.hev]
    paths.extend(path for path in explicit_paths if path is not None)
    paths.extend(args.extra)

    return list(dict.fromkeys(paths))


def _print_report(report) -> None:
    print("=" * 90)
    print("RESULTADO AUDITORIA:", "APROBADO" if report.success else "RECHAZADO")
    print("=" * 90)

    if report.errors:
        print("Errores de procesamiento:")
        for error in report.errors:
            print(f"  - {error}")
        print()

    print("Reglas:")
    for result in report.rule_results:
        status = "OK" if result.passed else "FAIL"
        print(f"  [{status}] {result.rule_id} - {result.description}")
        if result.expected is not None or result.actual is not None:
            print(f"     Esperado: {result.expected or 'N/D'}")
            print(f"     Actual:   {result.actual or 'N/D'}")
        for detail in result.details:
            print(f"     - {detail}")

    print()
    print("Datos extraidos por documento:")
    for parsed in sorted(report.parsed_documents, key=lambda item: item.source_path.name):
        cups = ", ".join(sorted(parsed.cups_codes)) if parsed.cups_codes else "N/D"
        print(f"  - {parsed.source_path.name} [{parsed.prefix}]")
        print(f"     Tipo interno:        {parsed.doc_type.value}")
        print(f"     Documento paciente:  {parsed.patient_document or 'N/D'}")
        print(f"     Tipo documento:      {parsed.patient_document_type or 'N/D'}")
        print(f"     Regimen:             {parsed.regimen or 'N/D'}")
        print(f"     Codigo/CUPS:         {cups}")


def _build_default_excel_path(pdf_paths: list[Path]) -> Path:
    case_name = "auditoria"
    if pdf_paths:
        first_parent = pdf_paths[0].parent.name.strip()
        if first_parent:
            case_name = first_parent.replace(" ", "_")
    return Path("salidas") / f"reporte_{case_name}.xlsx"


def _build_default_batch_excel_path(root_dir: Path) -> Path:
    safe_name = root_dir.name.strip().replace(" ", "_") or "masivo"
    return root_dir / f"reporte_masivo_{safe_name}.xlsx"


def _prompt_root_dir() -> Path:
    raw = input("Ingrese la ruta de la carpeta principal: ").strip().strip('"').strip("'")
    if not raw:
        raise ValueError("Debes ingresar una ruta de carpeta principal.")
    return Path(raw)


def _run_single_mode(args: argparse.Namespace, pdf_paths: list[Path]) -> int:
    extractor = PdfTextExtractor(tesseract_cmd=args.tesseract_cmd)
    service = PdfAuditService(
        extractor=extractor,
        min_pdfs=args.min_pdfs,
        max_pdfs=args.max_pdfs,
    )
    report = service.audit(pdf_paths)

    _print_report(report)

    excel_exporter = AuditExcelExporter()
    excel_output = args.output_excel or _build_default_excel_path(pdf_paths)
    excel_exporter.export(report, excel_output)
    print()
    print(f"Reporte Excel guardado en: {excel_output}")

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print()
        print(f"Reporte JSON guardado en: {args.output_json}")

    return 0 if report.success else 2


def _run_batch_mode(args: argparse.Namespace, root_dir: Path) -> int:
    if not root_dir.exists() or not root_dir.is_dir():
        raise ValueError(f"Ruta invalida para carpeta principal: {root_dir}")

    extractor = PdfTextExtractor(tesseract_cmd=args.tesseract_cmd)
    service = PdfAuditService(
        extractor=extractor,
        min_pdfs=args.min_pdfs,
        max_pdfs=args.max_pdfs,
    )
    runner = BatchAuditRunner(service)
    case_results = runner.run(root_dir)

    if not case_results:
        raise ValueError(f"No se encontraron subcarpetas con PDFs en: {root_dir}")

    print("=" * 90)
    print(f"RESULTADO AUDITORIA MASIVA - CARPETA PRINCIPAL: {root_dir}")
    print("=" * 90)

    approved = 0
    rejected = 0
    export_payload: list[tuple[str, AuditReport]] = []
    json_payload: list[dict] = []

    for item in case_results:
        relative_folder = item.case_folder.relative_to(root_dir)
        folder_label = str(relative_folder).replace("\\", "/")
        if folder_label in {"", "."}:
            folder_label = item.case_folder.name
        status = "APROBADO" if item.success else "RECHAZADO"
        if item.success:
            approved += 1
        else:
            rejected += 1

        print(
            f"[{status}] {folder_label} | PDFs: {len(item.pdf_paths)} | Errores: {len(item.report.errors)}"
        )
        export_payload.append((folder_label, item.report))
        json_payload.append(
            {
                "carpeta": folder_label,
                "pdf_count": len(item.pdf_paths),
                "report": item.report.to_dict(),
            }
        )

    print("-" * 90)
    print(f"Total carpetas evaluadas: {len(case_results)}")
    print(f"Aprobadas: {approved}")
    print(f"Rechazadas: {rejected}")

    excel_exporter = AuditExcelExporter()
    excel_output = args.output_excel or _build_default_batch_excel_path(root_dir)
    excel_exporter.export_many(export_payload, excel_output)
    print(f"Reporte Excel consolidado guardado en: {excel_output}")

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(
                {
                    "root_dir": str(root_dir),
                    "total_cases": len(case_results),
                    "approved": approved,
                    "rejected": rejected,
                    "cases": json_payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Reporte JSON consolidado guardado en: {args.output_json}")

    return 0 if rejected == 0 else 2


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    pdf_paths = _collect_paths(args)

    if args.min_pdfs < 1:
        parser.error("--min-pdfs debe ser >= 1.")
    if args.max_pdfs < args.min_pdfs:
        parser.error("--max-pdfs debe ser >= --min-pdfs.")

    single_inputs_provided = bool(pdf_paths)
    root_mode_provided = args.root_dir is not None

    if single_inputs_provided and root_mode_provided:
        parser.error("Usa modo unico (pdf-dir/fev/pde/crc/extra) o modo masivo (root-dir), no ambos.")

    if single_inputs_provided:
        return _run_single_mode(args, pdf_paths)

    try:
        root_dir = args.root_dir or _prompt_root_dir()
        return _run_batch_mode(args, root_dir)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
