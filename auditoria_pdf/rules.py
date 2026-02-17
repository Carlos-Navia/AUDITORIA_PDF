from __future__ import annotations

from abc import ABC, abstractmethod
import unicodedata

from auditoria_pdf.domain import AuditContext, DocumentType, RuleResult


def _normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_accents.upper().split())


def _normalize_regimen(value: str | None) -> str | None:
    token = _normalize_text(value)
    if not token:
        return None
    if "SUBSIDI" in token:
        return "SUBSIDIADO"
    if "CONTRIBUT" in token:
        return "CONTRIBUTIVO"
    return None


def _detect_eps(context: AuditContext) -> str:
    candidates: list[str] = []
    factura = context.get_mandatory(DocumentType.FACTURA)
    if factura:
        candidates.append(factura.raw_text.upper())
        candidates.append(str(factura.source_path).upper())

    for parsed in context.all_documents():
        candidates.append(str(parsed.source_path).upper())

    merged = " ".join(candidates)
    if "COOSALUD" in merged:
        return "COOSALUD"
    if "NUEVA EPS" in merged or "NUEVAEPS" in merged:
        return "NUEVA EPS"
    return "DESCONOCIDA"


class AuditRule(ABC):
    rule_id: str
    description: str

    @abstractmethod
    def evaluate(self, context: AuditContext) -> RuleResult:
        raise NotImplementedError


class FileSetComplianceRule(AuditRule):
    rule_id = "R0_ESTRUCTURA_LOTE"
    description = (
        "Validar estructura del lote: 4 a 6 PDFs, obligatorios FEV/PDE/CRC y minimo 1 adicional."
    )

    REQUIRED = (
        DocumentType.FACTURA,
        DocumentType.AUTORIZACION,
        DocumentType.SOPORTE,
    )

    def evaluate(self, context: AuditContext) -> RuleResult:
        total_parsed = len(context.all_documents())
        missing_required = [
            doc_type.value
            for doc_type in self.REQUIRED
            if context.get_mandatory(doc_type) is None
        ]

        details: list[str] = []
        if total_parsed < context.min_pdfs or total_parsed > context.max_pdfs:
            details.append(
                f"Cantidad invalida de PDFs: {total_parsed}. Permitido: {context.min_pdfs}-{context.max_pdfs}."
            )
        if missing_required:
            details.append(f"Faltan documentos obligatorios: {', '.join(missing_required)}.")
        if len(context.additional_documents) < 1:
            details.append("Debe existir al menos 1 documento adicional al trio FEV/PDE/CRC.")

        if not details:
            details.append("Estructura del lote valida.")

        return RuleResult(
            rule_id=self.rule_id,
            description=self.description,
            passed=len(details) == 1 and details[0] == "Estructura del lote valida.",
            expected=f"{context.min_pdfs}-{context.max_pdfs} PDFs con FEV/PDE/CRC + >=1 adicional",
            actual=(
                "total="
                f"{total_parsed}, obligatorios="
                + ",".join(
                    doc_type.value
                    for doc_type in sorted(
                        context.mandatory_documents.keys(), key=lambda d: d.value
                    )
                )
                + ", "
                f"adicionales={len(context.additional_documents)}"
            ),
            details=details,
        )


class CupsMatchRule(AuditRule):
    rule_id = "R1_CODIGO_FEV_VS_PDE"
    description = "Validar que el codigo/CUPS en FEV coincida con el codigo/CUPS en PDE."

    def evaluate(self, context: AuditContext) -> RuleResult:
        if _detect_eps(context) == "COOSALUD":
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=True,
                expected="N/A",
                actual="N/A",
                details=["Comparacion de codigo/CUPS omitida para COOSALUD por regla de negocio."],
            )

        factura = context.get_mandatory(DocumentType.FACTURA)
        autorizacion = context.get_mandatory(DocumentType.AUTORIZACION)

        if not factura or not autorizacion:
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=False,
                details=["Falta FEV o PDE para ejecutar la comparacion."],
            )

        cups_factura = factura.cups_codes
        cups_autorizacion = autorizacion.cups_codes

        if not cups_factura:
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=False,
                details=["No se detecto codigo/CUPS en FEV."],
            )
        if not cups_autorizacion:
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=False,
                details=["No se detecto codigo/CUPS en PDE."],
            )

        missing_in_pde = sorted(cups_factura - cups_autorizacion)
        extra_in_pde = sorted(cups_autorizacion - cups_factura)
        passed = len(missing_in_pde) == 0

        details: list[str] = []
        if missing_in_pde:
            details.append(
                f"Codigos en FEV sin soporte en PDE: {', '.join(missing_in_pde)}."
            )
        if extra_in_pde:
            details.append(
                f"Codigos en PDE no presentes en FEV: {', '.join(extra_in_pde)}."
            )
        if not details:
            details.append("Codigo/CUPS consistente entre FEV y PDE.")

        return RuleResult(
            rule_id=self.rule_id,
            description=self.description,
            passed=passed,
            expected=", ".join(sorted(cups_autorizacion)),
            actual=", ".join(sorted(cups_factura)),
            details=details,
        )


class PatientDocumentConsistencyRule(AuditRule):
    rule_id = "R2_DOCUMENTO_FEV_VS_TODOS"
    description = (
        "Verificar que el documento del paciente en FEV coincida contra todos los demas documentos del lote."
    )

    def evaluate(self, context: AuditContext) -> RuleResult:
        factura = context.get_mandatory(DocumentType.FACTURA)
        if not factura:
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=False,
                details=["No existe FEV para tomar documento de referencia."],
            )

        reference_document = factura.patient_document
        if not reference_document:
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=False,
                details=["No se pudo extraer documento del paciente en FEV (referencia)."],
            )

        targets = [
            doc
            for doc in context.all_documents()
            if doc.source_path != factura.source_path
        ]
        if not targets:
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=False,
                details=["No hay documentos adicionales para comparar contra FEV."],
            )

        details: list[str] = []
        mismatches: list[str] = []
        actual_tokens = [f"FEV:{reference_document}"]

        for doc in targets:
            value = doc.patient_document
            actual_tokens.append(f"{doc.prefix}:{value or 'N/D'}")
            if not value:
                mismatches.append(f"{doc.prefix}=N/D")
                details.append(
                    f"No se pudo extraer documento del paciente en {doc.source_path.name}."
                )
                continue
            if value != reference_document:
                mismatches.append(f"{doc.prefix}={value}")
                details.append(
                    f"Diferencia detectada: FEV={reference_document} vs {doc.prefix}={value} ({doc.source_path.name})."
                )

        passed = len(mismatches) == 0
        if passed:
            details.append("Documento del paciente consistente entre FEV y todos los demas PDFs.")

        return RuleResult(
            rule_id=self.rule_id,
            description=self.description,
            passed=passed,
            expected=reference_document,
            actual=" | ".join(actual_tokens),
            details=details,
        )


class RegimenConsistencyRule(AuditRule):
    rule_id = "R3_REGIMEN_FEV_VS_PDE"
    description = "Verificar regimen del paciente entre FEV y PDE (solo Subsidiado o Contributivo)."

    def evaluate(self, context: AuditContext) -> RuleResult:
        factura = context.get_mandatory(DocumentType.FACTURA)
        autorizacion = context.get_mandatory(DocumentType.AUTORIZACION)

        if not factura or not autorizacion:
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=False,
                details=["Falta FEV o PDE para comparar regimen."],
            )

        regimen_factura = _normalize_regimen(factura.regimen)
        regimen_autorizacion = _normalize_regimen(autorizacion.regimen)

        if not regimen_factura or not regimen_autorizacion:
            return RuleResult(
                rule_id=self.rule_id,
                description=self.description,
                passed=False,
                expected=regimen_autorizacion,
                actual=regimen_factura,
                details=[
                    "No se pudo extraer literalmente SUBSIDIADO/CONTRIBUTIVO en FEV o PDE.",
                    f"FEV: {factura.regimen or 'N/D'} | PDE: {autorizacion.regimen or 'N/D'}",
                ],
            )

        passed = regimen_factura == regimen_autorizacion
        details = (
            ["Regimen consistente entre FEV y PDE."]
            if passed
            else ["Regimen inconsistente entre FEV y PDE."]
        )

        return RuleResult(
            rule_id=self.rule_id,
            description=self.description,
            passed=passed,
            expected=regimen_autorizacion,
            actual=regimen_factura,
            details=details,
        )
