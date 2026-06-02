import argparse
import queue
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from protocolo import ENCODING, enviar_json_linea, recibir_json_linea


HOST_DEFAULT = "127.0.0.1"
PORT_DEFAULT = 5000
WORKERS_DEFAULT = 4


@dataclass
class ClienteConectado:
    conexion: socket.socket
    direccion: tuple
    send_lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class TareaDistribuida:
    tarea_id: str
    operacion: str
    datos: object
    cliente: ClienteConectado
    recibida_en: float


def fecha_actual():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parsear_numeros(datos):
    if isinstance(datos, list):
        valores = datos
    elif isinstance(datos, str):
        valores = [numero.strip() for numero in datos.split(",") if numero.strip()]
    else:
        raise ValueError("La operacion sumar requiere una lista o texto con numeros separados por coma")

    if not valores:
        raise ValueError("Debe enviar al menos un numero")

    return [float(valor) for valor in valores]


def procesar_tarea(operacion, datos):
    if operacion == "sumar":
        numeros = parsear_numeros(datos)
        return {
            "numeros": numeros,
            "total": sum(numeros),
            "cantidad": len(numeros),
        }

    if operacion == "contar_palabras":
        texto = str(datos)
        palabras = [palabra for palabra in texto.split() if palabra]
        return {
            "texto": texto,
            "palabras": len(palabras),
            "caracteres": len(texto),
        }

    if operacion == "mayusculas":
        return {"texto": str(datos).upper()}

    if operacion == "crear_tarea":
        if not isinstance(datos, dict):
            raise ValueError("crear_tarea requiere un objeto con titulo y descripcion")

        titulo = str(datos.get("titulo", "")).strip()
        descripcion = str(datos.get("descripcion", "")).strip()

        if not titulo:
            raise ValueError("El titulo de la tarea es obligatorio")

        return {
            "titulo": titulo,
            "descripcion": descripcion,
            "estado": "pendiente",
            "creada_en": fecha_actual(),
        }

    if operacion == "dormir":
        segundos = float(datos)
        segundos = max(0.0, min(segundos, 10.0))
        time.sleep(segundos)
        return {"segundos": segundos, "mensaje": "Tarea lenta completada"}

    raise ValueError(f"Operacion no soportada: {operacion}")


def worker_loop(nombre_worker, cola_tareas, detener_evento):
    print(f"[{nombre_worker}] listo para procesar tareas")

    while not detener_evento.is_set():
        try:
            tarea = cola_tareas.get(timeout=0.5)
        except queue.Empty:
            continue

        inicio = time.perf_counter()

        try:
            resultado = procesar_tarea(tarea.operacion, tarea.datos)
            duracion_ms = round((time.perf_counter() - inicio) * 1000, 2)
            espera_ms = round((inicio - tarea.recibida_en) * 1000, 2)

            respuesta = {
                "tipo": "resultado",
                "tarea_id": tarea.tarea_id,
                "estado": "completada",
                "worker": nombre_worker,
                "operacion": tarea.operacion,
                "resultado": resultado,
                "espera_ms": espera_ms,
                "duracion_ms": duracion_ms,
            }
        except Exception as error:
            respuesta = {
                "tipo": "error",
                "tarea_id": tarea.tarea_id,
                "estado": "fallida",
                "worker": nombre_worker,
                "operacion": tarea.operacion,
                "mensaje": str(error),
            }

        try:
            enviar_json_linea(tarea.cliente.conexion, respuesta, tarea.cliente.send_lock)
        except OSError:
            print(f"[{nombre_worker}] no se pudo enviar respuesta a {tarea.cliente.direccion}")
        finally:
            cola_tareas.task_done()


def iniciar_workers(cantidad, cola_tareas, detener_evento):
    workers = []

    for indice in range(1, cantidad + 1):
        nombre_worker = f"worker-{indice}"
        hilo = threading.Thread(
            target=worker_loop,
            args=(nombre_worker, cola_tareas, detener_evento),
            daemon=True,
        )
        hilo.start()
        workers.append(hilo)

    return workers


def manejar_cliente(conexion, direccion, cola_tareas):
    cliente = ClienteConectado(conexion=conexion, direccion=direccion)
    print(f"[CLIENTE] conectado desde {direccion[0]}:{direccion[1]}")

    try:
        enviar_json_linea(
            conexion,
            {
                "tipo": "conexion",
                "mensaje": "Conectado al servidor distribuido PFO 3",
                "fecha": fecha_actual(),
            },
            cliente.send_lock,
        )

        archivo = conexion.makefile("r", encoding=ENCODING, newline="\n")

        while True:
            try:
                mensaje = recibir_json_linea(archivo)
            except ValueError as error:
                enviar_json_linea(
                    conexion,
                    {"tipo": "error", "mensaje": f"JSON invalido: {error}"},
                    cliente.send_lock,
                )
                continue

            if mensaje is None:
                break

            tipo = mensaje.get("tipo")

            if tipo == "fin":
                enviar_json_linea(
                    conexion,
                    {"tipo": "desconexion", "mensaje": "Conexion finalizada"},
                    cliente.send_lock,
                )
                break

            if tipo != "tarea":
                enviar_json_linea(
                    conexion,
                    {"tipo": "error", "mensaje": "El mensaje debe tener tipo 'tarea'"},
                    cliente.send_lock,
                )
                continue

            operacion = mensaje.get("operacion")

            if not operacion:
                enviar_json_linea(
                    conexion,
                    {"tipo": "error", "mensaje": "Debe indicar una operacion"},
                    cliente.send_lock,
                )
                continue

            tarea = TareaDistribuida(
                tarea_id=mensaje.get("tarea_id") or str(uuid.uuid4()),
                operacion=operacion,
                datos=mensaje.get("datos"),
                cliente=cliente,
                recibida_en=time.perf_counter(),
            )
            cola_tareas.put(tarea)
            print(f"[COLA] tarea {tarea.tarea_id} recibida ({operacion}) desde {direccion}")

    except ConnectionResetError:
        print(f"[CLIENTE] conexion interrumpida por {direccion}")
    except OSError as error:
        print(f"[CLIENTE] error de socket con {direccion}: {error}")
    finally:
        conexion.close()
        print(f"[CLIENTE] desconectado {direccion}")


def iniciar_servidor(host, port, cantidad_workers):
    cola_tareas = queue.Queue()
    detener_evento = threading.Event()
    iniciar_workers(cantidad_workers, cola_tareas, detener_evento)

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor.bind((host, port))
        servidor.listen(20)
        print(f"[SERVIDOR] escuchando en {host}:{port}")
        print(f"[SERVIDOR] workers activos: {cantidad_workers}")

        while True:
            conexion, direccion = servidor.accept()
            hilo_cliente = threading.Thread(
                target=manejar_cliente,
                args=(conexion, direccion, cola_tareas),
                daemon=True,
            )
            hilo_cliente.start()

    except KeyboardInterrupt:
        print("\n[SERVIDOR] apagando servidor")
    finally:
        detener_evento.set()
        servidor.close()


def construir_parser():
    parser = argparse.ArgumentParser(description="Servidor distribuido PFO 3 por sockets")
    parser.add_argument("--host", default=HOST_DEFAULT, help="Host donde escucha el servidor")
    parser.add_argument("--port", type=int, default=PORT_DEFAULT, help="Puerto TCP del servidor")
    parser.add_argument("--workers", type=int, default=WORKERS_DEFAULT, help="Cantidad de workers")
    return parser


def main():
    args = construir_parser().parse_args()
    iniciar_servidor(args.host, args.port, args.workers)


if __name__ == "__main__":
    main()
