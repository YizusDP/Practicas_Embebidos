#!/usr/bin/env python3
"""Puente entre la telemetría y la Pico (Clase 11: IPC).

Recibe órdenes de texto por un socket UNIX de datagramas (AF_UNIX,
SOCK_DGRAM), las traduce a un reporte de salida HID de 8 bytes y lo escribe
en el hidraw del control (el mismo USB HID por el que llegan los botones).

    telemetria.py --AF_UNIX DGRAM--> puente_hid.py --hidraw (SET_REPORT)--> Pico

Reporte de salida (8 bytes, enteros en little-endian), igual que en
firmware/usb_data_tx.c:
    byte 0 = comando
      1 VIB : bytes 1-2 = ms
      2 BUZ : bytes 1-2 = Hz, bytes 3-4 = ms
      3 LED : byte 1 = id (1 o 2), byte 2 = estado (0 o 1)

Sincronización (Clase 9): este es el ÚNICO proceso que escribe en el hidraw,
así que dos órdenes nunca se mezclan y no hace falta un candado.

Robustez: si se desconecta el control, el puente sigue vivo y reintenta abrir
el dispositivo cada segundo (falla inducida F2 del reporte).
"""
import os
import re
import select
import socket
import struct
import sys
import time

SOCK_PUENTE = os.environ.get("ARCADE_SOCK", "/tmp/arcade_act.sock")
HIDRAW = os.environ.get("ARCADE_HID", "/dev/arcade_hid")   # enlace que crea la regla de udev
REINTENTO = 1.0      # s entre intentos de abrir el dispositivo
TAM_REPORTE = 8

# Órdenes de texto aceptadas (las manda telemetria.py)
VIB = re.compile(r"^VIB (\d{1,5})$")
BUZ = re.compile(r"^BUZ (\d{1,5}) (\d{1,5})$")
LED = re.compile(r"^LED ([12]) ([01])$")


def log(msg):
    print(f"[puente {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def a_reporte(orden):
    """Traduce 'VIB 300' -> 8 bytes del reporte HID; None si es inválida."""
    if m := VIB.match(orden):
        datos = struct.pack("<BH", 1, int(m[1]))
    elif m := BUZ.match(orden):
        datos = struct.pack("<BHH", 2, int(m[1]), int(m[2]))
    elif m := LED.match(orden):
        datos = struct.pack("<BBB", 3, int(m[1]), int(m[2]))
    else:
        return None
    return datos.ljust(TAM_REPORTE, b"\x00")


def abrir_hid():
    try:
        fd = os.open(HIDRAW, os.O_WRONLY)
    except OSError:
        return None
    log(f"control abierto: {HIDRAW} -> {os.path.realpath(HIDRAW)}")
    return fd


def crear_socket():
    try:
        os.unlink(SOCK_PUENTE)          # quita uno viejo si el proceso se reinició
    except FileNotFoundError:
        pass
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    s.bind(SOCK_PUENTE)
    os.chmod(SOCK_PUENTE, 0o666)
    log(f"escuchando en {SOCK_PUENTE}")
    return s


def main():
    sock = crear_socket()
    fd = None
    ultimo_intento = 0.0

    while True:
        if fd is None and time.monotonic() - ultimo_intento >= REINTENTO:
            ultimo_intento = time.monotonic()
            fd = abrir_hid()

        listos, _, _ = select.select([sock], [], [], REINTENTO)
        if not listos:
            continue

        orden = sock.recv(64).decode(errors="replace").strip()
        reporte = a_reporte(orden)
        if reporte is None:
            log(f"orden inválida, se ignora: {orden!r}")
            continue
        if fd is None:
            log(f"control desconectado, se descarta: {orden}")
            continue
        try:
            t0 = time.monotonic()
            # El control no usa Report ID: hidraw pide un 0 al inicio y el kernel lo quita
            os.write(fd, b"\x00" + reporte)
            ms = (time.monotonic() - t0) * 1000
            log(f"-> Pico: {orden} [{reporte.hex(' ')}] entregado en {ms:.1f} ms")
        except OSError as e:
            log(f"se perdió el control ({e.strerror}); reintentando")
            os.close(fd)
            fd = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
