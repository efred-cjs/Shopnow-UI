# ShopnowUI como un solo servicio

Este proyecto queda preparado para ejecutarse como una sola app FastAPI con interfaz web incluida.

## Levantar localmente con Docker

```bash
docker compose up --build
```

## URL local

```text
http://localhost:8000
```

Tambien quedan disponibles:

```text
http://localhost:8000/docs
http://localhost:8000/health
```

## Variables utiles

- `PORT`: puerto de arranque del contenedor
- `ENABLE_RABBITMQ=false`: desactiva RabbitMQ para el flujo unificado
- `CLIENTES_CSV`, `PRODUCTOS_CSV`, `INVENTARIO_CSV`, `PEDIDOS_CSV`: permiten apuntar a otras rutas CSV si lo necesitas

## Arranque sin Docker

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Que hace esta version

- Sirve la interfaz grafica y la API desde el mismo proceso.
- Mantiene los endpoints de clientes, productos, inventario y pedidos.
- Ya no depende de desplegar cuatro servicios separados para funcionar en Render.
