# ShopnowUI en Render como un solo servicio

Esta version queda lista para desplegarse como un unico `Web Service` basado en Docker.

## Resumen del enfoque

- La interfaz web y la API viven en la misma app FastAPI.
- `clientes`, `productos`, `inventario` y `pedidos` comparten proceso y almacenamiento CSV.
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

No necesitas definir `PORT`; Render la inyecta y el Dockerfile ya la respeta.

## URLs que debes probar despues del deploy

- `https://TU-SERVICIO.onrender.com/`
- `https://TU-SERVICIO.onrender.com/docs`
- `https://TU-SERVICIO.onrender.com/health`

## Flujo recomendado de prueba

1. Entra a la interfaz principal.
2. Registra o inicia sesion.
3. Crea un cliente si hace falta.
4. Crea un producto.
5. Inicializa inventario para ese producto.
6. Registra un pedido.
7. Verifica que el stock baje en inventario y que el pedido aparezca en el historial.

## Importante

En Render Free el filesystem sigue siendo temporal. Los CSV sirven para demo, pruebas y exposicion, pero pueden perderse si el servicio se reinicia o se vuelve a desplegar.

## Siguiente paso si quieres persistencia real

El cambio correcto seria mover los CSV a una base de datos persistente. Para esta entrega, el proyecto ya queda listo para Render como un solo servicio funcional.
