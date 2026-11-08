#!/usr/bin/env python3
"""Puente entre la telemetría y la Pico (Clase 11: IPC).

Recibe órdenes de actuador por un socket UNIX de datagramas (AF_UNIX,
SOCK_DGRAM) y las escribe por el USB serial de la Pico (/dev/ttyACM0).

    telemetria.py --AF_UNIX DGRAM--> puente_serial.py --/dev/ttyACM0--> Pico

Sincronización (Clase 9): este es el ÚNICO proceso que escribe en el serial,
así que dos órdenes nunca se mezclan a media línea y no hace falta un candado.

Robustez: si se desconecta el control, el puente sigue vivo y reintenta abrir
/dev/ttyACM0 cada segundo (falla inducida F2 del reporte).

Protocolo (guía, sección 5.C), una orden por línea; la Pico responde OK o ERR:
    VIB <ms>        BUZ <hz> <ms>        LED <n> <0|1>
"""
import os
import re
import select
import socket
import sys
import termios
import time

SOCK_PUENTE = os.environ.get("ARCADE_SOCK", "/tmp/arcade_act.sock")
SERIAL = os.environ.get("ARCADE_SERIAL", "/dev/ttyACM0")
REINTENTO = 1.0     # s entre intentos de abrir el serial

# Solo se aceptan órdenes con el formato acordado
ORDEN_VALIDA = re.compile(r"^(VIB \d{1,5}|BUZ \d{1,5} \d{1,5}|LED [12] [01])$")


def log(msg):
    print(f"[puente {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def abrir_serial():
    """Abre el serial en modo crudo; regresa el descriptor o None."""
    try:
        fd = os.open(SERIAL, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        attr = termios.tcgetattr(fd)
        attr[0] = 0                                     # iflag: sin procesar la entrada
        attr[1] = 0                                     # oflag: sin procesar la salida
        attr[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attr[3] = 0                                     # lflag: sin eco ni modo canónico
        termios.tcsetattr(fd, termios.TCSANOW, attr)
    except termios.error:
        pass    # un pty de pruebas puede no aceptar todo; no es grave
    log(f"serial abierto: {SERIAL}")
    return fd


def crear_socket():
    """Crea el socket UNIX de datagramas donde escucha el puente."""
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
    pendientes = {}          # orden -> instante de envío, para medir la respuesta
    buffer = b""

    while True:
        # Reabrir el serial si se perdió
        if fd is None and time.monotonic() - ultimo_intento >= REINTENTO:
            ultimo_intento = time.monotonic()
            fd = abrir_serial()

        entradas = [sock] + ([fd] if fd is not None else [])
        listos, _, _ = select.select(entradas, [], [], REINTENTO)

        # 1) Orden nueva desde la telemetría
        if sock in listos:
            orden = sock.recv(64).decode(errors="replace").strip()
            if not ORDEN_VALIDA.match(orden):
                log(f"orden inválida, se ignora: {orden!r}")
            elif fd is None:
                log(f"control desconectado, se descarta: {orden}")
            else:
                try:
                    os.write(fd, (orden + "\n").encode())
                    pendientes[orden] = time.monotonic()
                    log(f"-> Pico: {orden}")
                except OSError as e:
                    log(f"se perdió el serial ({e.strerror}); reintentando")
                    os.close(fd)
                    fd = None

        # 2) Respuesta de la Pico (OK / ERR)
        if fd is not None and fd in listos:
            try:
                datos = os.read(fd, 256)
            except OSError:
                datos = b""
            if not datos:
                log("se perdió el serial (control desconectado); reintentando")
                os.close(fd)
                fd = None
                buffer = b""
                continue
            buffer += datos
            while b"\n" in buffer:
                linea, buffer = buffer.split(b"\n", 1)
                linea = linea.decode(errors="replace").strip()
                if not linea:
                    continue
                if pendientes:
                    orden, t0 = next(iter(pendientes.items()))
                    del pendientes[orden]
                    log(f"<- Pico: {linea} ({orden}, {(time.monotonic() - t0) * 1000:.1f} ms)")
                else:
                    log(f"<- Pico: {linea}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
