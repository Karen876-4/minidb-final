import math, os, random, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import utils
from avl import AVL
from database import BaseDeDatos

utils.set_verbose(False)
COLS = [("id", "INT"), ("nombre", "TEXT"), ("edad", "INT")]


def balanceado(n):
    if n is None:
        return True
    return abs((n.izq.altura if n.izq else 0) - (n.der.altura if n.der else 0)) <= 1 \
        and balanceado(n.izq) and balanceado(n.der)


class TestAVL(unittest.TestCase):
    def test_insertar_ordenado_queda_balanceado(self):
        t = AVL()
        for i in range(1, 1025):            # peor caso para un BST normal
            t.insertar(i, i)
        self.assertTrue(balanceado(t.raiz))
        self.assertLessEqual(t.altura(), 1.45 * math.log2(1025))

    def test_inorder_ordenado_y_busqueda(self):
        t, claves = AVL(), random.sample(range(1000), 200)
        for k in claves:
            t.insertar(k, str(k))
        self.assertEqual([k for k, _ in t.inorder()], sorted(claves))
        self.assertEqual(t.buscar(claves[0]), str(claves[0]))
        self.assertIsNone(t.buscar(-1))

    def test_eliminar_mantiene_balance(self):
        t, claves = AVL(), list(range(300))
        for k in claves:
            t.insertar(k, k)
        random.shuffle(claves)
        for k in claves[:200]:
            t.eliminar(k)
            self.assertTrue(balanceado(t.raiz))
        self.assertEqual(t.tamano, 100)

    def test_rango_y_duplicados(self):
        t = AVL()
        for k in range(10):
            t.insertar(k, k)
        self.assertEqual([k for k, _ in t.rango(3, 6)], [3, 4, 5, 6])
        with self.assertRaises(KeyError):
            t.insertar(3, 3)


class TestDibujar(unittest.TestCase):
    def test_vacio(self):
        s = AVL().dibujar("socios")
        self.assertIn("RAIZ: (ninguna)", s)
        self.assertIn("(árbol vacío)", s)
        self.assertIn("ESTADO: AVL BALANCEADO", s)

    def test_un_nodo(self):
        t = AVL()
        t.insertar("mateo", 1)
        s = t.dibujar()
        self.assertIn("\nmateo\n", s)
        self.assertNotIn("+--", s)

    def test_ejemplo_del_enunciado(self):
        t = AVL()
        for k in ["mateo", "anuel", "teo", "alejandro"]:
            t.insertar(k, k)
        esperado = "\n".join([
            "mateo",
            "|",
            "+-- IZQUIERDA: anuel",
            "|   |",
            "|   +-- IZQUIERDA: alejandro",
            "|",
            "+-- DERECHA: teo",
        ])
        self.assertIn(esperado, t.dibujar("socios"))

    def test_desbalance_detectado(self):
        from avl import Nodo
        t = AVL()                      # árbol armado a mano, sin pasar por insertar()
        t.raiz = Nodo(3, 3); t.raiz.izq = Nodo(2, 2); t.raiz.izq.izq = Nodo(1, 1)
        t.raiz.izq.altura, t.raiz.altura, t.tamano = 2, 3, 3
        self.assertIn("NO BALANCEADO (|FE| > 1 en: 3)", t.dibujar())

    def test_no_modifica_el_arbol(self):
        t = AVL()
        for k in random.sample(range(500), 200):
            t.insertar(k, k)
        antes = (list(t.inorder()), t.altura(), t.tamano)
        s = t.dibujar()
        self.assertEqual(antes, (list(t.inorder()), t.altura(), t.tamano))
        self.assertEqual(s.count("+-- "), 199)   # todos los nodos menos la raíz


class TestDB(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = BaseDeDatos(self.dir)
        self.db.crear_tabla("p", COLS, "id")
        self.t = self.db.obtener("p")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_insert_select(self):
        self.t.insertar([2, "Luis", 30])
        self.t.insertar([1, "Ana", 20])
        self.assertEqual([f["id"] for f in self.t.seleccionar()], [1, 2])
        self.assertEqual(self.t.seleccionar([("id", "=", 2)])[0]["nombre"], "Luis")

    def test_rango_y_filtro_no_indexado(self):
        for i in range(1, 11):
            self.t.insertar([i, f"n{i}", i * 10])
        self.assertEqual(len(self.t.seleccionar([("id", ">=", 3), ("id", "<", 6)])), 3)
        self.assertEqual(len(self.t.seleccionar([("edad", ">", 50)])), 5)

    def test_update_delete(self):
        for i in range(1, 6):
            self.t.insertar([i, f"n{i}", 20])
        self.assertEqual(self.t.actualizar({"edad": 99}, [("id", ">", 3)]), 2)
        self.assertEqual(self.t.eliminar([("id", "=", 1)]), 1)
        self.assertEqual(len(self.t.seleccionar()), 4)

    def test_errores_no_corrompen(self):
        self.t.insertar([1, "Ana", 20])
        with self.assertRaises(KeyError):
            self.t.insertar([1, "Otra", 30])            # PK duplicada
        with self.assertRaises(ValueError):
            self.t.insertar([2, "Bob", "veinte"])       # tipo incorrecto
        with self.assertRaises(ValueError):
            self.t.actualizar({"edad": "x"}, None)      # validación antes de modificar
        self.assertEqual(self.t.seleccionar()[0]["edad"], 20)

    def test_recuperacion_tras_reinicio(self):
        for i in range(1, 51):
            self.t.insertar([i, f"n{i}", i])
        self.t.eliminar([("id", "=", 10)])
        self.t.actualizar({"nombre": "X"}, [("id", "=", 5)])
        db2 = BaseDeDatos(self.dir)                     # "reiniciar" el gestor
        t2 = db2.obtener("p")
        self.assertEqual(t2.indice.tamano, 49)
        self.assertEqual(t2.seleccionar([("id", "=", 5)])[0]["nombre"], "X")
        self.assertEqual(t2.seleccionar([("id", "=", 10)]), [])
        self.assertTrue(balanceado(t2.indice.raiz))


if __name__ == "__main__":
    unittest.main()