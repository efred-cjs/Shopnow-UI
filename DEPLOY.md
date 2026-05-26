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
- `STORAGE_BACKEND=csv`: usa archivos CSV locales
- `STORAGE_BACKEND=postgres`: usa Postgres si tambien existe `DATABASE_URL`
- `DATABASE_URL`: cadena de conexion de Postgres
- `DATABASE_SSLMODE=require`: recomendado para Render Postgres
- `CLIENTES_CSV`, `PRODUCTOS_CSV`, `INVENTARIO_CSV`, `PEDIDOS_CSV`: permiten apuntar a otras rutas CSV si lo necesitas

## Modo local con CSV

No definas `DATABASE_URL` y deja:

```bash
set STORAGE_BACKEND=csv
```

Con eso los cambios se quedan en los archivos CSV locales.

## Modo local con Postgres

Define la conexion en tu terminal o en un `.env` local que no se sube a Git:

```bash
set STORAGE_BACKEND=postgres
set DATABASE_URL=postgresql://USUARIO:CONTRASENA@HOST:5432/BASE_DE_DATOS
set DATABASE_SSLMODE=require
```

El proyecto crea automaticamente las tablas `clientes`, `productos`, `inventario` y `pedidos` si no existen.

## Arranque sin Docker

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Que hace esta version

- Sirve la interfaz grafica y la API desde el mismo proceso.
- Mantiene los endpoints de clientes, productos, inventario y pedidos.
- Puede trabajar con CSV local o Postgres por variables de entorno.
- Ya no depende de desplegar cuatro servicios separados para funcionar en Render.
