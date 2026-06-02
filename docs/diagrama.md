# Diagrama del sistema distribuido

```mermaid
flowchart LR
    subgraph Clientes
        web["Cliente web"]
        movil["Cliente movil"]
        cli["Cliente Python"]
    end

    lb["Balanceador de carga<br/>Nginx / HAProxy"]

    subgraph Servidores["Capa de servidores workers"]
        s1["Servidor Worker 1<br/>Socket TCP<br/>Pool de hilos"]
        s2["Servidor Worker 2<br/>Socket TCP<br/>Pool de hilos"]
        sn["Servidor Worker N<br/>Socket TCP<br/>Pool de hilos"]
    end

    rabbit["Cola de mensajes<br/>RabbitMQ"]

    subgraph Almacenamiento["Almacenamiento distribuido"]
        postgres["PostgreSQL<br/>datos transaccionales"]
        objstore["S3 / almacenamiento de objetos<br/>archivos y respaldos"]
    end

    web --> lb
    movil --> lb
    cli --> lb

    lb --> s1
    lb --> s2
    lb --> sn

    s1 <--> rabbit
    s2 <--> rabbit
    sn <--> rabbit

    rabbit --> postgres
    rabbit --> objstore
    s1 --> postgres
    s2 --> postgres
    sn --> postgres
```

## Descripcion breve

Los clientes se conectan al balanceador de carga, que reparte las conexiones entre varios servidores worker. Cada servidor mantiene un pool de hilos para procesar tareas concurrentes. RabbitMQ permite desacoplar tareas entre servidores y PostgreSQL/S3 representan el almacenamiento distribuido para datos y archivos.
