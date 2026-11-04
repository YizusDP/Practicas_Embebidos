import subprocess
import time
import spidev

DC, RST = 25, 24

def pin(n, alto):
    subprocess.run(["pinctrl", "set", str(n), "op", "dh" if alto else "dl"], check=True)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1_000_000

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

colores = [0xF800, 0x07E0, 0x001F, 0xFFFF]   # rojo, verde, azul, blanco
fila = bytearray(960)
for x in range(480):
    c = colores[x * 4 // 480]
    fila[2 * x] = c >> 8
    fila[2 * x + 1] = c & 0xFF
cuadro = bytes(fila) * 320

for modo in (0, 3):
    spi.mode = modo
    print(f"Probando modo SPI {modo}...")
    pin(DC, 1)
    pin(RST, 0)
    time.sleep(0.1)
    pin(RST, 1)
    time.sleep(0.15)

    cmd(0x11)
    time.sleep(0.12)
    for c, d in SEQ:
        cmd(c, d)
    time.sleep(0.12)
    cmd(0x21)
    cmd(0x29)
    cmd(0x2A, b"\x00\x00\x01\xDF")   # columnas 0 a 479
    cmd(0x2B, b"\x00\x00\x01\x3F")   # filas 0 a 319
    cmd(0x2C)
    pin(DC, 1)
    spi.writebytes2(cuadro)
    input(f"Modo {modo} enviado. Mira la pantalla y presiona Enter...")

spi.close()
print("Listo")
