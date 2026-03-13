from __future__ import annotations

from dataclasses import dataclass

from auditoria_pdf.domain import AuditContext, RuleResult
from auditoria_pdf.rules import (
    AuditRule,
    CupsMatchRule,
    FileSetComplianceRule,
    PatientDocumentConsistencyRule,
    RegimenConsistencyRule,
)


@dataclass(slots=True)
class AuditRuleEngine:
    rules: list[AuditRule]

    def evaluate(self, context: AuditContext) -> list[RuleResult]:
        return [rule.evaluate(context) for rule in self.rules]


def build_default_rules(cups_rule: AuditRule | None = None) -> list[AuditRule]:
    selected_cups_rule = cups_rule or CupsMatchRule()
    return [
        FileSetComplianceRule(),
        selected_cups_rule,
        PatientDocumentConsistencyRule(),
        RegimenConsistencyRule(),
    ]
