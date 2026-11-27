"""Genera scripts/medium.sql con 500 registros en orden aleatorio."""
import random
random.seed(1)
ids = list(range(1, 501))
random.shuffle(ids)
with open("scripts/medium.sql", "w", encoding="utf-8") as f:
    f.write("-- Dataset mediano: 500 productos\n")
    f.write("CREATE TABLE productos (id INT PRIMARY KEY, nombre TEXT, precio REAL, stock INT, activo BOOL)\n")
    for i in ids:
        f.write(f"INSERT INTO productos VALUES ({i}, 'producto{i}', {round(random.uniform(1, 500), 2)}, "
                f"{random.randint(0, 100)}, {random.choice(['true', 'false'])})\n")
