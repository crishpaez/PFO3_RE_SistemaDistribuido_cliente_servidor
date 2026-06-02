import json


ENCODING = "utf-8"


def enviar_json_linea(conexion, mensaje, lock=None):
    datos = json.dumps(mensaje, ensure_ascii=False) + "\n"
    payload = datos.encode(ENCODING)

    if lock is None:
        conexion.sendall(payload)
        return

    with lock:
        conexion.sendall(payload)


def recibir_json_linea(archivo):
    linea = archivo.readline()

    if not linea:
        return None

    return json.loads(linea)
