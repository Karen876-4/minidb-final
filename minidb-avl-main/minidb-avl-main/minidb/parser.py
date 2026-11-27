"""Convierte texto SQL-like en un diccionario {'cmd': ..., ...}."""
import re


def tokenizar(texto):
    return re.findall(r"'[^']*'|!=|<=|>=|[(),=<>*;]|[^\s(),=<>*;!']+", texto)


def valor(tok):
    if tok.startswith("'") and tok.endswith("'"):
        return tok[1:-1]
    if tok.lower() in ("true", "false"):
        return tok.lower() == "true"
    for conv in (int, float):
        try:
            return conv(tok)
        except ValueError:
            pass
    raise ValueError(f"Valor inválido: {tok}")


def separar_comas(tokens):
    grupos, actual = [], []
    for t in tokens:
        if t == ",":
            grupos.append(actual)
            actual = []
        else:
            actual.append(t)
    if actual:
        grupos.append(actual)
    return grupos


def parsear_where(tokens):
    """campo op valor [AND campo op valor ...] -> [(campo, op, valor)]"""
    conds, actual = [], []
    for t in tokens + ["AND"]:
        if t.upper() == "AND":
            if len(actual) != 3:
                raise ValueError("Condición inválida. Use: campo operador valor")
            conds.append((actual[0], actual[1], valor(actual[2])))
            actual = []
        else:
            actual.append(t)
    return conds


def _where(tokens, desde):
    return parsear_where(tokens[desde + 1:]) if len(tokens) > desde and tokens[desde].upper() == "WHERE" else None


def parsear(linea):
    t = [x for x in tokenizar(linea) if x != ";"]
    if not t:
        return None
    c = t[0].upper()
    try:
        if c == "CREATE" and t[1].upper() == "TABLE":
            columnas, pk = [], None
            for g in separar_comas(t[4:-1]):
                columnas.append((g[0], g[1].upper()))
                if [x.upper() for x in g[2:]] == ["PRIMARY", "KEY"]:
                    pk = g[0]
            if pk is None:
                raise ValueError("Falta la clave primaria (ej: id INT PRIMARY KEY)")
            return {"cmd": "create", "nombre": t[2], "columnas": columnas, "pk": pk}
        if c == "DROP" and t[1].upper() == "TABLE":
            return {"cmd": "drop", "nombre": t[2]}
        if c == "INSERT" and t[1].upper() == "INTO" and t[3].upper() == "VALUES":
            return {"cmd": "insert", "nombre": t[2],
                    "valores": [valor(g[0]) for g in separar_comas(t[5:-1])]}
        if c == "SELECT" and t[1] == "*" and t[2].upper() == "FROM":
            return {"cmd": "select", "nombre": t[3], "where": _where(t, 4)}
        if c == "UPDATE" and t[2].upper() == "SET":
            w = next((i for i, x in enumerate(t) if x.upper() == "WHERE"), len(t))
            cambios = {g[0]: valor(g[2]) for g in separar_comas(t[3:w])}
            return {"cmd": "update", "nombre": t[1], "cambios": cambios, "where": _where(t, w)}
        if c == "DELETE" and t[1].upper() == "FROM":
            return {"cmd": "delete", "nombre": t[2], "where": _where(t, 3)}
        if c == "SHOW" and t[1].upper() == "TABLES":
            return {"cmd": "show_tables"}
        if c == "SHOW" and t[1].upper() == "TREE":
            return {"cmd": "show_tree", "nombre": t[2]}
        if c == "VERBOSE":
            return {"cmd": "verbose", "on": t[1].upper() == "ON"}
        if c == "RUN":
            return {"cmd": "run", "ruta": t[1]}
        if c in ("HELP", "EXIT", "QUIT"):
            return {"cmd": c.lower()}
    except IndexError:
        pass
    raise ValueError("Comando no reconocido o incompleto. Escriba HELP")
