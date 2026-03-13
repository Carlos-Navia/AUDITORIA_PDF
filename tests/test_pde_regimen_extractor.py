from __future__ import annotations

import unittest

from auditoria_pdf.parsing.regimen_extractors import (
    NuevaEpsPdeRegimenExtractor,
    PdeRegimenExtractor,
    SanitasPdeRegimenExtractor,
)


class PdeRegimenExtractorTest(unittest.TestCase):
    def test_prefers_early_contributivo_over_late_disclaimer_subsidiado(self) -> None:
        text = """
        Datos de afiliacion :
        ESTADO ENTIDAD REGIMEN FECHA DE AFILIACION
        ACTIVO COOSALUD EPS S.A. -CMCONTRIBUTIVO01/05/2021 31/12/2999 COTIZANTE
        La informacion registrada corresponde al Regimen Subsidiado y Contributivo.
        """
        self.assertEqual(PdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_detects_subsidiado_from_nueva_eps_header_marker(self) -> None:
        text = """
        NT 901011395 BRIGADA MOVIL-SUBSIDIADO-IPS HORIZONTE SOCIAL LA
        Tipo Identificacion: CC
        Identificacion: 1094925577
        """
        self.assertEqual(PdeRegimenExtractor().extract(text), "SUBSIDIADO")

    def test_detects_contributivo_from_tipo_afiliado_cotizante(self) -> None:
        text = """
        Tipo Identificacion: CC
        Identificacion: 9738017
        Tipo Afiliado: COTIZANTE (A)
        """
        self.assertEqual(PdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_detects_contributivo_from_tipo_afiliado_beneficiario(self) -> None:
        text = """
        Tipo Identificacion: TI
        Identificacion: 1090278107
        Tipo Afiliado: BENEFICIARIO (A)
        """
        self.assertEqual(PdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_detects_contributivo_when_regimen_value_is_split_by_ocr_noise(self) -> None:
        text = """
        Numero de identificacion: 12345678
        R e g i m e n de Afiliacion:
        Con tri butivo
        """
        self.assertEqual(PdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_detects_subsidiado_when_sisben_appears_in_affiliation_fields(self) -> None:
        text = """
        Afiliado: CC 24626273 GONZALEZ MORALES OLGA CECILIA
        Edad: 60 Fecha Nacimiento: 15/12/1964 Tipo Afiliado: Beneficiario (SISBEN-1)
        Categoria Afiliado: SISBEN-1
        Semanas Cotizadas: 625
        """
        self.assertEqual(PdeRegimenExtractor().extract(text), "SUBSIDIADO")

    def test_detects_subsidiado_when_semanas_cotizadas_is_empty(self) -> None:
        text = """
        Tipo Afiliado: Beneficiario
        Categoria Afiliado: A
        Semanas Cotizadas:
        IPS Primaria: CHINCHINA
        """
        self.assertEqual(PdeRegimenExtractor().extract(text), "SUBSIDIADO")


class NuevaEpsPdeRegimenExtractorTest(unittest.TestCase):
    def test_infers_subsidiado_when_semanas_cotizadas_is_empty(self) -> None:
        text = """
        Tipo Afiliado: Beneficiario
        Categoria Afiliado: SISBEN-1
        Semanas Cotizadas:
        IPS Primaria: INSTITUTO DE DIAGNOSTICO
        """
        self.assertEqual(NuevaEpsPdeRegimenExtractor().extract(text), "SUBSIDIADO")

    def test_infers_contributivo_when_semanas_cotizadas_has_value(self) -> None:
        text = """
        Tipo Afiliado: CABEZA DE FAMILIA
        Categoria Afiliado: A
        Semanas Cotizadas: 321
        IPS Primaria: INSTITUTO DE DIAGNOSTICO
        """
        self.assertEqual(NuevaEpsPdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_infers_contributivo_when_semanas_value_is_on_next_line(self) -> None:
        text = """
        Tipo Afiliado: CABEZA DE FAMILIA
        Categoria Afiliado: A
        Semanas Cotizadas:
        198
        IPS Primaria: INSTITUTO DE DIAGNOSTICO
        """
        self.assertEqual(NuevaEpsPdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_infers_contributivo_when_semanas_has_non_numeric_content(self) -> None:
        text = """
        Tipo Afiliado: CABEZA DE FAMILIA
        Categoria Afiliado: A
        Semanas Cotizadas: ACTIVO
        IPS Primaria: INSTITUTO DE DIAGNOSTICO
        """
        self.assertEqual(NuevaEpsPdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_prioritizes_contributivo_when_any_semanas_occurrence_has_content(self) -> None:
        text = """
        Categoria Afiliado: SISBEN-1
        Semanas Cotizadas:
        IPS Primaria: SUBSIDIADO-RED SALUD ARMENIA
        Tipo Afiliado: CABEZA DE FAMILIA
        Categoria A filiado: A
        Semanas Cotizadas: 4
        """
        self.assertEqual(NuevaEpsPdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_keeps_subsidiado_when_semanas_is_empty_and_next_line_is_field_content(self) -> None:
        text = """
        Tipo Afiliado: Beneficiario
        Categoria Afiliado: SISBEN-1
        Semanas Cotizadas:
        SUBSIDIADO-RED SALUD ARMENIA ESE UNIDAD
        IPS Primaria: INTERMEDIA DEL SUR
        """
        self.assertEqual(NuevaEpsPdeRegimenExtractor().extract(text), "SUBSIDIADO")


class SanitasPdeRegimenExtractorTest(unittest.TestCase):
    def test_prefers_estado_usuario_marker_over_header_regimen(self) -> None:
        text = """
        10 REGIMEN CONTRIBUTIVO Contrato
        Numero de documento del Cotizante Titular: 24869471 Motivo del estado del usuario:
        SUBSIDIADO
        """
        self.assertEqual(SanitasPdeRegimenExtractor().extract(text), "SUBSIDIADO")

    def test_extracts_contributivo_from_estado_usuario_marker(self) -> None:
        text = """
        Numero de documento del Cotizante Titular: 9738017 Motivo del estado del usuario:
        CONTRIBUTIVO
        """
        self.assertEqual(SanitasPdeRegimenExtractor().extract(text), "CONTRIBUTIVO")

    def test_falls_back_to_generic_pde_regimen_when_marker_is_missing(self) -> None:
        text = """
        IPS Primaria: SUBSIDIADO-RED SALUD ARMENIA ESE
        Tipo Afiliado: CABEZA DE FAMILIA
        Categoria A filiado: A
        """
        self.assertEqual(SanitasPdeRegimenExtractor().extract(text), "SUBSIDIADO")


if __name__ == "__main__":
    unittest.main()
