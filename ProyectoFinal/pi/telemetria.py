#!/usr/bin/env python3
"""Proceso de telemetría del arcade (Clase 11: IPC).

Lee la RAM del juego que corre en RetroArch y, cuando detecta un evento,
manda una orden de actuador al proceso puente_serial.py por un socket UNIX
de datagramas (AF_UNIX, SOCK_DGRAM).

    RetroArch --UDP 55355--> telemetria.py --AF_UNIX DGRAM--> puente_serial.py --> Pico

Datos del juego (Pac-Man, core Nestopia):
  - Dirección 0x067 = vidas. Empieza en 3 y baja 1 con cada muerte.
  - Se lee con READ_CORE_RAM; READ_CORE_MEMORY no funciona con este core.
  - NUNCA mandar GET_STATUS: tumba RetroArch 1.20.0 (segmentation fault).

La prioridad baja de este proceso (Clase 8) la pone systemd con Nice=10.
"""
import os
import socket
import sys
import time

# --- Configuración (se puede cambiar con variables de entorno para pruebas) ---
RETROARCH = (os.environ.get("RA_HOST", "127.0.0.1"), int(os.environ.get("RA_PORT", "55355")))
SOCK_PUENTE = os.environ.get("ARCADE_SOCK", "/tmp/arcade_act.sock")
DIR_VIDAS = 0x067             # vidas de Pac-Man en la RAM del NES
PERIODO = 1 / 60              # 16.6 ms, un cuadro del juego
TIEMPO_ESPERA = 0.2           # s que se espera la respuesta de RetroArch

# Órdenes que se mandan en cada evento (protocolo de la guía, sección 5.C)
AL_PERDER_VIDA = ["VIB 300", "BUZ 220 300", "LED 1 1"]
AL_EMPEZAR_PARTIDA = ["LED 1 0"]


def log(msg):
    # systemd guarda la salida estándar en journalctl
    print(f"[telemetria {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# Socket UDP para preguntarle a RetroArch
ra = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ra.settimeout(TIEMPO_ESPERA)

# Socket UNIX de datagramas hacia el puente (Clase 11)
puente = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)


def leer_ram(direccion):
    """Regresa el byte en 'direccion' o None si RetroArch no contesta."""
    ra.sendto(f"READ_CORE_RAM {direccion:X} 1".encode(), RETROARCH)
    try:
        resp = ra.recv(64).decode().split()
    except (socket.timeout, ConnectionRefusedError):
        return None
    # Respuesta esperada: "READ_CORE_RAM 67 03"; si falla: "READ_CORE_RAM 67 -1"
    if len(resp) < 3 or resp[0] != "READ_CORE_RAM" or resp[2] == "-1":
        return None
    return int(resp[2], 16)


def enviar(ordenes):
    """Manda cada orden como un datagrama independiente al puente."""
    for orden in ordenes:
        try:
            puente.sendto(orden.encode(), SOCK_PUENTE)
            log(f"enviado al puente: {orden}")
        except (FileNotFoundError, ConnectionRefusedError):
            log(f"el puente no está activo; se descarta: {orden}")


def main():
    log(f"leyendo vidas en 0x{DIR_VIDAS:03X} de RetroArch {RETROARCH[0]}:{RETROARCH[1]}")
    vidas_antes = None
    conectado = False
    siguiente = time.monotonic()

    while True:
        vidas = leer_ram(DIR_VIDAS)

        if vidas is None:
            if conectado:
                log("RetroArch no contesta; reintentando")
                conectado = False
            vidas_antes = None          # al volver, no comparar con datos viejos
            time.sleep(1)
            siguiente = time.monotonic()
            continue

        if not conectado:
            log(f"conectado a RetroArch, vidas = {vidas}")
            conectado = True

        if vidas_antes is not None and vidas != vidas_antes:
            if vidas < vidas_antes:
                log(f"vida perdida ({vidas_antes} -> {vidas})")
                enviar(AL_PERDER_VIDA)
            else:
                log(f"partida nueva ({vidas_antes} -> {vidas})")
                enviar(AL_EMPEZAR_PARTIDA)
        vidas_antes = vidas

        # Periodo fijo de 16.6 ms sin acumular retraso
        siguiente += PERIODO
        espera = siguiente - time.monotonic()
        if espera > 0:
            time.sleep(espera)
        else:
            siguiente = time.monotonic()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
