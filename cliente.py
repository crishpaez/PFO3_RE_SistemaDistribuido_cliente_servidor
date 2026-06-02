import argparse
import json
import socket
import uuid

from protocolo import ENCODING, enviar_json_linea, recibir_json_linea


HOST_DEFAULT = "127.0.0.1"
PORT_DEFAULT = 5000


def conectar_cliente(host, port):
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect((host, port))
    archivo = cliente.makefile("r", encoding=ENCODING, newline="\n")
    bienvenida = recibir_json_linea(archivo)

    if bienvenida:
        print("[SERVIDOR]", json.dumps(bienvenida, ensure_ascii=True))

    return cliente, archivo


def imprimir_respuesta(respuesta):
    print(json.dumps(respuesta, indent=2, ensure_ascii=True))


def esperar_resultado(archivo, tarea_id):
    while True:
        respuesta = recibir_json_linea(archivo)

        if respuesta is None:
            raise ConnectionError("El servidor cerro la conexion")

        if respuesta.get("tipo") in ("resultado", "error") and respuesta.get("tarea_id") == tarea_id:
            return respuesta

        imprimir_respuesta(respuesta)


def enviar_tarea(cliente, archivo, operacion, datos):
    tarea_id = str(uuid.uuid4())
    mensaje = {
        "tipo": "tarea",
        "tarea_id": tarea_id,
        "operacion": operacion,
        "datos": datos,
    }

    enviar_json_linea(cliente, mensaje)
    return esperar_resultado(archivo, tarea_id)


def solicitar_datos_interactivos(opcion):
    if opcion == "1":
        numeros = input("Numeros separados por coma: ").strip()
        return "sumar", numeros

    if opcion == "2":
        texto = input("Texto a analizar: ").strip()
        return "contar_palabras", texto

    if opcion == "3":
        texto = input("Texto a convertir: ").strip()
        return "mayusculas", texto

    if opcion == "4":
        titulo = input("Titulo de la tarea: ").strip()
        descripcion = input("Descripcion: ").strip()
        return "crear_tarea", {"titulo": titulo, "descripcion": descripcion}

    if opcion == "5":
        segundos = input("Segundos de procesamiento simulado (0 a 10): ").strip()
        return "dormir", segundos

    return None, None


def menu_interactivo(cliente, archivo):
    while True:
        print("\n=== Cliente PFO 3 ===")
        print("1. Sumar numeros")
        print("2. Contar palabras")
        print("3. Convertir texto a mayusculas")
        print("4. Crear tarea")
        print("5. Simular tarea lenta")
        print("6. Salir")

        opcion = input("Seleccione una opcion: ").strip()

        if opcion == "6":
            enviar_json_linea(cliente, {"tipo": "fin"})
            respuesta = recibir_json_linea(archivo)
            if respuesta:
                imprimir_respuesta(respuesta)
            break

        operacion, datos = solicitar_datos_interactivos(opcion)

        if operacion is None:
            print("Opcion invalida")
            continue

        respuesta = enviar_tarea(cliente, archivo, operacion, datos)
        imprimir_respuesta(respuesta)


def datos_desde_argumentos(operacion, datos):
    if operacion == "crear_tarea":
        partes = [parte.strip() for parte in datos.split("|", maxsplit=1)]
        return {
            "titulo": partes[0],
            "descripcion": partes[1] if len(partes) > 1 else "",
        }

    if operacion == "sumar":
        return datos

    if operacion == "dormir":
        return datos

    return datos


def construir_parser():
    parser = argparse.ArgumentParser(description="Cliente PFO 3 por sockets")
    parser.add_argument("--host", default=HOST_DEFAULT, help="Host del servidor")
    parser.add_argument("--port", type=int, default=PORT_DEFAULT, help="Puerto TCP del servidor")
    parser.add_argument("--operacion", help="Operacion a ejecutar sin menu interactivo")
    parser.add_argument("--datos", default="", help="Datos de la tarea para modo no interactivo")
    return parser


def main():
    args = construir_parser().parse_args()
    cliente, archivo = conectar_cliente(args.host, args.port)

    try:
        if args.operacion:
            datos = datos_desde_argumentos(args.operacion, args.datos)
            respuesta = enviar_tarea(cliente, archivo, args.operacion, datos)
            imprimir_respuesta(respuesta)
            enviar_json_linea(cliente, {"tipo": "fin"})
        else:
            menu_interactivo(cliente, archivo)
    except OSError as error:
        print(f"[ERROR CLIENTE] {error}")
    finally:
        cliente.close()


if __name__ == "__main__":
    main()
