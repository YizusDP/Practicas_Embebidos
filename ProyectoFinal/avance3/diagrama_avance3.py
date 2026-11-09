# Genera avance3/img/diagrama_bloques_v3.png. Uso: python3 avance3/diagrama_avance3.py
# Mismo estilo que ProyectoFinal/diagrama.py (Avance 2), actualizado al sistema integrado del Avance 3.
import asyncio, pathlib
from playwright.async_api import async_playwright

W, H = 1400, 800
FONT = "Inter, Liberation Sans, sans-serif"
TINTA, GRIS, ACENTO = "#1b2430", "#5b6675", "#0b6e6e"
LISTO_BG = "#e3f2f0"


def caja(x, y, w, h, titulo, lineas=(), tam=17):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{LISTO_BG}" stroke="{ACENTO}" stroke-width="2"/>'
    t = y + 26
    s += f'<text x="{x+w/2}" y="{t}" text-anchor="middle" font-weight="700" font-size="{tam}" fill="{TINTA}">{titulo}</text>'
    for l in lineas:
        t += 21
        s += f'<text x="{x+w/2}" y="{t}" text-anchor="middle" font-size="14.5" fill="{GRIS}">{l}</text>'
    return s


def nodo(x, y, w, h, titulo, sub):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="none" stroke="{TINTA}" stroke-width="2"/>'
            f'<text x="{x+18}" y="{y+30}" font-weight="700" font-size="20" fill="{TINTA}">{titulo}</text>'
            f'<text x="{x+18}" y="{y+52}" font-size="14.5" fill="{GRIS}">{sub}</text>')


def etiqueta(x, y, texto, ancla="middle"):
    return (f'<text x="{x}" y="{y}" text-anchor="{ancla}" font-size="14" font-weight="600" fill="{TINTA}" '
            f'paint-order="stroke" stroke="#fff" stroke-width="5">{texto}</text>')


def flecha(x1, y1, x2, y2, texto="", ex=0, ey=-9, ancla="middle"):
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{ACENTO}" stroke-width="2.4" marker-end="url(#fin)"/>'
    if texto:
        s += etiqueta((x1 + x2) / 2 + ex, (y1 + y2) / 2 + ey, texto, ancla)
    return s


def codo(puntos, texto="", ex=0, ey=0, ancla="middle"):
    pts = " ".join(f"{x},{y}" for x, y in puntos)
    s = f'<polyline points="{pts}" fill="none" stroke="{ACENTO}" stroke-width="2.4" marker-end="url(#fin)"/>'
    if texto:
        s += etiqueta(ex, ey, texto, ancla)
    return s


p = []
p.append(nodo(20, 20, 870, 670, "Mando", "Raspberry Pi Pico (RP2040), bare-metal con Pico SDK 2.1"))
p.append(nodo(1010, 20, 370, 670, "Consola", "Raspberry Pi 4 B 1 GB, RPi OS Lite (Debian 13)"))

# --- Mando: entradas ---
p.append(caja(45, 95, 190, 70, "10 botones", ["pull-down"]))
p.append(caja(45, 205, 190, 90, "74HC165 ×2", ["en cascada", "GP16 a GP18"], tam=16))
p.append(flecha(140, 165, 140, 205))
p.append(caja(45, 330, 190, 100, "Ejes analógicos", ["joystick X, Y", "potenciómetro Z", "GP26 a GP28"], tam=16))
p.append(caja(45, 520, 190, 135, "Actuadores", ["motor GP15 (PWM 20 kHz)", "buzzer GP12 (PWM)", "LED 1 GP10", "LED 2 GP11"], tam=16))

# --- Mando: tren autónomo por hardware ---
p.append(f'<rect x="275" y="190" width="590" height="250" rx="10" fill="none" stroke="{GRIS}" stroke-width="1.5" stroke-dasharray="5 4"/>')
p.append(f'<text x="290" y="212" font-size="15" font-weight="700" fill="{TINTA}">Adquisición por hardware (sin CPU)</text>')
p.append(caja(295, 225, 170, 80, "PIO0 SM0", ["tramas de 10 bits", "autopush"], tam=16))
p.append(caja(295, 340, 170, 80, "ADC", ["round-robin, 12 bits", "4 kHz por canal"], tam=16))
p.append(caja(495, 225, 150, 80, "DMA ×2", ["encadenados", "PIO → SRAM"], tam=16))
p.append(caja(495, 340, 150, 80, "DMA ×2", ["anillo de 8 B", "ADC → SRAM"], tam=16))
p.append(caja(675, 225, 170, 195, "g_controls", ["controls_report_t", "10 B en SRAM", "volatile", "= reporte HID"], tam=16))
p.append(flecha(295, 250, 235, 250, "LD, CLK", ey=-8))
p.append(flecha(235, 280, 295, 280, "Q7", ey=17))
p.append(flecha(235, 380, 295, 380))
p.append(flecha(465, 265, 495, 265))
p.append(flecha(465, 380, 495, 380))
p.append(flecha(645, 265, 675, 265))
p.append(flecha(645, 380, 675, 380))

# --- Mando: Core 0 ---
p.append(caja(400, 500, 445, 160, "Core 0: lazo principal (cada 1 ms)",
              ["TinyUSB: envía el reporte de entrada (10 B)", "recibe el reporte de salida (8 B) → actuadores",
               "watchdog de 250 ms (solo si los DMA avanzan)", "duerme con __wfi() entre eventos"], tam=16))
p.append(flecha(760, 420, 760, 500, "lectura de 16 bits", ex=10, ey=0, ancla="start"))
p.append(flecha(400, 588, 235, 588, "PWM / GPIO", ey=-9))

# --- Enlace USB HID ---
p.append(codo([(845, 545), (930, 545), (930, 140), (1035, 140)], "entrada 10 B, 1 ms", 960, 330))
p.append(codo([(1035, 170), (950, 170), (950, 615), (845, 615)], "salida 8 B", 980, 470))
p.append(etiqueta(940, 112, "USB HID", ancla="middle"))

# --- Consola ---
p.append(caja(1035, 95, 320, 90, "Kernel: usbhid / hidraw", ["/dev/input/eventX (botones, ejes)", "/dev/arcade_hid (regla de udev)"], tam=16))
p.append(caja(1035, 225, 320, 80, "RetroArch", ["Pac-Man, core Nestopia · Nice −5"], tam=16))
p.append(caja(1035, 345, 320, 80, "telemetria.py", ["vidas en RAM 0x067 · Nice 10"], tam=16))
p.append(caja(1035, 465, 320, 80, "puente_hid.py", ["texto → reporte de salida HID"], tam=16))
p.append(caja(1035, 585, 320, 80, "systemd: arcade.target", ["arranque automático, Restart=always"], tam=16))
p.append(flecha(1150, 185, 1150, 225, "evdev", ex=10, ey=4, ancla="start"))
p.append(flecha(1150, 305, 1150, 345, "UDP 55355", ex=10, ey=4, ancla="start"))
p.append(flecha(1150, 425, 1150, 465, "AF_UNIX DGRAM", ex=10, ey=4, ancla="start"))
p.append(codo([(1355, 505), (1372, 505), (1372, 165), (1355, 165)]))
p.append(etiqueta(1340, 340, "hidraw", ancla="end"))

# --- Pantalla ---
p.append(caja(1035, 715, 320, 72, "TFT 3.5\" ST7796S", ["SPI 50 MHz · panel-mipi-dbi (DRM)"], tam=16))
p.append(codo([(1035, 265), (1020, 265), (1020, 750), (1035, 750)]))
p.append(etiqueta(1012, 720, "KMS", ancla="end"))

# Leyenda
p.append(f'<rect x="30" y="725" width="26" height="18" rx="4" fill="{LISTO_BG}" stroke="{ACENTO}" stroke-width="2"/>')
p.append(f'<text x="66" y="740" font-size="15" fill="{TINTA}">Integrado en el Avance 3</text>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<defs>
<marker id="fin" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{ACENTO}"/></marker>
</defs><rect width="{W}" height="{H}" fill="#fff"/>{"".join(p)}</svg>'''


async def main():
    salida = pathlib.Path(__file__).parent / "img" / "diagrama_bloques_v3.png"
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        await pg.set_content(f'<body style="margin:0">{svg}</body>')
        await pg.screenshot(path=str(salida))
        await b.close()

asyncio.run(main())
