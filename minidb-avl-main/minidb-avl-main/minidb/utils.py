"""Mensajes paso a paso. Cada módulo llama a paso() para explicar qué hace."""

VERBOSE = True


def set_verbose(valor):
    global VERBOSE
    VERBOSE = valor


def paso(etiqueta, mensaje):
    if VERBOSE:
        print(f"   [{etiqueta}] {mensaje}")
