from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
import csv
import json

from fastapi import Body, Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
import pika

from config import get_data_file, get_rabbitmq_connection_parameters, is_rabbitmq_enabled
from datosCent import Cliente, ClienteLogin, ClienteRegistro, ClienteUpdate, bd_clientes

SECRET_KEY = "tu_llave_secreta_super_segura_123"
ALGORITHM = "HS256"
TOKEN_DURATION_HOURS = 8
security = HTTPBearer()
FILE_NAME = get_data_file("CLIENTES_CSV", "clientes.csv")
HEADERS = ["id_cliente", "nombre", "correo", "direccion", "telefono"]
UI_DIR = Path(__file__).resolve().parent / "web"

if not FILE_NAME.exists():
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADERS)

app = FastAPI(
    title="API de Clientes",
    description="Este es el servicio encargado del registro basico inicial de los clientes. \n\n"
    "Esta api actua como eje de nuestro programa para el seguimiento y modificacion de los clientes. \n\n"
    "Ejecutar en puerto 8000 y los demas servicios en su respectivo puerto tal como: Pedidos (8002) y Productos (8001)",
    version="2.3.0",
    contact={
        "name": "Efren Camilo Jimenez Suarez ISC, Tecnm Queretaro",
    },
)

app.mount("/ui-assets", StaticFiles(directory=UI_DIR), name="ui-assets")


def crear_token(cliente: Cliente):
    expira = datetime.now(timezone.utc) + timedelta(hours=TOKEN_DURATION_HOURS)
    payload = {
        "sub": cliente.nombre,
        "id_cliente": cliente.id_cliente,
        "correo": cliente.correo,
        "exp": expira,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def obtener_cliente_por_id(id_cliente: int):
    return next((c for c in bd_clientes if c.id_cliente == id_cliente), None)


def obtener_cliente_por_nombre(nombre: str):
    nombre_normalizado = nombre.strip().lower()
    return next((c for c in bd_clientes if c.nombre.strip().lower() == nombre_normalizado), None)


def construir_respuesta_autenticacion(cliente: Cliente, mensaje: str):
    token = crear_token(cliente)
    return {
        "token": token,
        "mensaje": mensaje,
        "cliente": cliente.dict(),
        "expira_en_horas": TOKEN_DURATION_HOURS,
    }


def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")

    cliente = obtener_cliente_por_id(payload.get("id_cliente", 0))
    if cliente is None:
        raise HTTPException(status_code=401, detail="El usuario del token ya no existe")

    return {"payload": payload, "cliente": cliente}


def enviar_evento(tipo_evento, data):
    if not is_rabbitmq_enabled():
        return
    try:
        connection = pika.BlockingConnection(get_rabbitmq_connection_parameters())
        channel = connection.channel()
        channel.queue_declare(queue="clientes", durable=True)

        mensaje = {
            "evento": tipo_evento,
            "data": data,
        }

        channel.basic_publish(
            exchange="",
            routing_key="clientes",
            body=json.dumps(mensaje),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
    except Exception as e:
        print("Error enviando a RabbitMQ:", e)


def guardar_clientes(clientes: List[Cliente]):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write("id_cliente,nombre,correo,direccion,telefono\n")
        for c in clientes:
            f.write(f"{c.id_cliente},{c.nombre},{c.correo},{c.direccion},{c.telefono}\n")


def registrar_cliente_en_memoria(nuevo_cliente: ClienteRegistro):
    if any(c.correo.strip().lower() == nuevo_cliente.correo.strip().lower() for c in bd_clientes):
        raise HTTPException(status_code=409, detail="Ya existe un cliente registrado con ese correo")

    nuevo_id = 1 if len(bd_clientes) == 0 else max(c.id_cliente for c in bd_clientes) + 1
    cliente = Cliente(
        id_cliente=nuevo_id,
        nombre=nuevo_cliente.nombre.strip(),
        correo=nuevo_cliente.correo.strip().lower(),
        direccion=nuevo_cliente.direccion.strip(),
        telefono=int(nuevo_cliente.telefono),
    )

    bd_clientes.append(cliente)
    guardar_clientes(bd_clientes)
    enviar_evento("cliente_creado", cliente.dict())
    return cliente


@app.get("/", include_in_schema=False)
def interfaz_login():
    return FileResponse(UI_DIR / "index.html")


@app.get("/health", tags=["Infra"])
def health_check():
    return {"status": "ok", "service": "clientes"}


@app.get("/clientes", response_model=List[Cliente], tags=["Clientes"])
def obtener_clientes():
    return bd_clientes


@app.get("/clientes_seguro", response_model=List[Cliente], tags=["Clientes"])
def obtener_clientes_seguro(token_data=Depends(verificar_token)):
    return bd_clientes


@app.get("/perfil", tags=["Autenticacion"])
def obtener_perfil(token_data=Depends(verificar_token)):
    return {
        "autenticado": True,
        "cliente": token_data["cliente"].dict(),
        "token": token_data["payload"],
    }


@app.post("/clientes", status_code=status.HTTP_201_CREATED, tags=["Clientes"])
def registrar_cliente(nuevo_cliente: ClienteRegistro):
    cliente = registrar_cliente_en_memoria(nuevo_cliente)
    return construir_respuesta_autenticacion(cliente, "Cliente registrado y autenticado con exito")


@app.post("/registro", status_code=status.HTTP_201_CREATED, tags=["Autenticacion"])
def registro_auth(nuevo_cliente: ClienteRegistro):
    cliente = registrar_cliente_en_memoria(nuevo_cliente)
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
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if str(cliente.telefono) != str(telefono).strip():
        raise HTTPException(status_code=401, detail="Telefono incorrecto")

    return construir_respuesta_autenticacion(cliente, "Logueado con exito")


@app.delete("/clientes/{id_cliente}", tags=["Clientes"])
def eliminar_cliente(id_cliente: int):
    borrar_cliente = next((c for c in bd_clientes if c.id_cliente == id_cliente), None)
    if not borrar_cliente:
        raise HTTPException(status_code=404, detail=f"No se encontraron clientes con este ID {id_cliente}")

    bd_clientes.remove(borrar_cliente)
    guardar_clientes(bd_clientes)
    enviar_evento("cliente_eliminado", {"id_cliente": id_cliente})
    return {"Alerta": f"Cliente {id_cliente} eliminado exitosamente de la memoria"}


@app.patch("/clientes/{id_cliente}", tags=["Clientes"])
def actualizar_cliente(id_cliente: int, update_datos: ClienteUpdate):
    cliente_update = next((c for c in bd_clientes if c.id_cliente == id_cliente), None)

    if not cliente_update:
        raise HTTPException(status_code=404, detail=f"No se encontro el cliente con ID {id_cliente}")

    if update_datos.nombre is not None:
        cliente_update.nombre = update_datos.nombre
    if update_datos.correo is not None:
        cliente_update.correo = update_datos.correo
    if update_datos.direccion is not None:
        cliente_update.direccion = update_datos.direccion
    if update_datos.telefono is not None:
        cliente_update.telefono = update_datos.telefono

    guardar_clientes(bd_clientes)
    enviar_evento("cliente_actualizado", cliente_update.dict())
    return {"mensaje": "Cliente actualizado correctamente", "datos": cliente_update}
