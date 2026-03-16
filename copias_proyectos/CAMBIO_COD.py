import re
from pathlib import Path


COD_PRESTADOR_NUEVA_EPS = {
    "FVEP": "190010892311",
    "FVEA": "630010180202",
    "FVEM": "170010288401",
}

COD_PRESTADOR_FIJO_POR_METODO = {
    "1": "170010288401",  # Salud Total
    "3": "760011569301",  # Coosalud
    "4": "170010288401",  # Famisanar
}

NOMBRE_METODO = {
    "1": "Salud Total",
    "2": "Nueva EPS",
    "3": "Coosalud",
    "4": "Famisanar",
}

NUM_FACTURA_PATTERN = re.compile(r'"numFactura"\s*:\s*"([^"]+)"')
COD_PRESTADOR_PATTERN = re.compile(r'("codPrestador"\s*:\s*")([^"]*)(")')
FINALIDAD_TEC_SALUD_PATTERN = re.compile(
    r'("finalidadTecnologiaSalud"\s*:\s*")11(")'
)


def seleccionar_metodo() -> str:
    print("Selecciona el metodo a usar:")
    print("1. Salud Total")
    print("2. Nueva EPS")
    print("3. Coosalud")
    print("4. Famisanar")

    while True:
        metodo = input("Opcion (1-4): ").strip()
        if metodo in NOMBRE_METODO:
            return metodo
        print("Opcion invalida. Debes elegir 1, 2, 3 o 4.")


def obtener_cod_prestador_nueva_eps(num_factura: str) -> str | None:
    for prefijo, cod_prestador in COD_PRESTADOR_NUEVA_EPS.items():
        if num_factura.startswith(prefijo):
            return cod_prestador
    return None


def obtener_cod_objetivo(texto: str, metodo: str) -> tuple[str | None, str | None]:
    if metodo in COD_PRESTADOR_FIJO_POR_METODO:
        return COD_PRESTADOR_FIJO_POR_METODO[metodo], None

    match_factura = NUM_FACTURA_PATTERN.search(texto)
    if not match_factura:
        return None, "Sin numFactura valida"

    num_factura = match_factura.group(1)
    cod_objetivo = obtener_cod_prestador_nueva_eps(num_factura)
    if cod_objetivo is None:
        return None, f"Sin prefijo objetivo en numFactura ({num_factura})"

    return cod_objetivo, None


def procesar_archivo_json(ruta_json: Path, metodo: str) -> tuple[bool, str]:
    try:
        texto = ruta_json.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"No se pudo leer {ruta_json}: {e}"

    cod_objetivo, motivo_sin_cambio = obtener_cod_objetivo(texto, metodo)
    if cod_objetivo is None:
        return False, f"{motivo_sin_cambio}: {ruta_json}"

    total_cod_prestador = len(COD_PRESTADOR_PATTERN.findall(texto))
    cambios_cod_prestador = 0

    def reemplazar_cod_prestador(match: re.Match[str]) -> str:
        nonlocal cambios_cod_prestador
        cod_actual = match.group(2)
        if cod_actual == cod_objetivo:
            return match.group(0)
        cambios_cod_prestador += 1
        return f"{match.group(1)}{cod_objetivo}{match.group(3)}"

    texto_actualizado = COD_PRESTADOR_PATTERN.sub(reemplazar_cod_prestador, texto)
    texto_actualizado, cambios_finalidad = FINALIDAD_TEC_SALUD_PATTERN.subn(
        r"\g<1>12\2", texto_actualizado
    )

    if cambios_cod_prestador == 0 and cambios_finalidad == 0:
        return False, (
            f"Sin cambios (codPrestador ya correcto y "
            f"sin finalidadTecnologiaSalud=\"11\"): {ruta_json}"
        )

    try:
        ruta_json.write_text(texto_actualizado, encoding="utf-8")
    except OSError as e:
        return False, f"No se pudo escribir {ruta_json}: {e}"

    return True, (
        f"Actualizado: {ruta_json} "
        f"(codPrestador modificados: {cambios_cod_prestador}/{total_cod_prestador}, "
        f"finalidadTecnologiaSalud 11->12: {cambios_finalidad})"
    )


def main() -> None:
    metodo = seleccionar_metodo()
    print(f"Metodo seleccionado: {NOMBRE_METODO[metodo]}")

    ruta_input = input("Ingresa la ruta de la carpeta principal: ").strip().strip('"')
    carpeta_principal = Path(ruta_input)

    if not carpeta_principal.exists() or not carpeta_principal.is_dir():
        print(f"Ruta invalida o no es carpeta: {carpeta_principal}")
        return

    archivos_json = sorted(carpeta_principal.rglob("*.json"))
    if not archivos_json:
        print("No se encontraron archivos .json en la carpeta indicada.")
        return

    total = len(archivos_json)
    actualizados = 0

    for ruta_json in archivos_json:
        cambio, mensaje = procesar_archivo_json(ruta_json, metodo)
        if cambio:
            actualizados += 1
        print(mensaje)

    print("\nResumen:")
    print(f"Archivos JSON encontrados: {total}")
    print(f"Archivos actualizados: {actualizados}")
    print(f"Archivos sin cambio/error: {total - actualizados}")


if __name__ == "__main__":
    main()
