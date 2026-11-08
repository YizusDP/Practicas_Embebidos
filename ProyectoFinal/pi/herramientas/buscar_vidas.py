#!/usr/bin/env python3
"""Busca en la RAM del NES la dirección del contador de vidas.

Uso: con RetroArch corriendo el juego (network_cmd_enable = "true"),
ejecutar este script y seguir las instrucciones. Toma tres fotos de la
RAM (2 KB, 0x000-0x7FF) con READ_CORE_RAM: con todas las vidas, tras
perder una y tras perder otra. Imprime los bytes que bajaron de 1 en 1.

Resultado con Pac-Man (core Nestopia): 0x067 = vidas de reserva (2 -> 1 -> 0).
Nota: no usar GET_STATUS; tumba RetroArch 1.20.0 con este core.
"""
import socket

PUERTO = ("127.0.0.1", 55355)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(1)


def ram():
    datos = []
    for base in range(0, 0x800, 0x100):
        s.sendto(f"READ_CORE_RAM {base:X} 256".encode(), PUERTO)
        datos += [int(x, 16) for x in s.recv(8192).decode().split()[2:]]
    return datos


fotos = []
for msg in ["Empieza la partida y ya jugando con TODAS las vidas, presiona Enter aquí",
            "Deja que te maten UNA vez; cuando reaparezcas, presiona Enter aquí",
            "Deja que te maten OTRA vez; cuando reaparezcas, presiona Enter aquí"]:
    input("\n>> " + msg + "... ")
    fotos.append(ram())
    print(f"   foto {len(fotos)} tomada ({len(fotos[-1])} bytes)")

a, b, c = fotos
cand = [i for i in range(0x800) if a[i] - b[i] == 1 and b[i] - c[i] == 1]
print("\nCandidatos (bajaron 1 en cada muerte):")
for i in cand:
    print(f"  0x{i:03X}: {a[i]} -> {b[i]} -> {c[i]}")
if not cand:
    print("  ninguno; candidatos que solo bajaron:")
    for i in range(0x800):
        if a[i] > b[i] > c[i]:
            print(f"  0x{i:03X}: {a[i]} -> {b[i]} -> {c[i]}")
