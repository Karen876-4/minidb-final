"""REPL: lee comandos, los parsea y los ejecuta explicando cada paso."""
import sys
import utils
from utils import paso
from parser import parsear
from database import BaseDeDatos

AYUDA = """Comandos:
  CREATE TABLE personas (id INT PRIMARY KEY, nombre TEXT, edad INT, nota REAL, activo BOOL)
  DROP TABLE personas
  INSERT INTO personas VALUES (1, 'Ana', 20, 4.5, true)
  SELECT * FROM personas [WHERE campo op valor [AND ...]]      op: = != < > <= >=
  UPDATE personas SET edad = 21, nota = 5.0 WHERE id = 1
  DELETE FROM personas WHERE id = 1
  SHOW TABLES | SHOW TREE personas | VERBOSE ON|OFF | RUN archivo.sql | HELP | EXIT"""


def imprimir_tabla(columnas, filas):
    nombres = [c for c, _ in columnas]
    ancho = {n: max([len(n)] + [len(str(f[n])) for f in filas]) for n in nombres}
    print(" | ".join(n.ljust(ancho[n]) for n in nombres))
    print("-+-".join("-" * ancho[n] for n in nombres))
    for f in filas:
        print(" | ".join(str(f[n]).ljust(ancho[n]) for n in nombres))
    print(f"({len(filas)} fila(s))")


def ejecutar(db, linea):
    paso("PARSER", f"Leí: {linea.strip()}")
    cmd = parsear(linea)
    if cmd is None:
        return True
    paso("PARSER", f"Comando identificado: {cmd['cmd'].upper()}")
    c = cmd["cmd"]
    if c in ("exit", "quit"):
        return False
    if c == "help":
        print(AYUDA)
    elif c == "verbose":
        utils.set_verbose(cmd["on"])
        print("Modo paso a paso:", "ACTIVADO" if cmd["on"] else "DESACTIVADO")
    elif c == "create":
        db.crear_tabla(cmd["nombre"], cmd["columnas"], cmd["pk"])
        print(f"OK: tabla '{cmd['nombre']}' creada (índice AVL sobre '{cmd['pk']}')")
    elif c == "drop":
        db.borrar_tabla(cmd["nombre"])
        print(f"OK: tabla '{cmd['nombre']}' eliminada")
    elif c == "insert":
        db.obtener(cmd["nombre"]).insertar(cmd["valores"])
        print("OK: 1 registro insertado")
    elif c == "select":
        t = db.obtener(cmd["nombre"])
        imprimir_tabla(t.columnas, t.seleccionar(cmd["where"]))
    elif c == "update":
        n = db.obtener(cmd["nombre"]).actualizar(cmd["cambios"], cmd["where"])
        print(f"OK: {n} registro(s) actualizado(s)")
    elif c == "delete":
        n = db.obtener(cmd["nombre"]).eliminar(cmd["where"])
        print(f"OK: {n} registro(s) eliminado(s)")
    elif c == "show_tables":
        for t in db.tablas.values():
            print(f"- {t.nombre}: {t.indice.tamano} registros, PK={t.pk}, "
                  f"columnas={[f'{n} {ty}' for n, ty in t.columnas]}")
        if not db.tablas:
            print("(no hay tablas)")
    elif c == "show_tree":
        t = db.obtener(cmd["nombre"])
        print(t.indice.dibujar(t.nombre))
    elif c == "run":
        correr_script(db, cmd["ruta"])
    return True


def correr_script(db, ruta):
    with open(ruta, encoding="utf-8") as f:
        lineas = [l for l in f if l.strip() and not l.strip().startswith("--")]
    previo = utils.VERBOSE
    if len(lineas) > 20:
        utils.set_verbose(False)
        print(f"Script grande ({len(lineas)} comandos): modo paso a paso apagado durante la carga")
    for l in lineas:
        try:
            ejecutar(db, l)
        except Exception as e:
            print(f"ERROR en '{l.strip()}': {e}")
    utils.set_verbose(previo)
    print(f"Script terminado: {len(lineas)} comandos ejecutados")


def main():
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "data"
    print("=== MiniDB con árbol AVL === (escriba HELP para ver comandos)")
    db = BaseDeDatos(carpeta)
    while True:
        try:
            linea = input("\ndb> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            if not ejecutar(db, linea):
                break
        except (ValueError, KeyError) as e:
            print(f"ERROR: {e.args[0] if e.args else e}")
    print("Hasta luego")


if __name__ == "__main__":
    main()