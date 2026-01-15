BYTES_ERROR = 14
BYTES_SIN_RED = 34
BYTES_VALIDOS = BYTES_SIN_RED

def extraer_tramas(info: bytes) -> list:
    """
    Extrae tramas de archivo descargado en binario desde debugger.
    La primera trama se toma desde el byte 21 hasta el primer header_inicio.
    Después todas las demás tramas comienzan después de los 25 bytes del header de cada trama.
    """

    header_inicio = bytes([0x0D, 0x0A, 0x30, 0x0D, 0x0A])
    header_total = 25
    tramas = []
    size = len(info)
    # --- 1) PRIMERA TRAMA ---
    primer_header = info.find(header_inicio, 20)

    if primer_header == -1:
        tramas.append(info[20:])
        return tramas

    primera_trama = info[20:primer_header]
    tramas.append(primera_trama)
    # --- 2) SIGUIENTES TRAMAS ---
    i = primer_header

    while i < size:
        pos = info.find(header_inicio, i)
        if pos == -1:
            break

        siguiente = info.find(header_inicio, pos + len(header_inicio))

        if siguiente == -1:
            # última trama → va hasta el final
            trama = info[pos + header_total:]
            tramas.append(trama)
            break
        # CORRECCIÓN IMPORTANTE:
        # recortar los 25 bytes del header
        trama = info[pos + header_total : siguiente]
        tramas.append(trama)

        i = siguiente

    return tramas

def tramas_validas(longitud):
    return longitud > BYTES_VALIDOS

DIRECCIONES = {
        0: ("POS", "Proxy", "REQ"),
        1: ("Proxy", "B24", "REQ"),
        2: ("B24", "Proxy", "RESP"),
        3: ("Proxy", "POS", "RESP"),
    }
def request_response(linea: int) -> tuple[str, str, str]:
    posicion = (linea -1) % 4
    return DIRECCIONES[posicion]

def byte_a_hex(trama: bytes) -> str:
    return " ".join(f"{b:02X}" for b in trama)

def construir_linea_tx(
    indice_trx: int,
    origen: str,
    destino: str,
    tipo: str,
    longitud: int,
    hex_str: str
) -> str:
    return (
        f"TX{indice_trx};"
        f"{origen}->{destino};"
        f"{tipo};"
        f"{longitud}: "
        f"{hex_str}\n"
    )

def procesar_archivo(archivo_bin, archivo_salida):

    with open(archivo_bin, "rb") as f:
        data = f.read()

    print(f"Archivo leído correctamente ({len(data)} bytes).")

    tramas = extraer_tramas(data)

    with open(archivo_salida, "w", encoding="utf-8") as out:
        linea = 0  # contador solo de tramas válidas

        for trama in tramas:
            longitud = len(trama)

            # REGLA 1: descartar tramas cortas
            if not tramas_validas(longitud):
                continue

            linea += 1
            origen, destino, tipo = request_response(linea)

            hex_str = byte_a_hex(trama)

            indice_tx = (linea - 1) // 4 + 1

            linea_salida = construir_linea_tx(
                indice_tx,
                origen,
                destino,
                tipo,
                longitud,
                hex_str
            )

            out.write(linea_salida)

    print(f"Listo. Se escribieron {linea} tramas válidas en {archivo_salida}")

if __name__ == "__main__":
    procesar_archivo(
        "bytes-260113_1600.log",
        "tramas_13-01-26_1600.csv"
    )