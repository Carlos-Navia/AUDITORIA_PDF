from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from auditoria_pdf.domain import DocumentType
from auditoria_pdf.parsing import BaseDocumentParser
from auditoria_pdf.parsing.document_parsers import NuevaEpsPdeDocumentParser, SanitasPdeDocumentParser
from auditoria_pdf.rules import (
    AuditRule,
    CupsMatchRule,
    CupsMatchSkippedRule,
    FileSetComplianceRule,
    PatientDocumentConsistencyRule,
    RegimenConsistencyRule,
)


class EpsProfileKey(str, Enum):
    COOSALUD = "coosalud"
    NUEVA_EPS = "nueva_eps"
    SANITAS = "sanitas"


class EpsAuditProfile(ABC):
    key: EpsProfileKey
    display_name: str

    @abstractmethod
    def build_rules(self) -> list[AuditRule]:
        raise NotImplementedError

    def page_limits(self) -> dict[DocumentType, int]:
        return {
            DocumentType.FACTURA: 2,
            DocumentType.AUTORIZACION: 2,
            DocumentType.SOPORTE: 2,
            DocumentType.VALIDADOR: 3,
            DocumentType.ADICIONAL: 2,
        }

    def render_fallback_types(self) -> set[DocumentType]:
        return {
            DocumentType.FACTURA,
            DocumentType.AUTORIZACION,
            DocumentType.SOPORTE,
            DocumentType.VALIDADOR,
            DocumentType.ADICIONAL,
        }

    def parser_overrides(self) -> dict[DocumentType, BaseDocumentParser]:
        return {}


def _build_shared_rules(cups_rule: AuditRule) -> list[AuditRule]:
    return [
        FileSetComplianceRule(),
        cups_rule,
        PatientDocumentConsistencyRule(),
        RegimenConsistencyRule(),
    ]


class CoosaludAuditProfile(EpsAuditProfile):
    key = EpsProfileKey.COOSALUD
    display_name = "COOSALUD"

    def build_rules(self) -> list[AuditRule]:
        return _build_shared_rules(
            CupsMatchSkippedRule(eps_name=self.display_name),
        )


class NuevaEpsAuditProfile(EpsAuditProfile):
    key = EpsProfileKey.NUEVA_EPS
    display_name = "NUEVA EPS"

    def build_rules(self) -> list[AuditRule]:
        return _build_shared_rules(CupsMatchRule())

    def parser_overrides(self) -> dict[DocumentType, BaseDocumentParser]:
        return {
            DocumentType.AUTORIZACION: NuevaEpsPdeDocumentParser(),
        }


class SanitasAuditProfile(EpsAuditProfile):
    key = EpsProfileKey.SANITAS
    display_name = "SANITAS"

    def build_rules(self) -> list[AuditRule]:
        return _build_shared_rules(CupsMatchRule())

    def parser_overrides(self) -> dict[DocumentType, BaseDocumentParser]:
        return {
            DocumentType.AUTORIZACION: SanitasPdeDocumentParser(),
        }


class EpsAuditProfileFactory:
    def __init__(self) -> None:
        self._profiles: dict[EpsProfileKey, EpsAuditProfile] = {
            EpsProfileKey.COOSALUD: CoosaludAuditProfile(),
            EpsProfileKey.NUEVA_EPS: NuevaEpsAuditProfile(),
            EpsProfileKey.SANITAS: SanitasAuditProfile(),
        }

    def create(self, eps: str | EpsProfileKey) -> EpsAuditProfile:
        key = self._normalize_key(eps)
        return self._profiles[key]

    def create_for_coosalud(self) -> EpsAuditProfile:
        return self._profiles[EpsProfileKey.COOSALUD]

    def create_for_nueva_eps(self) -> EpsAuditProfile:
        return self._profiles[EpsProfileKey.NUEVA_EPS]

    def create_for_sanitas(self) -> EpsAuditProfile:
        return self._profiles[EpsProfileKey.SANITAS]

    def _normalize_key(self, eps: str | EpsProfileKey) -> EpsProfileKey:
        if isinstance(eps, EpsProfileKey):
            return eps

        token = str(eps).strip().lower().replace("-", "_").replace(" ", "_")
        aliases: dict[str, EpsProfileKey] = {
            "1": EpsProfileKey.COOSALUD,
            "coosalud": EpsProfileKey.COOSALUD,
            "2": EpsProfileKey.NUEVA_EPS,
            "nueva_eps": EpsProfileKey.NUEVA_EPS,
            "nuevaeps": EpsProfileKey.NUEVA_EPS,
            "3": EpsProfileKey.SANITAS,
            "sanitas": EpsProfileKey.SANITAS,
        }
        selected = aliases.get(token)
        if selected is None:
            supported = ", ".join(item.value for item in EpsProfileKey)
            raise ValueError(
                f"EPS no soportada: {eps}. Valores permitidos: {supported}."
            )
        return selected
