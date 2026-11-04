import subprocess
import time
import spidev

DC, RST = 25, 24

def pin(n, alto):
    subprocess.run(["pinctrl", "set", str(n), "op", "dh" if alto else "dl"], check=True)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.mode = 0
spi.max_speed_hz = 8_000_000

def cmd(c, data=b""):
    pin(DC, 0)
    spi.writebytes2(bytes([c]))
    if data:
        pin(DC, 1)
        spi.writebytes2(bytes(data))

SEQ = [
    (0x36, [0x28]),
    (0x3A, [0x55]),
    (0xF0, [0xC3]),
    (0xF0, [0x96]),
    (0xB4, [0x02]),
    (0xB7, [0xC6]),
    (0xC0, [0xC0, 0x00]),
    (0xC1, [0x13]),
    (0xC2, [0xA7]),
    (0xC5, [0x21]),
    (0xE8, [0x40, 0x8A, 0x1B, 0x1B, 0x23, 0x0A, 0xAC, 0x33]),
    (0xE0, [0xD2, 0x05, 0x08, 0x06, 0x05, 0x02, 0x2A, 0x44, 0x46, 0x39, 0x15, 0x15, 0x2D, 0x32]),
    (0xE1, [0x96, 0x08, 0x0C, 0x09, 0x09, 0x25, 0x2E, 0x43, 0x42, 0x35, 0x11, 0x11, 0x28, 0x2E]),
    (0xF0, [0x3C]),
    (0xF0, [0x69]),
]

colores = [b"\xF8\x00", b"\x00\x1F"]   # rojo y azul
cuadros = [c * (480 * 320) for c in colores]
vuelta = 0

print("Mandando colores. Mueve los cables con cuidado. Ctrl+C para salir.")
try:
    while True:
        pin(DC, 1)
        pin(RST, 0)
        time.sleep(0.02)
        pin(RST, 1)
        time.sleep(0.12)
        cmd(0x11)
        time.sleep(0.12)
        for c, d in SEQ:
            cmd(c, d)
        cmd(0x21)
        cmd(0x29)
        cmd(0x2A, b"\x00\x00\x01\xDF")
        cmd(0x2B, b"\x00\x00\x01\x3F")
        cmd(0x2C)
        pin(DC, 1)
        spi.writebytes2(cuadros[vuelta % 2])
        vuelta += 1
        print("Vuelta", vuelta, end="\r")
except KeyboardInterrupt:
    spi.close()
    print("\nListo")
