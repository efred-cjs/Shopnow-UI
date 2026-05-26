# ShopnowUI en Render como un solo servicio

Esta version queda lista para desplegarse como un unico `Web Service` basado en Docker.

## Resumen del enfoque

- La interfaz web y la API viven en la misma app FastAPI.
- `clientes`, `productos`, `inventario` y `pedidos` comparten proceso.
- El almacenamiento puede ser Postgres en Render o CSV local.
- RabbitMQ queda desactivado en Render con `ENABLE_RABBITMQ=false`.
- El contenedor arranca con `uvicorn main:app`.

## Opcion 1: usar `render.yaml`

El repositorio ya incluye un archivo `render.yaml` con la definicion base del servicio.

Pasos:

1. Sube este repo a GitHub.
2. En Render crea un nuevo Blueprint o selecciona el repo.
3. Deja que Render detecte `render.yaml`.
4. Confirma el servicio `shopnowui`.
5. Revisa que la variable `ENABLE_RABBITMQ=false` quede aplicada.
6. Agrega `DATABASE_URL` como secreto usando la cadena de conexion de tu Postgres.

## Opcion 2: crear el servicio manualmente

Configura el servicio asi:

- Name: `shopnowui`
- Runtime: `Docker`
- Plan: `Free`
- Branch: la rama donde dejes estos cambios
- Dockerfile Path: `./Dockerfile`
- Docker Context: `.`
- Health Check Path: `/health`

Variables:

- `ENABLE_RABBITMQ=false`
- `DATABASE_URL=postgresql://USUARIO:CONTRASENA@HOST:5432/BASE_DE_DATOS`
- `DATABASE_SSLMODE=require`

No necesitas definir `PORT`; Render la inyecta y el Dockerfile ya la respeta.

## URLs que debes probar despues del deploy

- `https://TU-SERVICIO.onrender.com/`
- `https://TU-SERVICIO.onrender.com/docs`
- `https://TU-SERVICIO.onrender.com/health`

En `/health` debe aparecer `"storage":"postgres"` si `DATABASE_URL` quedo bien configurada.

## Flujo recomendado de prueba

1. Entra a la interfaz principal.
2. Registra o inicia sesion.
3. Crea un cliente si hace falta.
4. Crea un producto.
5. Inicializa inventario para ese producto.
6. Registra un pedido.
7. Verifica que el stock baje en inventario y que el pedido aparezca en el historial.

## Importante

Si usas Postgres, los datos quedan en la base de datos. Si desactivas `DATABASE_URL` o fuerzas `STORAGE_BACKEND=csv`, vuelves al modo local con archivos CSV.

## Siguiente paso si quieres persistencia real

La app ya tiene persistencia por Postgres. El siguiente paso natural seria mover validaciones o procedimientos especificos de negocio a SQL si tu profesor lo pide.
