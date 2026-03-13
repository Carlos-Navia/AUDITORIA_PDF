from __future__ import annotations

import unittest

from auditoria_pdf.parsers import (
    _extract_patient_document_crc,
    _extract_patient_document_generic,
)
from auditoria_pdf.parsing.patient_document_extractors import (
    FevPatientDocumentExtractor,
    HevPatientDocumentExtractor,
    PdePatientDocumentExtractor,
    PdxPatientDocumentExtractor,
    SanitasPdePatientDocumentExtractor,
)


class PatientDocumentExtractorTest(unittest.TestCase):
    def test_extracts_fev_document_number_in_compact_layout(self) -> None:
        text = """
        DATOS SALUD
        TIPO DOCUMENTO. Tarjeta Identidad NUMERO DOCUMENTO = 1112156995 COBERTURA
        PRIMER NOMBRE JHERYKO PRIMER APELLIDO TEJADA
        """
        self.assertEqual(_extract_patient_document_generic(text), "1112156995")

    def test_prioritizes_patient_number_over_promoter_number(self) -> None:
        text = """
        Numero identificacion: 26147840
        Nombre usuario: DOMINGA GUERRERO MATOS
        1099735197 26147840
        Numero de identificacion y firma promotor(a): Numero de identificacion y firma usuario(a):
        """
        self.assertEqual(_extract_patient_document_generic(text), "26147840")

    def test_avoids_nit_when_patient_section_exists(self) -> None:
        text = """
        NIT 901011395
        Datos del paciente
        Identificacion: CC-22870931
        """
        self.assertEqual(_extract_patient_document_generic(text), "22870931")

    def test_handles_ocr_noise_near_digits(self) -> None:
        text = """
        Datos del paciente
        Identificacion: TI-1112I56995
        """
        self.assertEqual(_extract_patient_document_generic(text), "1112156995")

    def test_prefers_document_identity_over_phone_in_noisy_line(self) -> None:
        text = """
        FORMATO ENTREGA DE RESULTADOS
        DOCUMENTO IDENTIDAD: [85126366 SS FECHA DE NACIMIENTO: 28/12/1969
        NOMBRES: VICENTE ANTONIO
        APELLIDOS: CARRILLO VILLAR TELEFONO 3012327124
        """
        self.assertEqual(_extract_patient_document_generic(text), "85126366")

    def test_crc_table_layout_extracts_identification_not_cellphone(self) -> None:
        text = """
        Cuidando nuestra comunidad RECIBO DE SATISFACCION DEL SERVICIO DE SALUD EN
        UNIDAD MOVIL
        Tipo de Identificacion: ce Numero de identificacion:
        Sexo: FEMENINO Numero Celular:
        ADN-VPH (CUPS 908890)
        MARIA SOLEDAD
        31913423
        61
        SUBSIDIADO
        3207173962
        CALI
        """
        self.assertEqual(_extract_patient_document_crc(text), "31913423")

    def test_crc_keeps_document_when_phone_is_on_same_block(self) -> None:
        text = """
        HORIZONTE SOCIAL LA ESPERANZA- IPS HORISOES
        NIT-901011395-1
        Numero de Documento: 1084726821 Direccion VE LA ESTRELLA SALIDA PUEBLO
        Nombre y Apellidos: DELSY JUDITH GARCIA MARTINEZ Telefono: 3148742619
        Departamento: MAGDALENA
        """
        self.assertEqual(_extract_patient_document_crc(text), "1084726821")


class PdxPatientDocumentExtractorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = PdxPatientDocumentExtractor()

    def test_prefers_patient_identification_over_phone_and_signatures(self) -> None:
        text = """
        COLCAN LABORATORIO CLINICO
        Nombre ZANCHES LOPEZ MARIA ISABEL
        Identificacion CC 1049346469 Tel. 999999999
        Fecha de recepcion 09/05/2025
        Examen PAPILOMAVIRUS POR PCR CON TIPIFICACION DE 14 CEPAS

        Tecnica: Anyplex II, HPV HR detection - SEEGENE.
        QUINTERO MARROQUIN DANIELA ANDREA
        CC.1011167055
        BACTERIOLOGA
        IVAN GIOVANNI RAMIREZ AYALA
        C.C 88.272.036
        BACTERIOLOGO
        """
        self.assertEqual(self.extractor.extract(text), "1049346469")

    def test_extracts_identification_without_document_type_prefix(self) -> None:
        text = """
        COLCAN LABORATORIO CLINICO
        Nombre PACIENTE DEMO
        Identificacion: 1049346469 Tel: 3150000000
        Examen PCR
        """
        self.assertEqual(self.extractor.extract(text), "1049346469")

    def test_uses_only_identification_line_before_tel(self) -> None:
        text = """
        Nombre: ROCIO DEL PILAR MEJIA BOLAÑOS Nº Ordenamiento: 20439-57430707
        Identificación: CC 57430707 Tel: 999999999 Fecha de recepción: 09/09/2025
        Firma bacteriologo CC 1011167055
        """
        self.assertEqual(self.extractor.extract(text), "57430707")

    def test_returns_none_when_identification_line_is_missing(self) -> None:
        text = """
        Nombre: PACIENTE DEMO
        Firma bacteriologo CC 1011167055
        Tel: 999999999
        """
        self.assertIsNone(self.extractor.extract(text))


class DocumentSpecificPatientExtractorTest(unittest.TestCase):
    def test_fev_extractor_prioritizes_document_field(self) -> None:
        text = """
        FACTURA ELECTRONICA
        TIPO DOCUMENTO: CC NUMERO DOCUMENTO: 1112156995
        TELEFONO: 3011111111
        """
        self.assertEqual(FevPatientDocumentExtractor().extract(text), "1112156995")

    def test_pde_extractor_uses_identification_anchor(self) -> None:
        text = """
        AUTORIZACION DE SERVICIOS
        Numero de Identificacion: 22870931
        Afiliado: CC 999999999
        """
        self.assertEqual(PdePatientDocumentExtractor().extract(text), "22870931")

    def test_sanitas_pde_extractor_prioritizes_cotizante_titular_document(self) -> None:
        text = """
        Telefono principal: 3217011629
        Segundo Telefono: 3217011629
        Tipo de documento: CC
        Numero de documento del Cotizante Titular: 24869471 Motivo del estado del usuario:
        SUBSIDIADO
        """
        self.assertEqual(SanitasPdePatientDocumentExtractor().extract(text), "24869471")

    def test_hev_extractor_ignores_signature_document(self) -> None:
        text = """
        VALIDACION
        Paciente CC 1049346469
        Firma bacteriologo CC 1011167055
        """
        self.assertEqual(HevPatientDocumentExtractor().extract(text), "1049346469")

    def test_hev_extractor_ficha_educacion_layout_uses_identification_field(self) -> None:
        text = """
        FICHA DE EDUCACION INDIVIDUAL
        DATOS BASICOS DE LA PERSONA QUE RECIBE LA ACTIVIDAD EDUCATIVA
        Tipo de Identificacion: CEDULA
        Numero de identificacion: 12395389
        NOMBRE E IDENTIFICACION DEL EDUCADOR
        FIRMA DEL PACIENTE
        92318339
        """
        self.assertEqual(HevPatientDocumentExtractor().extract(text), "12395389")

    def test_hev_extractor_demanda_inducida_layout_uses_identification_field(self) -> None:
        text = """
        FORMATO DE DEMANDA INDUCIDA (COOSALUD)
        DATOS PERSONALES DEL USUARIO
        Numero Identificacion: 26930345 Tipo ID: CC
        Primer nombre: JONUE
        Numero de celular: 3106247230
        """
        self.assertEqual(HevPatientDocumentExtractor().extract(text), "26930345")

    def test_hev_extractor_returns_none_when_only_noisy_signature_number_exists(self) -> None:
        text = """
        FICHA DE EDUCACION INDIVIDUAL
        Tipo de Identificacion Numero de identificacion ZC AAG
        NOMBRE E IDENTIFICACION DEL EDUCADOR
        FIRMA DEL PACIENTE
        730945
        """
        self.assertIsNone(HevPatientDocumentExtractor().extract(text))


if __name__ == "__main__":
    unittest.main()
