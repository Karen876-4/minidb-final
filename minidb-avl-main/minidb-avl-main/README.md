# MiniDB con árbol AVL

Gestor de bases de datos relacional minimalista en Python (solo librería estándar).
Cada tabla tiene un **índice AVL propio** sobre su clave primaria. La consola explica paso a paso qué hace
(`[PARSER]`, `[TABLA]`, `[AVL]`, `[DISCO]`).

## Ejecutar
```bash
python3 main.py              # guarda las tablas en la carpeta data/
python3 -m unittest discover -s tests -v     # pruebas
python3 scripts/gen_medium.py                # regenera el dataset mediano (500 registros)
```
Dentro del REPL: `RUN scripts/small.sql` (10 registros) o `RUN scripts/medium.sql` (500 registros).
`VERBOSE OFF` / `VERBOSE ON` apaga o enciende el modo paso a paso.

## Comandos
```
CREATE TABLE personas (id INT PRIMARY KEY, nombre TEXT, edad INT, nota REAL, activo BOOL)
INSERT INTO personas VALUES (1, 'Ana', 20, 4.5, true)
SELECT * FROM personas
SELECT * FROM personas WHERE id = 1
SELECT * FROM personas WHERE id >= 10 AND id <= 50      -- rango con el AVL
SELECT * FROM personas WHERE edad > 20                   -- campo sin índice: recorrido completo
UPDATE personas SET edad = 21 WHERE id = 1
DELETE FROM personas WHERE id = 1
SHOW TABLES | SHOW TREE personas | DROP TABLE personas | HELP | EXIT
```
Tipos: `INT`, `TEXT`, `REAL`, `BOOL`.

## Módulos
| Archivo | Responsabilidad |
|---|---|
| `avl.py` | Árbol AVL propio: insertar, buscar, eliminar, inorder, rango |
| `table.py` | Esquema, validación de tipos, CRUD, persistencia JSON |
| `database.py` | Administra tablas y las recupera al iniciar |
| `parser.py` | Texto SQL-like → diccionario de comando |
| `main.py` | REPL (CLI) |
| `utils.py` | Mensajes paso a paso |

## Persistencia y recuperación
- Un archivo `data/<tabla>.json` con esquema y registros (ordenados por clave).
- El índice **se reconstruye** insertando los registros en un AVL al iniciar (O(n log n)).
- **Atomicidad:** se escribe `tabla.json.tmp` + `fsync` + `os.replace`, así el archivo nunca queda a medias.
  Si el guardado falla, la tabla se recarga desde el último estado bueno del disco.
  Las validaciones (tipos, PK duplicada) se hacen antes de modificar datos.
- Sin concurrencia (un solo usuario).

## Complejidad (n = registros, k = resultados)
| Operación | Tiempo | Espacio |
|---|---|---|
| Insertar / buscar / eliminar en AVL | O(log n) | O(1) extra (recursión O(log n)) |
| Rango en AVL | O(log n + k) | O(log n) |
| Recorrido inorder | O(n) | O(log n) |
| SELECT/UPDATE/DELETE por PK | O(log n) | — |
| Consulta por campo sin índice | O(n) | O(n) |
| Guardar a disco (cada escritura) | O(n) | O(n) |
| Cargar al iniciar | O(n log n) | O(n) |
| Almacenamiento total | — | O(n) |

## Invariante del AVL
Para todo nodo: `|altura(izq) − altura(der)| ≤ 1`. Tras cada inserción/eliminación, al volver de la recursión
se recalcula la altura y, si el factor de balance es ±2, se aplica rotación simple (izq/der) o doble (izq-der / der-izq).
Altura máxima ≈ 1.44·log₂(n).
