import subprocess
import time
import spidev

DC, RST = 25, 24

def pin(n, alto):
    subprocess.run(["pinctrl", "set", str(n), "op", "dh" if alto else "dl"], check=True)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.mode = 0
spi.max_speed_hz = 1_000_000

def cmd(c, data=b""):
    pin(DC, 0)
    spi.writebytes2(bytes([c]))
    if data:
        pin(DC, 1)
        spi.writebytes2(bytes(data))

pin(DC, 1)

pin(RST, 0)
input("PASO 1, RST en bajo. Anota que se ve y presiona Enter...")

pin(RST, 1)
time.sleep(0.15)
input("PASO 2, reset terminado. Anota que se ve y presiona Enter...")

cmd(0x11)
time.sleep(0.15)
cmd(0x3A, b"\x55")
cmd(0x29)
input("PASO 3, comandos de encendido. Anota que se ve y presiona Enter...")

cmd(0x21)
input("PASO 4, colores invertidos. Anota que se ve y presiona Enter...")

cmd(0x20)
input("PASO 5, inversion apagada. Anota que se ve y presiona Enter...")

cmd(0x2A, b"\x00\x00\x01\x3F")
cmd(0x2B, b"\x00\x00\x01\xDF")
cmd(0x2C)
pin(DC, 1)
spi.writebytes2(b"\xF8\x00" * (320 * 480))
input("PASO 6, pantalla roja enviada. Anota que se ve y presiona Enter...")

spi.close()
print("Listo")
