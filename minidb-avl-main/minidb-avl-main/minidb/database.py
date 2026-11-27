"""Gestor: administra las tablas y las recupera al iniciar."""
import os
from table import Tabla, TIPOS
from utils import paso


class BaseDeDatos:
    def __init__(self, carpeta="data"):
        self.carpeta = carpeta
        os.makedirs(carpeta, exist_ok=True)
        self.tablas = {}
        paso("DISCO", f"Buscando tablas guardadas en '{carpeta}/'")
        for archivo in sorted(os.listdir(carpeta)):
            if archivo.endswith(".json"):
                t = Tabla.cargar(os.path.join(carpeta, archivo))
                self.tablas[t.nombre] = t

    def crear_tabla(self, nombre, columnas, pk):
        if nombre in self.tablas:
            raise ValueError(f"La tabla '{nombre}' ya existe")
        for _, tipo in columnas:
            if tipo not in TIPOS:
                raise ValueError(f"Tipo no soportado: {tipo} (use {', '.join(sorted(TIPOS))})")
        t = Tabla(os.path.join(self.carpeta, nombre + ".json"), nombre, columnas, pk)
        t.guardar()
        self.tablas[nombre] = t

    def borrar_tabla(self, nombre):
        t = self.obtener(nombre)
        os.remove(t.ruta)
        paso("DISCO", f"Archivo {t.ruta} eliminado")
        del self.tablas[nombre]

    def obtener(self, nombre):
        if nombre not in self.tablas:
            raise ValueError(f"La tabla '{nombre}' no existe")
        return self.tablas[nombre]
