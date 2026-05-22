from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from config import get_data_file

"""
INICIO DE CLIENTES
"""
#Esta seccion define como debe verse un cliente
class Cliente(BaseModel):
    id_cliente: int 
    nombre: str
    correo: EmailStr
    direccion: str
    telefono: int

#Esta sirve para el post
class ClienteRegistro(BaseModel):
    nombre: str
    correo: EmailStr
    direccion: str
    telefono: str


class ClienteLogin(BaseModel):
    nombre: str
    telefono: str

#Esta seccion define como debe de verse el patch
class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    correo: Optional[EmailStr] = None
    direccion: Optional[str] = None
    telefono: Optional[int] = None

def up_clientes():
    lista = []
    try:
        with open(get_data_file("CLIENTES_CSV", "clientes.csv"), "r", encoding="utf-8") as f:
            for linea in f.readlines()[1:]:
                datos = linea.strip().split(",")
                if len(datos) == 5:
                    lista.append(Cliente(id_cliente=int(datos[0]), nombre=datos[1], correo=datos[2], direccion=datos[3], telefono=int(datos[4])))
    except FileNotFoundError:
        pass
    return lista

bd_clientes = up_clientes()

"""

FINAL DE CLIENTES

"""


"""
INICIO DE PODUCTOS
"""
class Producto(BaseModel):
    id_producto: int
    descripcion: str
    costo: int

class ProductoRegistro(BaseModel):
    descripcion: str
    costo: int

class ProductoUpdate(BaseModel):
    descripcion: Optional[str] = None
    costo: Optional[int] = None

def up_productos():
    lista = []
    try:
        with open(get_data_file("PRODUCTOS_CSV", "productos.csv"), "r", encoding="utf-8") as f:
            for linea in f.readlines()[1:]:
                datos = linea.strip().split(",")
                if len(datos) == 3:
                    lista.append(Producto(id_producto=int(datos[0]), descripcion=datos[1], costo=int(datos[2])))
    except FileNotFoundError:
        pass
    return lista

bd_productos = up_productos()

"""

FIN DE PODUCTOS

"""


"""

INICIO DE INVENTARIO

"""

class Inventario(BaseModel):
    id_producto: int
    cantidad: int = Field(ge=0, description="Debe ser mayor o igual a 0")

class InventarioRegistro(BaseModel):
    cantidad: int

class InventarioUpdate(BaseModel):
    cantidad: Optional[int] = None

def update_inventario():
    lista = []
    try:
        with open(get_data_file("INVENTARIO_CSV", "inventario.csv"), "r", encoding="utf-8") as f:
            for linea in f.readlines()[1:]:
                datos = linea.strip().split(",")
                if len(datos) == 2:
                    lista.append(Inventario(id_producto=int(datos[0]), cantidad=int(datos[1])))
    except FileNotFoundError:
        pass
    return lista

bd_inventario = update_inventario()

"""

FIN DE INVENTARIO

"""



"""

INICIO DE PEDIDO

"""
class Pedido(BaseModel):
    id_pedido: int
    id_producto: int
    id_cliente: int
    cantidad: int = Field(gt=0, description="No puede ser 0")
    costo: int
    
class PedidoRegistro(BaseModel):
    cantidad: int
    costo: int

class PedidoUpdate(BaseModel):
    cantidad: Optional[int] = None
    costo: Optional[int] = None

def update_pedidos():
    lista = []
    try:
        with open(get_data_file("PEDIDOS_CSV", "pedidos.csv"), "r", encoding="utf-8") as f:
            for linea in f.readlines()[1:]:
                datos = linea.strip().split(",")
                if len(datos) == 5:
                    lista.append(Pedido(
                        id_pedido=int(datos[0]),
                        id_producto=int(datos[1]),
                        id_cliente=int(datos[2]),
                        cantidad=int(datos[3]),
                        costo=int(datos[4])
                    ))
    except FileNotFoundError:
        pass
    return lista

bd_pedidos = update_pedidos()

"""

FIN DE PEDIDO

"""

