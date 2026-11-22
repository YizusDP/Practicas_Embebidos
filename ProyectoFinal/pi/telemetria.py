#!/usr/bin/env python3
"""Proceso de telemetría del arcade (Clase 11: IPC).

Lee la RAM del juego que corre en RetroArch y, cuando detecta un evento,
manda órdenes de actuador al proceso puente_hid.py por un socket UNIX
de datagramas (AF_UNIX, SOCK_DGRAM).

    RetroArch --UDP 55355--> telemetria.py --AF_UNIX DGRAM--> puente_hid.py --> Pico

El arcade tiene varios juegos (Pac-Man, Tetris y Pong). Para saber cuál está
abierto se lee la primera entrada del historial de RetroArch (content_history_path
en ra_gl.cfg). Solo se lee la RAM de los juegos que están en JUEGOS: en otro
juego la misma dirección significa otra cosa y daría avisos falsos.

Datos de Pac-Man (core Nestopia):
  - Dirección 0x067 = vidas. Empieza en 3 y baja 1 con cada muerte.
  - Se lee con READ_CORE_RAM; READ_CORE_MEMORY no funciona con este core.
  - NUNCA mandar GET_STATUS: tumba RetroArch 1.20.0 (segmentation fault).

Al perder una vida: vibra el motor, suena el buzzer y se prenden los dos LEDs.
El motor y el buzzer los apaga la Pico al terminar su tiempo; los LEDs los
apaga este proceso DURACION_MS después, sin detener el ciclo de lectura.

La prioridad baja de este proceso (Clase 8) la pone systemd con Nice=10.
"""
import json
import os
import socket
import sys
import time

# --- Configuración (se puede cambiar con variables de entorno para pruebas) ---
RETROARCH = (os.environ.get("RA_HOST", "127.0.0.1"), int(os.environ.get("RA_PORT", "55355")))
SOCK_PUENTE = os.environ.get("ARCADE_SOCK", "/tmp/arcade_act.sock")
HISTORIAL = os.environ.get("ARCADE_HISTORIAL", "/home/konan/roms/historial.lpl")
PERIODO = 1 / 60              # 16.6 ms, un cuadro del juego
TIEMPO_ESPERA = 0.2           # s que se espera la respuesta de RetroArch

# Juegos con telemetría: nombre del archivo de la ROM -> dirección de las vidas
JUEGOS = {
    "pacman.nes": (0x067, "vidas"),
    "pong.nes": (0x013, "puntos"),
    "tetris.nes": (0x048, "fin"),
}
EVENTOS = {"vidas": "vida perdida", "puntos": "punto en contra", "fin": "fin de la partida"}


def evento(tipo, antes, ahora):
    if tipo == "fin":
        return ahora == 10 and antes != 10
    return (ahora < antes) == (tipo == "vidas")

# Órdenes que se mandan en cada evento (protocolo de la guía, sección 5.C)
DURACION_MS = 500             # duración del aviso al perder una vida
AL_PERDER_VIDA = [f"VIB {DURACION_MS}", f"BUZ 2700 {DURACION_MS}", "LED 1 1", "LED 2 1"]
AL_TERMINAR_AVISO = ["LED 1 0", "LED 2 0"]   # motor y buzzer los apaga la Pico
AL_EMPEZAR_PARTIDA = ["LED 1 0", "LED 2 0"]


def log(msg):
    # systemd guarda la salida estándar en journalctl
    print(f"[telemetria {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# Socket UDP para preguntarle a RetroArch
ra = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ra.settimeout(TIEMPO_ESPERA)

# Socket UNIX de datagramas hacia el puente (Clase 11)
puente = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

# El historial solo se vuelve a leer cuando cambia su fecha de modificación
_historial = {"mtime": None, "juego": None}


def leer_historial():
    """Regresa el nombre de la ROM de la primera entrada del historial, o None."""
    try:
        with open(HISTORIAL, encoding="utf-8") as f:
            texto = f.read()
    except OSError:
        return None
    try:
        items = json.loads(texto).get("items", [])
        ruta = items[0].get("path", "") if items else ""
    except (ValueError, AttributeError, TypeError):
        # Formato viejo de RetroArch: la primera línea es la ruta
        ruta = texto.splitlines()[0] if texto else ""
    return os.path.basename(ruta) or None


def juego_actual():
    """Nombre de la última ROM que abrió RetroArch (None si no hay historial)."""
    try:
        mtime = os.stat(HISTORIAL).st_mtime
    except OSError:
        return None
    if mtime != _historial["mtime"]:
        _historial["mtime"] = mtime
        _historial["juego"] = leer_historial()
    return _historial["juego"]


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
    log(f"historial de RetroArch: {HISTORIAL}")
    log(f"juegos con telemetría: {', '.join(JUEGOS)}")
    juego_antes = None
    vidas_antes = None
    conectado = False
    apagar_en = None              # momento en que se apagan los LEDs (None = nada pendiente)
    siguiente = time.monotonic()

    while True:
        # Apagar los LEDs al terminar el aviso, sin detener el ciclo de 16.6 ms
        if apagar_en is not None and time.monotonic() >= apagar_en:
            enviar(AL_TERMINAR_AVISO)
            apagar_en = None

        # ¿Cambió el juego? Entonces no se compara con las vidas del juego anterior
        juego = juego_actual()
        if juego != juego_antes:
            nota = "" if juego in JUEGOS else " (sin telemetría)"
            log(f"juego actual: {juego or 'ninguno'}{nota}")
            juego_antes = juego
            vidas_antes = None
            conectado = False
            if apagar_en is not None:
                enviar(AL_TERMINAR_AVISO)
                apagar_en = None

        # Juego sin telemetría: no se lee su RAM, solo se revisa si cambia el juego
        if juego not in JUEGOS:
            time.sleep(0.5)
            siguiente = time.monotonic()
            continue

        direccion, tipo = JUEGOS[juego]
        vidas = leer_ram(direccion)

        if vidas is None:
            if conectado:
                log("RetroArch no contesta; reintentando")
                conectado = False
            vidas_antes = None          # al volver, no comparar con datos viejos
            time.sleep(1)
            siguiente = time.monotonic()
            continue

        if not conectado:
            log(f"conectado a RetroArch ({juego}), valor = {vidas}")
            conectado = True

        if vidas_antes is not None and vidas != vidas_antes:
            if evento(tipo, vidas_antes, vidas):
                log(f"{EVENTOS[tipo]} ({vidas_antes} -> {vidas})")
                enviar(AL_PERDER_VIDA)
                apagar_en = time.monotonic() + DURACION_MS / 1000
            elif tipo != "fin" or vidas_antes == 10:
                log(f"partida nueva ({vidas_antes} -> {vidas})")
                enviar(AL_EMPEZAR_PARTIDA)
                apagar_en = None
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
