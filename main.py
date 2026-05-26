from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from fastapi import Body, Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
import pika

from config import get_rabbitmq_connection_parameters, is_rabbitmq_enabled
from datosCent import (
    Cliente,
    ClienteLogin,
    ClienteRegistro,
    ClienteUpdate,
    Inventario,
    InventarioAlta,
    InventarioRegistro,
    InventarioUpdate,
    Pedido,
    PedidoRegistro,
    PedidoUpdate,
    Producto,
    ProductoRegistro,
    ProductoUpdate,
    bd_clientes,
    bd_inventario,
    bd_pedidos,
    bd_productos,
    data_lock,
    guardar_clientes,
    guardar_inventarios,
    guardar_pedidos,
    guardar_productos,
    siguiente_id,
    sincronizar_archivos,
)


SECRET_KEY = "shopnowui_render_secret_key_2026"
ALGORITHM = "HS256"
TOKEN_DURATION_HOURS = 8
DEFAULT_ORDER_STATUS = "COMPLETADO"
UI_DIR = Path(__file__).resolve().parent / "web"
security = HTTPBearer()

app = FastAPI(
    title="Shopnow Unified API",
    description="Servicio unificado para clientes, productos, inventario, pedidos e interfaz web.",
    version="3.0.0",
)

app.mount("/ui-assets", StaticFiles(directory=UI_DIR), name="ui-assets")


@app.on_event("startup")
def startup_sync_files() -> None:
    sincronizar_archivos()


def model_dump_compat(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def crear_token(cliente: Cliente) -> str:
    expira = datetime.now(timezone.utc) + timedelta(hours=TOKEN_DURATION_HOURS)
    payload = {
        "sub": cliente.nombre,
        "id_cliente": cliente.id_cliente,
        "correo": cliente.correo,
        "exp": expira,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def obtener_cliente_por_id(id_cliente: int) -> Cliente | None:
    return next((cliente for cliente in bd_clientes if cliente.id_cliente == id_cliente), None)


def obtener_cliente_por_nombre(nombre: str) -> Cliente | None:
    nombre_normalizado = nombre.strip().lower()
    return next((cliente for cliente in bd_clientes if cliente.nombre.strip().lower() == nombre_normalizado), None)


def obtener_producto_por_id(id_producto: int) -> Producto | None:
    return next((producto for producto in bd_productos if producto.id_producto == id_producto), None)


def obtener_inventario_por_producto(id_producto: int) -> Inventario | None:
    return next((item for item in bd_inventario if item.id_producto == id_producto), None)


def obtener_pedido_por_id(id_pedido: int) -> Pedido | None:
    return next((pedido for pedido in bd_pedidos if pedido.id_pedido == id_pedido), None)


def serializar_cliente(cliente: Cliente) -> dict:
    return model_dump_compat(cliente)


def serializar_producto(producto: Producto, version: str = "default") -> dict:
    base = {
        "id_producto": producto.id_producto,
        "descripcion": producto.descripcion,
        "activo": producto.activo,
    }
    precio = round(float(producto.precio), 2)

    if version == "v2":
        return {
            **base,
            "costo_unitario": precio,
        }

    if version == "v1":
        return {
            **base,
            "precio": precio,
        }

    return {
        **base,
        "precio": precio,
        "costo": precio,
        "costo_unitario": precio,
    }


def serializar_inventario(item: Inventario) -> dict:
    producto = obtener_producto_por_id(item.id_producto)
    payload = {
        "id_producto": item.id_producto,
        "cantidad": item.cantidad,
        "descripcion": producto.descripcion if producto else "Producto sin catalogo",
        "activo": producto.activo if producto else False,
    }
    if producto:
        payload["precio"] = round(float(producto.precio), 2)
    return payload


def serializar_pedido(pedido: Pedido) -> dict:
    cliente = obtener_cliente_por_id(pedido.id_cliente)
    producto = obtener_producto_por_id(pedido.id_producto)
    precio_unitario = round(float(pedido.costo) / pedido.cantidad, 2) if pedido.cantidad else 0.0
    return {
        "id_pedido": pedido.id_pedido,
        "id_producto": pedido.id_producto,
        "id_cliente": pedido.id_cliente,
        "cantidad": pedido.cantidad,
        "costo": round(float(pedido.costo), 2),
        "estado": pedido.estado,
        "created_at": pedido.created_at,
        "precio_unitario": precio_unitario,
        "cliente_nombre": cliente.nombre if cliente else "Cliente no disponible",
        "producto_descripcion": producto.descripcion if producto else "Producto no disponible",
    }


def construir_respuesta_autenticacion(cliente: Cliente, mensaje: str) -> dict:
    return {
        "token": crear_token(cliente),
        "mensaje": mensaje,
        "cliente": serializar_cliente(cliente),
        "expira_en_horas": TOKEN_DURATION_HOURS,
    }


def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")

    cliente = obtener_cliente_por_id(payload.get("id_cliente", 0))
    if cliente is None or not cliente.activo:
        raise HTTPException(status_code=401, detail="El usuario del token ya no esta activo")

    return {"payload": payload, "cliente": cliente}


def publicar_evento(queue_name: str, evento: str, data: dict) -> None:
    if not is_rabbitmq_enabled():
        return

    try:
        connection = pika.BlockingConnection(get_rabbitmq_connection_parameters())
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps({"evento": evento, "data": data}),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
    except Exception as exc:
        print(f"RabbitMQ no disponible para {queue_name}: {exc}")


def validar_cliente_activo(id_cliente: int) -> Cliente:
    cliente = obtener_cliente_por_id(id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail="El cliente no existe.")
    if not cliente.activo:
        raise HTTPException(status_code=400, detail="El cliente esta inactivo.")
    return cliente


def validar_producto_activo(id_producto: int) -> Producto:
    producto = obtener_producto_por_id(id_producto)
    if producto is None:
        raise HTTPException(status_code=404, detail="El producto no existe.")
    if not producto.activo:
        raise HTTPException(status_code=400, detail="El producto esta inactivo.")
    return producto


def normalizar_estado(estado: str | None) -> str:
    if not estado:
        return DEFAULT_ORDER_STATUS
    return estado.strip().upper()


@app.get("/", include_in_schema=False)
def interfaz_principal():
    return FileResponse(UI_DIR / "index.html")


@app.get("/health", tags=["Infra"])
def health_check():
    return {
        "status": "ok",
        "service": "shopnowui",
        "clientes": len(bd_clientes),
        "productos": len(bd_productos),
        "inventario": len(bd_inventario),
        "pedidos": len(bd_pedidos),
    }


@app.post("/registro", status_code=status.HTTP_201_CREATED, tags=["Autenticacion"])
def registro_auth(nuevo_cliente: ClienteRegistro):
    with data_lock:
        if any(cliente.correo.strip().lower() == nuevo_cliente.correo.strip().lower() for cliente in bd_clientes):
            raise HTTPException(status_code=409, detail="Ya existe un cliente registrado con ese correo")

        nuevo_id = siguiente_id(bd_clientes, "id_cliente")
        cliente = Cliente(
            id_cliente=nuevo_id,
            nombre=nuevo_cliente.nombre.strip(),
            correo=nuevo_cliente.correo.strip().lower(),
            direccion=nuevo_cliente.direccion.strip(),
            telefono=nuevo_cliente.telefono.strip(),
            activo=bool(nuevo_cliente.activo),
        )
        bd_clientes.append(cliente)
        guardar_clientes(bd_clientes)

    publicar_evento("clientes", "cliente_creado", serializar_cliente(cliente))
    return construir_respuesta_autenticacion(cliente, "Registro completado con exito")


@app.post("/login", tags=["Autenticacion"])
def login(
    credenciales: ClienteLogin | None = Body(default=None),
    nombre: str | None = None,
    telefono: str | None = None,
):
    if credenciales is not None:
        nombre = credenciales.nombre
        telefono = credenciales.telefono

    if not nombre or not telefono:
        raise HTTPException(status_code=422, detail="Debes enviar nombre y telefono")

    cliente = obtener_cliente_por_nombre(nombre)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if not cliente.activo:
        raise HTTPException(status_code=403, detail="El cliente esta dado de baja")
    if cliente.telefono.strip() != str(telefono).strip():
        raise HTTPException(status_code=401, detail="Telefono incorrecto")

    return construir_respuesta_autenticacion(cliente, "Logueado con exito")


@app.get("/perfil", tags=["Autenticacion"])
def obtener_perfil(token_data=Depends(verificar_token)):
    return {
        "autenticado": True,
        "cliente": serializar_cliente(token_data["cliente"]),
        "token": token_data["payload"],
    }


@app.get("/panel/resumen", tags=["Panel"])
def panel_resumen(token_data=Depends(verificar_token)):
    return {
        "cliente_actual": serializar_cliente(token_data["cliente"]),
        "clientes": [serializar_cliente(cliente) for cliente in bd_clientes],
        "productos": [serializar_producto(producto) for producto in bd_productos],
        "inventario": [serializar_inventario(item) for item in bd_inventario],
        "pedidos": [serializar_pedido(pedido) for pedido in bd_pedidos],
    }


@app.get("/clientes", tags=["Clientes"])
def obtener_clientes(token_data=Depends(verificar_token)):
    return [serializar_cliente(cliente) for cliente in bd_clientes]


@app.post("/clientes", status_code=status.HTTP_201_CREATED, tags=["Clientes"])
def registrar_cliente(nuevo_cliente: ClienteRegistro, token_data=Depends(verificar_token)):
    with data_lock:
        if any(cliente.correo.strip().lower() == nuevo_cliente.correo.strip().lower() for cliente in bd_clientes):
            raise HTTPException(status_code=409, detail="Ya existe un cliente registrado con ese correo")

        cliente = Cliente(
            id_cliente=siguiente_id(bd_clientes, "id_cliente"),
            nombre=nuevo_cliente.nombre.strip(),
            correo=nuevo_cliente.correo.strip().lower(),
            direccion=nuevo_cliente.direccion.strip(),
            telefono=nuevo_cliente.telefono.strip(),
            activo=bool(nuevo_cliente.activo),
        )
        bd_clientes.append(cliente)
        guardar_clientes(bd_clientes)

    publicar_evento("clientes", "cliente_creado", serializar_cliente(cliente))
    return {"mensaje": "Cliente registrado exitosamente", "datos": serializar_cliente(cliente)}


@app.patch("/clientes/{id_cliente}", tags=["Clientes"])
def actualizar_cliente(id_cliente: int, update_datos: ClienteUpdate, token_data=Depends(verificar_token)):
    cliente = obtener_cliente_por_id(id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail=f"No se encontro el cliente con ID {id_cliente}")

    with data_lock:
        if update_datos.nombre is not None:
            cliente.nombre = update_datos.nombre.strip()
        if update_datos.correo is not None:
            correo_normalizado = update_datos.correo.strip().lower()
            if any(
                item.id_cliente != id_cliente and item.correo.strip().lower() == correo_normalizado
                for item in bd_clientes
            ):
                raise HTTPException(status_code=409, detail="Ya existe otro cliente con ese correo")
            cliente.correo = correo_normalizado
        if update_datos.direccion is not None:
            cliente.direccion = update_datos.direccion.strip()
        if update_datos.telefono is not None:
            cliente.telefono = update_datos.telefono.strip()
        if update_datos.activo is not None:
            cliente.activo = update_datos.activo
        guardar_clientes(bd_clientes)

    publicar_evento("clientes", "cliente_actualizado", serializar_cliente(cliente))
    return {"mensaje": "Cliente actualizado correctamente", "datos": serializar_cliente(cliente)}


@app.delete("/clientes/{id_cliente}", tags=["Clientes"])
def eliminar_cliente(id_cliente: int, token_data=Depends(verificar_token)):
    cliente = obtener_cliente_por_id(id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail=f"No se encontro el cliente con ID {id_cliente}")

    with data_lock:
        cliente.activo = False
        guardar_clientes(bd_clientes)

    publicar_evento("clientes", "cliente_desactivado", serializar_cliente(cliente))
    return {"mensaje": "Cliente dado de baja logicamente", "datos": serializar_cliente(cliente)}


@app.get("/productos", tags=["Productos"])
def obtener_productos(token_data=Depends(verificar_token)):
    return [serializar_producto(producto) for producto in bd_productos]


@app.get("/v1/productos", tags=["Productos"])
def obtener_productos_v1(token_data=Depends(verificar_token)):
    return [serializar_producto(producto, version="v1") for producto in bd_productos]


@app.get("/v2/productos", tags=["Productos"])
def obtener_productos_v2(token_data=Depends(verificar_token)):
    return [serializar_producto(producto, version="v2") for producto in bd_productos]


@app.post("/productos", status_code=status.HTTP_201_CREATED, tags=["Productos"])
def registrar_producto(nuevo_producto: ProductoRegistro, token_data=Depends(verificar_token)):
    if nuevo_producto.precio in (None, 0):
        raise HTTPException(status_code=422, detail="Debes enviar precio, costo o costo_unitario")

    with data_lock:
        producto = Producto(
            id_producto=siguiente_id(bd_productos, "id_producto"),
            descripcion=nuevo_producto.descripcion.strip(),
            precio=float(nuevo_producto.precio),
            activo=bool(nuevo_producto.activo),
        )
        bd_productos.append(producto)
        guardar_productos(bd_productos)

    publicar_evento("productos", "producto_creado", serializar_producto(producto))
    return {"mensaje": "Producto registrado exitosamente", "datos": serializar_producto(producto)}


@app.post("/v1/productos", status_code=status.HTTP_201_CREATED, tags=["Productos"])
def registrar_producto_v1(nuevo_producto: ProductoRegistro, token_data=Depends(verificar_token)):
    return registrar_producto(nuevo_producto, token_data)


@app.post("/v2/productos", status_code=status.HTTP_201_CREATED, tags=["Productos"])
def registrar_producto_v2(nuevo_producto: ProductoRegistro, token_data=Depends(verificar_token)):
    return registrar_producto(nuevo_producto, token_data)


@app.patch("/productos/{id_producto}", tags=["Productos"])
def actualizar_producto(id_producto: int, update_datos: ProductoUpdate, token_data=Depends(verificar_token)):
    producto = obtener_producto_por_id(id_producto)
    if producto is None:
        raise HTTPException(status_code=404, detail=f"No se encontro el producto con ID {id_producto}")

    with data_lock:
        if update_datos.descripcion is not None:
            producto.descripcion = update_datos.descripcion.strip()
        if update_datos.precio is not None:
            producto.precio = float(update_datos.precio)
        if update_datos.activo is not None:
            producto.activo = update_datos.activo
        guardar_productos(bd_productos)

    publicar_evento("productos", "producto_actualizado", serializar_producto(producto))
    return {"mensaje": "Producto actualizado correctamente", "datos": serializar_producto(producto)}


@app.patch("/v1/productos/{id_producto}", tags=["Productos"])
def actualizar_producto_v1(id_producto: int, update_datos: ProductoUpdate, token_data=Depends(verificar_token)):
    return actualizar_producto(id_producto, update_datos, token_data)


@app.patch("/v2/productos/{id_producto}", tags=["Productos"])
def actualizar_producto_v2(id_producto: int, update_datos: ProductoUpdate, token_data=Depends(verificar_token)):
    return actualizar_producto(id_producto, update_datos, token_data)


@app.delete("/productos/{id_producto}", tags=["Productos"])
def eliminar_producto(id_producto: int, token_data=Depends(verificar_token)):
    producto = obtener_producto_por_id(id_producto)
    if producto is None:
        raise HTTPException(status_code=404, detail=f"No se encontro el producto con ID {id_producto}")

    with data_lock:
        producto.activo = False
        guardar_productos(bd_productos)

    publicar_evento("productos", "producto_desactivado", serializar_producto(producto))
    return {"mensaje": "Producto dado de baja logicamente", "datos": serializar_producto(producto)}


@app.delete("/v1/productos/{id_producto}", tags=["Productos"])
def eliminar_producto_v1(id_producto: int, token_data=Depends(verificar_token)):
    return eliminar_producto(id_producto, token_data)


@app.delete("/v2/productos/{id_producto}", tags=["Productos"])
def eliminar_producto_v2(id_producto: int, token_data=Depends(verificar_token)):
    return eliminar_producto(id_producto, token_data)


@app.get("/inventario", tags=["Inventario"])
def obtener_inventario(token_data=Depends(verificar_token)):
    return [serializar_inventario(item) for item in bd_inventario]


@app.post("/inventario", status_code=status.HTTP_201_CREATED, tags=["Inventario"])
def registrar_inventario(nuevo_registro: Inventario, token_data=Depends(verificar_token)):
    validar_producto_activo(nuevo_registro.id_producto)
    if obtener_inventario_por_producto(nuevo_registro.id_producto) is not None:
        raise HTTPException(status_code=400, detail="Ya existe inventario para este producto.")

    with data_lock:
        bd_inventario.append(Inventario(id_producto=nuevo_registro.id_producto, cantidad=nuevo_registro.cantidad))
        guardar_inventarios(bd_inventario)

    return {"mensaje": "Stock inicial registrado", "datos": serializar_inventario(obtener_inventario_por_producto(nuevo_registro.id_producto))}


@app.post("/inventario/alta", status_code=status.HTTP_201_CREATED, tags=["Inventario"])
def registrar_alta_inventario(datos: InventarioAlta, token_data=Depends(verificar_token)):
    return registrar_inventario(Inventario(id_producto=datos.id_producto, cantidad=datos.cantidad_inicial), token_data)


@app.patch("/inventario/{id_producto}", tags=["Inventario"])
def actualizar_inventario(id_producto: int, datos_nuevos: InventarioUpdate, token_data=Depends(verificar_token)):
    item_actual = obtener_inventario_por_producto(id_producto)
    if item_actual is None:
        raise HTTPException(status_code=404, detail=f"No hay inventario registrado para el producto {id_producto}")

    if datos_nuevos.cantidad is None:
        raise HTTPException(status_code=422, detail="Debes enviar una cantidad valida")

    with data_lock:
        item_actual.cantidad = datos_nuevos.cantidad
        guardar_inventarios(bd_inventario)

    return {"mensaje": "Stock actualizado correctamente", "datos": serializar_inventario(item_actual)}


@app.patch("/inventario/{id_producto}/agregar", tags=["Inventario"])
def agregar_stock(id_producto: int, datos: InventarioRegistro, token_data=Depends(verificar_token)):
    item_actual = obtener_inventario_por_producto(id_producto)
    if item_actual is None:
        raise HTTPException(status_code=404, detail="El producto no esta registrado en el inventario.")

    with data_lock:
        item_actual.cantidad += datos.cantidad
        guardar_inventarios(bd_inventario)

    return {"mensaje": "Stock agregado correctamente", "datos": serializar_inventario(item_actual)}


@app.put("/inventario/descontar/{id_producto}", tags=["Inventario"])
def descontar_stock(id_producto: int, orden: InventarioRegistro, token_data=Depends(verificar_token)):
    item_actual = obtener_inventario_por_producto(id_producto)
    if item_actual is None:
        raise HTTPException(status_code=404, detail="El producto no tiene stock registrado.")
    if item_actual.cantidad < orden.cantidad:
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Quedan {item_actual.cantidad}.")

    with data_lock:
        item_actual.cantidad -= orden.cantidad
        guardar_inventarios(bd_inventario)

    return {"mensaje": "Stock actualizado tras descuento", "stock_restante": item_actual.cantidad}


@app.get("/pedidos", tags=["Pedidos"])
def obtener_pedidos(token_data=Depends(verificar_token)):
    return [serializar_pedido(pedido) for pedido in bd_pedidos]


@app.post("/pedidos", status_code=status.HTTP_201_CREATED, tags=["Pedidos"])
def registrar_pedido(nuevo_pedido: PedidoRegistro, token_data=Depends(verificar_token)):
    validar_cliente_activo(nuevo_pedido.id_cliente)
    producto = validar_producto_activo(nuevo_pedido.id_producto)
    item_inventario = obtener_inventario_por_producto(nuevo_pedido.id_producto)

    if item_inventario is None:
        raise HTTPException(status_code=404, detail="El producto no tiene inventario registrado.")
    if item_inventario.cantidad < nuevo_pedido.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente para registrar el pedido.")

    costo_total = round(float(producto.precio) * nuevo_pedido.cantidad, 2)
    estado = normalizar_estado(nuevo_pedido.estado)

    with data_lock:
        item_inventario.cantidad -= nuevo_pedido.cantidad
        pedido = Pedido(
            id_pedido=siguiente_id(bd_pedidos, "id_pedido"),
            id_producto=nuevo_pedido.id_producto,
            id_cliente=nuevo_pedido.id_cliente,
            cantidad=nuevo_pedido.cantidad,
            costo=costo_total,
            estado=estado,
        )
        bd_pedidos.append(pedido)
        guardar_inventarios(bd_inventario)
        guardar_pedidos(bd_pedidos)

    publicar_evento("pedidos", "pedido_creado", serializar_pedido(pedido))
    return {"mensaje": "Pedido registrado correctamente", "datos": serializar_pedido(pedido)}


@app.patch("/pedidos/{id_pedido}", tags=["Pedidos"])
def actualizar_pedido(id_pedido: int, datos_nuevos: PedidoUpdate, token_data=Depends(verificar_token)):
    pedido = obtener_pedido_por_id(id_pedido)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    item_inventario = obtener_inventario_por_producto(pedido.id_producto)
    producto = obtener_producto_por_id(pedido.id_producto)
    if item_inventario is None or producto is None:
        raise HTTPException(status_code=404, detail="El pedido ya no tiene referencias validas")

    with data_lock:
        if datos_nuevos.cantidad is not None and datos_nuevos.cantidad != pedido.cantidad:
            diferencia = datos_nuevos.cantidad - pedido.cantidad

            if diferencia > 0 and item_inventario.cantidad < diferencia:
                raise HTTPException(status_code=400, detail="Stock insuficiente para aumentar el pedido.")

            item_inventario.cantidad -= diferencia
            pedido.cantidad = datos_nuevos.cantidad
            pedido.costo = round(float(producto.precio) * pedido.cantidad, 2)
            guardar_inventarios(bd_inventario)

        if datos_nuevos.estado is not None:
            pedido.estado = normalizar_estado(datos_nuevos.estado)

        guardar_pedidos(bd_pedidos)

    publicar_evento("pedidos", "pedido_actualizado", serializar_pedido(pedido))
    return {"mensaje": "Pedido actualizado", "datos": serializar_pedido(pedido)}

