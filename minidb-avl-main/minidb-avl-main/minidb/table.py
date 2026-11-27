"""Una tabla = esquema + registros. Índice AVL sobre la clave primaria.
Persistencia: un archivo JSON por tabla, escrito de forma atómica."""
import json
import os
from avl import AVL
from utils import paso

TIPOS = {"INT", "TEXT", "REAL", "BOOL"}
OPS = {
    "=": lambda a, b: a == b, "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b, ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b,
}


class Tabla:
    def __init__(self, ruta, nombre, columnas, pk):
        self.ruta, self.nombre, self.columnas, self.pk = ruta, nombre, columnas, pk
        self.tipos = dict(columnas)
        self.indice = AVL(lambda m: paso("AVL", m))

    # ---------- persistencia ----------
    def guardar(self):
        datos = {"nombre": self.nombre, "columnas": self.columnas, "pk": self.pk,
                 "registros": [fila for _, fila in self.indice.inorder()]}
        tmp = self.ruta + ".tmp"
        paso("DISCO", f"Escribo archivo temporal {tmp}")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.ruta)          # reemplazo atómico
        paso("DISCO", f"Reemplazo atómico por {self.ruta} (o queda el viejo, o el nuevo)")

    def _reconstruir(self, registros):
        log, self.indice = self.indice.log, AVL()      # silencio el AVL al reconstruir
        for fila in registros:
            self.indice.insertar(fila[self.pk], fila)
        self.indice.log = log

    @classmethod
    def cargar(cls, ruta):
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        t = cls(ruta, d["nombre"], [tuple(c) for c in d["columnas"]], d["pk"])
        t._reconstruir(d["registros"])
        paso("DISCO", f"Tabla '{t.nombre}': {t.indice.tamano} registros leídos, "
                      f"índice AVL reconstruido (altura {t.indice.altura()})")
        return t

    def _commit(self):
        """Guarda; si falla, vuelve al último estado bueno del disco (atomicidad)."""
        try:
            self.guardar()
        except Exception:
            paso("DISCO", "¡Falló el guardado! Revierto al estado anterior del disco")
            with open(self.ruta, encoding="utf-8") as f:
                self._reconstruir(json.load(f)["registros"])
            raise

    # ---------- validación ----------
    def _convertir(self, campo, valor):
        if campo not in self.tipos:
            raise ValueError(f"La columna '{campo}' no existe")
        t = self.tipos[campo]
        ok = ((t == "INT" and isinstance(valor, int) and not isinstance(valor, bool))
              or (t == "REAL" and isinstance(valor, (int, float)) and not isinstance(valor, bool))
              or (t == "TEXT" and isinstance(valor, str))
              or (t == "BOOL" and isinstance(valor, bool)))
        if not ok:
            raise ValueError(f"'{campo}' espera {t}, recibió {valor!r}")
        return float(valor) if t == "REAL" else valor

    def _condiciones(self, where):
        return [(c, o, self._convertir(c, v)) for c, o, v in (where or [])]

    # ---------- búsqueda de candidatos (aquí se usa el índice) ----------
    def _candidatos(self, conds):
        pk_conds = [c for c in conds if c[0] == self.pk]
        igual = [c for c in pk_conds if c[1] == "="]
        rango = [c for c in pk_conds if c[1] in ("<", ">", "<=", ">=")]
        if igual:
            paso("TABLA", f"Condición {self.pk} = {igual[0][2]} sobre la clave primaria: uso el AVL, O(log n)")
            fila = self.indice.buscar(igual[0][2])
            filas = [fila] if fila else []
        elif rango:
            lo = max([v for _, o, v in rango if o in (">", ">=")], default=None)
            hi = min([v for _, o, v in rango if o in ("<", "<=")], default=None)
            paso("TABLA", "Rango sobre la clave primaria: uso el AVL, O(log n + k)")
            filas = [f for _, f in self.indice.rango(lo, hi)]
        else:
            paso("TABLA", "Sin condición sobre la clave primaria: recorro todo el AVL (inorder), O(n)")
            filas = [f for _, f in self.indice.inorder()]
        paso("TABLA", f"Candidatos obtenidos: {len(filas)}; filtro con todas las condiciones")
        return [f for f in filas if all(OPS[o](f[c], v) for c, o, v in conds)]

    # ---------- operaciones CRUD ----------
    def insertar(self, valores):
        if len(valores) != len(self.columnas):
            raise ValueError(f"Se esperaban {len(self.columnas)} valores, llegaron {len(valores)}")
        fila = {c: self._convertir(c, v) for (c, _), v in zip(self.columnas, valores)}
        paso("TABLA", "Tipos validados correctamente")
        self.indice.insertar(fila[self.pk], fila)   # lanza KeyError si la PK se repite
        self._commit()
        return fila

    def seleccionar(self, where=None):
        return self._candidatos(self._condiciones(where))

    def actualizar(self, cambios, where=None):
        conds = self._condiciones(where)
        if self.pk in cambios:
            raise ValueError("No se permite modificar la clave primaria")
        nuevos = {c: self._convertir(c, v) for c, v in cambios.items()}  # valida ANTES de tocar nada
        filas = self._candidatos(conds)
        for f in filas:
            f.update(nuevos)
        if filas:
            self._commit()
        return len(filas)

    def eliminar(self, where=None):
        filas = self._candidatos(self._condiciones(where))
        for f in filas:
            self.indice.eliminar(f[self.pk])
        if filas:
            self._commit()
        return len(filas)
