# ===============================
# CONFIGURACIÓN DE CAMPOS (BYTES)
# ===============================
TAM_MEN = 2
VER = 2
STORE = 7
FILLER = 2
TERMINAL = 2
MESSAGE = 1
TRX_NUM = 3
SEQ = 2
PLAN = 1
STAT_CODE = 1
IND_STAT = 1

FILLER_AUT_DEFAULT = 35
AUT = 38

BYTES_MIN_TRAMA = 14
# ===============================
# CATÁLOGO DE PLANES
# ===============================
CATALOGO_PLANES = {
    "0-0": "Cheques",
    "15-0": "Venta Empleado",
    "16-0": "Consulta Nip",
    "19-0": "Carga llaves internas",
    "19-1": "Carga llaves internas",
    "23-0": "Venta Mon Robustecido",
    "25-0": "Recarga Mon Robustecido",
    "26-0": "Devolución Mon Robustecido",
    "33-0": "Consulta Mon Integrado",
    "35-0": "Recarga Mon Integrado",
    "36-0": "Devolución Mon Integrado",
    "36-4": "Cancelación Dev Mon Integrado",
    "38-0": "Devolución Dilisa",
    "39-0": "Devolución LPC",
    "52-0": "Emisión Monedero",
    "69-0": "Carga llaves BBVA",
    "84-0": "Paquetería/MKP",
    "90-0": "Mesa Regalos/SDI",
    "92-0": "Cancelación Emisión Mon",
    "93-0": "Venta OMS Aprobada",
    "94-0": "Venta OMS Confirmada",
    "97-0": "Cancelación OMS",
    "2-4": "Cancelación Vales",
    "8-4": "Cancelación Dilisa",
    "11-4": "Cancelación LPC",
    "11-0": "Venta LPC",
    "14-0": "Venta AmEx",
    "14-4": "Cancelación Venta AmEx",
    "2-0": "Vales",
    "28-0": "Abono Dilisa",
    "28-4": "Cancelación Abono Dilisa",
    "29-0": "Abono LPC",
    "29-4": "Cancelación Abono LPC",
    "60-0": "Venta Externa",
    "60-1": "Nip Venta Externa",
    "60-4": "Reverso Externa",
    "60-6": "Devolución Externa",
    "60-7": "Cancelación Externa",
    "60-8": "Puntos BBVA",
    "60-9": "Nip Puntos BBVA",
    "61-0": "Puntos MasterCard",
    "61-1": "Nip Puntos MasterCard",
    "8-0": "Venta Dilisa",
    "8-1": "Nip Venta Dilisa"
}

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
def binario_a_int(bytes_hex):
    return int("".join(bytes_hex), 16)

def ebcdic_a_ascii(bytes_hex):
    return bytes(int(b, 16) for b in bytes_hex).decode("cp037", errors="ignore").strip()

def bcd_unpacked_a_int(bytes_hex):
    return int(bytes_hex[0][1])

def bcd_packed_a_str(bytes_hex):
    digits = ""
    for b in bytes_hex:
        val = int(b, 16)
        digits += f"{(val >> 4) & 0xF}{val & 0xF}"
    return digits

def bcd_packed_a_int(bytes_hex):
    return int(bcd_packed_a_str(bytes_hex))

def amount_a_decimal(bytes_hex):
    return bcd_packed_a_int(bytes_hex) / 100

# ===============================
# PARSEO BASE (NO TOCAR)
# ===============================
def extraer_campos(bytes_trama):
    i = 0
    c = {}

    c["tam_men"] = bytes_trama[i:i+TAM_MEN]; i += TAM_MEN
    c["ver"] = bytes_trama[i:i+VER]; i += VER
    c["store"] = bytes_trama[i:i+STORE]; i += STORE
    c["filler"] = bytes_trama[i:i+FILLER]; i += FILLER
    c["terminal"] = bytes_trama[i:i+TERMINAL]; i += TERMINAL
    c["message"] = bytes_trama[i:i+MESSAGE]; i += MESSAGE
    c["trx_num"] = bytes_trama[i:i+TRX_NUM]; i += TRX_NUM
    c["seq"] = bytes_trama[i:i+SEQ]; i += SEQ
    c["plan"] = bytes_trama[i:i+PLAN]; i += PLAN
    c["stat_code"] = bytes_trama[i:i+STAT_CODE]; i += STAT_CODE

    plan_int = bcd_packed_a_int(c["plan"])

    if plan_int == 60:
        c["ind_stat"] = bytes_trama[i:i+IND_STAT]
        i += IND_STAT
        amount_len = 5
    else:
        c["ind_stat"] = None
        amount_len = 4

    c["amount"] = bytes_trama[i:i+amount_len]
    return c

# ===============================
# AUTORIZACIÓN (NUEVO, AISLADO)
# ===============================
def extraer_autorizacion(linea: str, plan: int) -> str:
    if "Proxy->POS" not in linea or ":" not in linea:
        return ""

    bytes_hex = hex_bytes(linea)

    if plan in (19, 69):
        filler = 36
    elif plan in (60, 61):
        filler = 37
    else:
        filler = FILLER_AUT_DEFAULT

    inicio = filler
    fin = inicio + AUT

    if len(bytes_hex) < fin:
        return ""

    raw = bytes_hex[inicio:fin]
    texto = ebcdic_a_ascii(raw)

    return "".join(c for c in texto if c.isprintable()).strip()

# ===============================
# REGLAS DE NEGOCIO
# ===============================
def construir_registro(c, autorizacion):
    message = bcd_unpacked_a_int(c["message"])
    plan = bcd_packed_a_int(c["plan"])
    amount = amount_a_decimal(c["amount"])

    plan_key = f"{plan}-{message}"
    descripcion = CATALOGO_PLANES.get(plan_key, "DESCONOCIDO")
    boleta = bcd_packed_a_str(c["trx_num"]).lstrip("01") or "0"

    r = {
        "plan": plan_key,
        "descripcion": descripcion,
        "devolucion": 0.00,
        "venta": 0.00,
        "tienda": ebcdic_a_ascii(c["store"]),
        "terminal": binario_a_int(c["terminal"]),
        "boleta": boleta,
        "autorizacion": autorizacion,
    }

    if plan in (26, 36, 38, 39, 92, 97):
        r["devolucion"] = amount
    elif message in (4, 6, 7):
        r["devolucion"] = amount
    elif message in (0, 1, 8, 9):
        r["venta"] = amount

    return r

# ===============================
# PROCESO PRINCIPAL
# ===============================
def es_linea_proxy_b24(linea: str) -> bool:
    return "Proxy->B24" in linea
                
def trama_min_valida(bytes_hex: list[str]) -> bool:                
    return len(bytes_hex) >= BYTES_MIN_TRAMA

def procesar_csv(entrada, salida):
    with open(entrada, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    with open(salida, "w", encoding="utf-8") as out:
        out.write("Plan;Descripcion;Devolucion;Venta;Tienda;Terminal;Boleta\n")

        for linea in lineas:
            if not es_linea_proxy_b24(linea):
                continue

            bytes_trama = hex_bytes(linea)
            if not trama_min_valida(bytes_trama):
                continue

            campos = extraer_campos(bytes_trama)
            plan_int = bcd_packed_a_int(campos["plan"])

            autorizacion = extraer_autorizacion(linea, plan_int)
            r = construir_registro(campos, autorizacion)

            out.write(
                f"{r['plan']};{r['descripcion']};"
                f"{r['devolucion']:.2f};{r['venta']:.2f};"
                f"{r['tienda']};{r['terminal']};"
                f"{r['boleta']}\n"
            )

    print(f"Archivo generado correctamente: {salida}")

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    procesar_csv(
        "tramas_18-01-26_1500.csv",
        "monitor_18-01-26_1500.csv"
    )