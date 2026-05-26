from __future__ import annotations

import csv
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, root_validator

from config import get_data_file


data_lock = RLock()

CLIENTES_FILE = get_data_file("CLIENTES_CSV", "clientes.csv")
PRODUCTOS_FILE = get_data_file("PRODUCTOS_CSV", "productos.csv")
INVENTARIO_FILE = get_data_file("INVENTARIO_CSV", "inventario.csv")
PEDIDOS_FILE = get_data_file("PEDIDOS_CSV", "pedidos.csv")

CLIENTES_HEADERS = ["id_cliente", "nombre", "correo", "direccion", "telefono", "activo"]
PRODUCTOS_HEADERS = ["id_producto", "descripcion", "precio", "activo"]
INVENTARIO_HEADERS = ["id_producto", "cantidad"]
PEDIDOS_HEADERS = ["id_pedido", "id_producto", "id_cliente", "cantidad", "costo", "estado", "created_at"]


def _as_bool(value: Any, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si"}


def _as_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(value)


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _read_rows(path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with open(path, "r", newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        return list(reader)


def _write_rows(path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class Cliente(BaseModel):
    id_cliente: int
    nombre: str
    correo: EmailStr
    direccion: str
    telefono: str
    activo: bool = True


class ClienteRegistro(BaseModel):
    nombre: str
    correo: EmailStr
    direccion: str
    telefono: str
    activo: bool = True


class ClienteLogin(BaseModel):
    nombre: str
    telefono: str


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    correo: Optional[EmailStr] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None


class Producto(BaseModel):
    id_producto: int
    descripcion: str
    precio: float = Field(gt=0)
    activo: bool = True


class ProductoRegistro(BaseModel):
    descripcion: str
    precio: Optional[float] = None
    costo: Optional[float] = None
    costo_unitario: Optional[float] = None
    activo: bool = True

    @root_validator(pre=True)
    def _normalizar_precio(cls, values: dict[str, Any]) -> dict[str, Any]:
        precio = values.get("precio")
        if precio in (None, ""):
            precio = values.get("costo")
        if precio in (None, ""):
            precio = values.get("costo_unitario")
        values["precio"] = precio
        return values


class ProductoUpdate(BaseModel):
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    costo: Optional[float] = None
    costo_unitario: Optional[float] = None
    activo: Optional[bool] = None

    @root_validator(pre=True)
    def _normalizar_precio(cls, values: dict[str, Any]) -> dict[str, Any]:
        precio = values.get("precio")
        if precio in (None, ""):
            precio = values.get("costo")
        if precio in (None, ""):
            precio = values.get("costo_unitario")
        if precio not in (None, ""):
            values["precio"] = precio
        return values


class Inventario(BaseModel):
    id_producto: int
    cantidad: int = Field(ge=0)


class InventarioRegistro(BaseModel):
    cantidad: int = Field(gt=0)


class InventarioAlta(BaseModel):
    id_producto: int
    cantidad_inicial: int = Field(ge=0)


class InventarioUpdate(BaseModel):
    cantidad: Optional[int] = Field(default=None, ge=0)


class Pedido(BaseModel):
    id_pedido: int
    id_producto: int
    id_cliente: int
    cantidad: int = Field(gt=0)
    costo: float = Field(ge=0)
    estado: str = "COMPLETADO"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PedidoRegistro(BaseModel):
    id_pedido: Optional[int] = None
    id_producto: int
    id_cliente: int
    cantidad: int = Field(gt=0)
    costo: Optional[float] = None
    estado: Optional[str] = None


class PedidoUpdate(BaseModel):
    cantidad: Optional[int] = Field(default=None, gt=0)
    estado: Optional[str] = None


def cargar_clientes() -> list[Cliente]:
    clientes: list[Cliente] = []
    for row in _read_rows(CLIENTES_FILE):
        try:
            clientes.append(
                Cliente(
                    id_cliente=_as_int(row.get("id_cliente")),
                    nombre=(row.get("nombre") or "").strip(),
                    correo=(row.get("correo") or "").strip().lower(),
                    direccion=(row.get("direccion") or "").strip(),
                    telefono=(row.get("telefono") or "").strip(),
                    activo=_as_bool(row.get("activo"), default=True),
                )
            )
        except Exception:
            continue
    return clientes


def cargar_productos() -> list[Producto]:
    productos: list[Producto] = []
    for row in _read_rows(PRODUCTOS_FILE):
        try:
            precio = row.get("precio")
            if precio in (None, ""):
                precio = row.get("costo")
            if precio in (None, ""):
                precio = row.get("costo_unitario")

            productos.append(
                Producto(
                    id_producto=_as_int(row.get("id_producto")),
                    descripcion=(row.get("descripcion") or "").strip(),
                    precio=_as_float(precio),
                    activo=_as_bool(row.get("activo"), default=True),
                )
            )
        except Exception:
            continue
    return productos


def cargar_inventario() -> list[Inventario]:
    inventario: list[Inventario] = []
    for row in _read_rows(INVENTARIO_FILE):
        try:
            inventario.append(
                Inventario(
                    id_producto=_as_int(row.get("id_producto")),
                    cantidad=_as_int(row.get("cantidad")),
                )
            )
        except Exception:
            continue
    return inventario


def cargar_pedidos() -> list[Pedido]:
    pedidos: list[Pedido] = []
    for row in _read_rows(PEDIDOS_FILE):
        try:
            pedidos.append(
                Pedido(
                    id_pedido=_as_int(row.get("id_pedido")),
                    id_producto=_as_int(row.get("id_producto")),
                    id_cliente=_as_int(row.get("id_cliente")),
                    cantidad=_as_int(row.get("cantidad")),
                    costo=_as_float(row.get("costo")),
                    estado=(row.get("estado") or "COMPLETADO").strip().upper(),
                    created_at=(row.get("created_at") or datetime.now(timezone.utc).isoformat()).strip(),
                )
            )
        except Exception:
            continue
    return pedidos


bd_clientes = cargar_clientes()
bd_productos = cargar_productos()
bd_inventario = cargar_inventario()
bd_pedidos = cargar_pedidos()


def guardar_clientes(clientes: list[Cliente]) -> None:
    rows = []
    for cliente in clientes:
        row = _model_dump(cliente)
        row["correo"] = str(row["correo"]).lower()
        row["telefono"] = str(row["telefono"]).strip()
        rows.append(row)
    _write_rows(CLIENTES_FILE, CLIENTES_HEADERS, rows)


def guardar_productos(productos: list[Producto]) -> None:
    rows = []
    for producto in productos:
        row = _model_dump(producto)
        row["precio"] = f"{float(row['precio']):.2f}"
        rows.append(row)
    _write_rows(PRODUCTOS_FILE, PRODUCTOS_HEADERS, rows)


def guardar_inventarios(inventarios: list[Inventario]) -> None:
    rows = [_model_dump(item) for item in inventarios]
    _write_rows(INVENTARIO_FILE, INVENTARIO_HEADERS, rows)


def guardar_pedidos(pedidos: list[Pedido]) -> None:
    rows = []
    for pedido in pedidos:
        row = _model_dump(pedido)
        row["costo"] = f"{float(row['costo']):.2f}"
        row["estado"] = str(row["estado"]).upper()
        rows.append(row)
    _write_rows(PEDIDOS_FILE, PEDIDOS_HEADERS, rows)


def sincronizar_archivos() -> None:
    with data_lock:
        guardar_clientes(bd_clientes)
        guardar_productos(bd_productos)
        guardar_inventarios(bd_inventario)
        guardar_pedidos(bd_pedidos)


def siguiente_id(items: list[Any], attr_name: str) -> int:
    if not items:
        return 1
    return max(int(getattr(item, attr_name)) for item in items) + 1

