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

def enviar(byte, dc):
    pin(DC, dc)
    spi.writebytes2(bytes([byte]))

pin(DC, 1)
pin(RST, 0)
time.sleep(0.1)
pin(RST, 1)
time.sleep(0.15)

enviar(0x11, 0)
time.sleep(0.15)
enviar(0x29, 0)
enviar(0x20, 0)
input("A) Inversion apagada. Anota el color y presiona Enter...")

for i in range(3):
    enviar(0x21, 1)
    time.sleep(1)
    enviar(0x20, 1)
    time.sleep(1)
input("B) Se mando como DATO durante 6 seg. Cambio el color? Enter...")

for i in range(3):
    enviar(0x21, 0)
    time.sleep(1)
    enviar(0x20, 0)
    time.sleep(1)
input("C) Se mando como COMANDO durante 6 seg. Cambio el color? Enter...")

spi.close()
print("Listo")
