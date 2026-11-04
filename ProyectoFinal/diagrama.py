# Genera docs/img/diagrama_bloques.png. Uso: python3 docs/diagrama.py
import asyncio, pathlib
from playwright.async_api import async_playwright

W, H = 1400, 800
FONT = "Inter, Liberation Sans, sans-serif"
TINTA, GRIS, ACENTO = "#1b2430", "#5b6675", "#0b6e6e"
LISTO_BG, FUT_BG, BORDE = "#e3f2f0", "#f4f5f7", "#9aa5b1"

def caja(x, y, w, h, titulo, lineas=(), listo=True, tam=17):
    fondo = LISTO_BG if listo else FUT_BG
    borde = ACENTO if listo else BORDE
    trazo = "" if listo else 'stroke-dasharray="7 5"'
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fondo}" stroke="{borde}" stroke-width="2" {trazo}/>'
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

def flecha(x1, y1, x2, y2, etiqueta="", listo=True, ex=0, ey=-9, ancla="middle", doble=False):
    color = ACENTO if listo else BORDE
    trazo = "" if listo else 'stroke-dasharray="7 5"'
    ini = 'marker-start="url(#ini)"' if doble else ""
    fin = "fin" if listo else "fing"
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2.4" {trazo} {ini} marker-end="url(#{fin})"/>'
    if etiqueta:
        s += (f'<text x="{(x1+x2)/2+ex}" y="{(y1+y2)/2+ey}" text-anchor="{ancla}" font-size="14" '
              f'font-weight="600" fill="{TINTA}" paint-order="stroke" stroke="#fff" stroke-width="5">{etiqueta}</text>')
    return s

def codo(puntos, etiqueta, ex, ey, listo=True):
    color = ACENTO if listo else BORDE
    trazo = "" if listo else 'stroke-dasharray="7 5"'
    fin = "fin" if listo else "fing"
    pts = " ".join(f"{x},{y}" for x, y in puntos)
    return (f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.4" {trazo} marker-end="url(#{fin})"/>'
            f'<text x="{ex}" y="{ey}" text-anchor="middle" font-size="14" font-weight="600" fill="{TINTA}" '
            f'paint-order="stroke" stroke="#fff" stroke-width="5">{etiqueta}</text>')

p = []
p.append(nodo(20, 20, 870, 640, "Mando", "Raspberry Pi Pico (RP2040), bare-metal con Pico SDK"))
p.append(nodo(1010, 20, 370, 640, "Consola", "Raspberry Pi 4 B 1 GB, RPi OS Lite"))

# Entradas
p.append(caja(45, 110, 170, 86, "8 botones", ["tact switch con", "pull-down 10 kΩ"]))
p.append(caja(45, 262, 170, 110, "74HC165 ×1 o ×2", ["carga paralela", "salida serie Q7", "3.3 V"]))
p.append(caja(45, 440, 170, 64, "Potenciómetro", ["por confirmar"], listo=False, tam=16))
p.append(caja(45, 555, 170, 84, "Actuadores", ["vibración, LEDs,", "buzzer"], listo=False, tam=16))
p.append(flecha(130, 196, 130, 262, "paralelo A–H", ex=8, ey=4, ancla="start"))

# RP2040
p.append(caja(345, 262, 150, 110, "PIO0 SM0", ["GP16 a GP18", "CLK 1 MHz", "captura 10.2 µs"]))
p.append(flecha(345, 300, 215, 300, "LD y CLK", ey=-10))
p.append(flecha(215, 342, 345, 342, "Q7", ey=20))

p.append(f'<rect x="530" y="100" width="340" height="300" rx="10" fill="none" stroke="{GRIS}" stroke-width="1.5" stroke-dasharray="3 4"/>')
p.append(f'<text x="548" y="125" font-size="15" font-weight="700" fill="{TINTA}">Core 1: adquisición</text>')
p.append(caja(548, 138, 304, 64, "Alarma de hardware cada 5 ms", ["IRQ de máxima prioridad, 200 Hz"], tam=15.5))
p.append(caja(548, 232, 304, 150, "IRQ de captura", ["antirrebote: 2 muestras + 20 ms", "diagnóstico de Q7 suelto", "medición de periodo", "estado y eventos estáticos"], tam=15.5))
p.append(flecha(600, 202, 600, 232))
p.append(flecha(548, 170, 420, 262, "dispara", ey=-14, ex=-10))
p.append(flecha(495, 330, 548, 330, "FIFO", ey=-9))

p.append(f'<rect x="530" y="452" width="340" height="190" rx="10" fill="none" stroke="{GRIS}" stroke-width="1.5" stroke-dasharray="3 4"/>')
p.append(f'<text x="548" y="477" font-size="15" font-weight="700" fill="{TINTA}">Core 0: comunicación</text>')
p.append(caja(548, 490, 304, 140, "Reporte y supervisión", ["USB CDC: líneas EST y EVT", "watchdog de 2 s", "LED GP25: normal o falla", "USB HID en Avance 3"], tam=15.5))
p.append(flecha(790, 382, 790, 490, "spin lock", ex=10, ey=-14, ancla="start"))
p.append(flecha(548, 597, 215, 597, "PWM/GPIO, Avance 3", listo=False))
p.append(flecha(215, 472, 530, 472, "ADC, por confirmar", listo=False))

# Consola
p.append(caja(1035, 110, 320, 106, "Script de verificación", ["verificar_modulo.sh", "PASA o FALLA, sin operador"]))
p.append(codo([(852, 530), (950, 530), (950, 163), (1035, 163)], "USB CDC", 950, 350))
p.append(caja(1035, 262, 320, 106, "RetroArch", ["Pong y Pac-Man", "Avance 3"], listo=False))
p.append(caja(1035, 414, 320, 86, "Telemetría", ["proceso aparte, Avance 3"], listo=False))
p.append(codo([(852, 600), (975, 600), (975, 315), (1035, 315)], "USB HID", 975, 470, listo=False))
p.append(flecha(1195, 368, 1195, 414, listo=False))

# Salidas
p.append(caja(1035, 690, 150, 84, "TFT 3.5\"", ["ST7796S, SPI"], listo=False, tam=16))
p.append(caja(1205, 690, 150, 84, "Red LAN", ["Ethernet"], listo=False, tam=16))
p.append(flecha(1110, 660, 1110, 690, listo=False))
p.append(flecha(1280, 660, 1280, 690, listo=False))

# Leyenda
p.append(f'<rect x="30" y="705" width="26" height="18" rx="4" fill="{LISTO_BG}" stroke="{ACENTO}" stroke-width="2"/>')
p.append(f'<text x="66" y="720" font-size="15" fill="{TINTA}">Funciona en el Avance 2 (firmware 0.2.0)</text>')
p.append(f'<rect x="30" y="738" width="26" height="18" rx="4" fill="{FUT_BG}" stroke="{BORDE}" stroke-width="2" stroke-dasharray="4 3"/>')
p.append(f'<text x="66" y="753" font-size="15" fill="{TINTA}">Planeado para los siguientes avances</text>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<defs>
<marker id="fin" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{ACENTO}"/></marker>
<marker id="fing" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{BORDE}"/></marker>
</defs><rect width="{W}" height="{H}" fill="#fff"/>{"".join(p)}</svg>'''

async def main():
    salida = pathlib.Path(__file__).parent / "img" / "diagrama_bloques.png"
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        await pg.set_content(f'<body style="margin:0">{svg}</body>')
        await pg.screenshot(path=str(salida))
        await b.close()
asyncio.run(main())
