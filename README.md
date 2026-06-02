# PFO 3 - Rediseño como Sistema Distribuido Cliente-Servidor

## Descripcion

Este proyecto transforma los trabajos anteriores en una arquitectura distribuida basada en sockets. El servidor recibe tareas por TCP, las coloca en una cola interna y un pool de workers las procesa en paralelo. El cliente envia tareas y recibe los resultados por el mismo canal de socket.

La propuesta conecta con:

- PFO 1: comunicacion cliente-servidor mediante sockets TCP.
- https://github.com/crishpaez/pfo1-chat-cliente-servidor-sockets
- PFO 2: concepto de gestion de tareas y cliente de consola.
- https://github.com/crishpaez/PFO2_API_Tareas_Flask_SQLite

## Arquitectura solicitada

El diagrama esta disponible en [docs/diagrama.md](docs/diagrama.md).

Componentes incluidos en el diseno:

- Clientes moviles, web y cliente Python.
- Balanceador de carga Nginx/HAProxy.
- Servidores workers con pool de hilos.
- Cola de mensajes RabbitMQ para comunicacion entre servidores.
- Almacenamiento distribuido con PostgreSQL y S3.

En esta implementacion academica se ejecuta un servidor local con `queue.Queue` y `threading.Thread` para simular la cola y el pool de workers sin requerir servicios externos.

## Estructura

```text
.
|-- cliente.py
|-- servidor.py
|-- protocolo.py
|-- docs/
|   `-- diagrama.md
|-- README.md
`-- .gitignore
```

## Requisitos

- Python 3.10 o superior.
- No requiere librerias externas.

## Como ejecutar

Abrir una terminal y ejecutar el servidor:

```bash
python servidor.py
```

Por defecto escucha en:

```text
127.0.0.1:5000
```

En otra terminal ejecutar el cliente interactivo:

```bash
python cliente.py
```

Tambien se puede probar una tarea directamente:

```bash
python cliente.py --operacion sumar --datos "10,20,30"
```

## Opciones del servidor

```bash
python servidor.py --host 127.0.0.1 --port 5000 --workers 4
```

- `--host`: direccion donde escucha el servidor.
- `--port`: puerto TCP.
- `--workers`: cantidad de hilos workers que procesan tareas.

## Operaciones soportadas

| Operacion | Datos esperados | Resultado |
|---|---|---|
| `sumar` | Numeros separados por coma | Total y cantidad |
| `contar_palabras` | Texto | Cantidad de palabras y caracteres |
| `mayusculas` | Texto | Texto convertido a mayusculas |
| `crear_tarea` | Titulo y descripcion | Tarea normalizada con estado pendiente |
| `dormir` | Segundos entre 0 y 10 | Simula una tarea lenta |

## Protocolo de comunicacion

El cliente y el servidor intercambian JSON terminado en salto de linea.

Ejemplo de solicitud:

```json
{
  "tipo": "tarea",
  "tarea_id": "uuid",
  "operacion": "sumar",
  "datos": "1,2,3"
}
```

Ejemplo de respuesta:

```json
{
  "tipo": "resultado",
  "estado": "completada",
  "worker": "worker-1",
  "resultado": {
    "total": 6.0,
    "cantidad": 3
  }
}
```

## Autor

Humberto Cristian Paez
