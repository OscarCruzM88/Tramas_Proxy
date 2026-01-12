# ===============================
# CONFIGURACIÓN
# ===============================
PLAN_POS_OFFSET = 14      # byte 15 (base 0)
AUT_LEN = 38


# ===============================
# EXTRACCIÓN DE BYTES
# ===============================
def hex_bytes(linea: str) -> list[str]:
    if ":" not in linea:
        return []
    return linea.split(":", 1)[1].strip().upper().split()


# ===============================
# CONVERSIONES
# ===============================
def bcd_packed_a_int(byte_hex: str) -> int:
    val = int(byte_hex, 16)
    return ((val >> 4) & 0xF) * 10 + (val & 0xF)


def decodificar_texto(bytes_hex: list[str]) -> str:
    data = bytes(int(b, 16) for b in bytes_hex)

    for encoding in ("ascii", "cp037"):
        try:
            texto = data.decode(encoding)
            if any(c.isalpha() for c in texto):
                # Limpia caracteres de control (ASCII < 32)
                return "".join(c for c in texto if ord(c) >= 32).rstrip()
        except:
            pass

    return ""



# ===============================
# LÓGICA DE AUTORIZACIÓN
# ===============================
def obtener_inicio_aut(plan: int) -> int:
    """
    Regla validada:
    - Plan 19, 69 → byte 37 (base 0 = 36)
    - Plan 60, 61 → byte 38 (base 0 = 37)
    - Resto        → byte 36 (base 0 = 35)
    """
    if plan in (19, 69):
        return 36
    elif plan in (60, 61):
        return 37
    else:
        return 35


def extraer_autorizacion(bytes_trama: list[str]) -> tuple[str, str]:
    if len(bytes_trama) <= PLAN_POS_OFFSET:
        return "", ""

    # PLAN viene fijo en byte 15
    plan = bcd_packed_a_int(bytes_trama[PLAN_POS_OFFSET])

    inicio_aut = obtener_inicio_aut(plan)
    fin_aut = inicio_aut + AUT_LEN

    if len(bytes_trama) < fin_aut:
        return str(plan), ""

    aut_bytes = bytes_trama[inicio_aut:fin_aut]
    autorizacion = decodificar_texto(aut_bytes)

    return str(plan), autorizacion


# ===============================
# PROCESO PRINCIPAL
# ===============================
def procesar_pos(entrada: str, salida: str):

    with open(entrada, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    with open(salida, "w", encoding="utf-8") as out:
        out.write("Autorizacion\n")

        for linea in lineas:
            if "Proxy->POS" not in linea:
                continue

            bytes_trama = hex_bytes(linea)
            if not bytes_trama:
                continue

            plan, autorizacion = extraer_autorizacion(bytes_trama)

            # No usar comillas aunque venga vacío
            out.write(f"{autorizacion}\n")

    print(f"Archivo generado correctamente: {salida}")


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    procesar_pos(
        "tramas_11-01-26_1600.csv",
        "aut_11-01-26_1600.csv"
    )