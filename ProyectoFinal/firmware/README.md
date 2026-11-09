# Firmware del control (Raspberry Pi Pico)

Firmware del mando del arcade. La Pico lee **10 botones** (dos 74HC165 en cascada) y
**3 ejes analógicos** (joystick X/Y y potenciómetro), y se presenta ante la Raspberry Pi 4
como un **control USB HID**. Por el mismo enlace HID recibe de la Pi las órdenes para el
**motor de vibración, el buzzer y 2 LEDs**.

La lectura no usa la CPU: la PIO y el ADC escriben en SRAM por DMA, y el lazo principal
solo atiende el USB, aplica las órdenes de actuadores y alimenta el *watchdog*.

## Archivos

| Archivo | Qué hace |
|---|---|
| `main.c` | Inicialización, lazo principal (despertado cada 1 ms) y *watchdog* de 250 ms |
| `controls_report.h` | `controls_report_t`: imagen de los controles en SRAM = reporte HID de 10 bytes |
| `read_74hc165.c/.h`, `read_74hc165.pio` | Botones: la PIO arma tramas de 10 bits; 2 canales DMA encadenados las copian a SRAM |
| `read_adc.c/.h` | Ejes: ADC en *round-robin* (4 canales, 4 kHz por canal) con DMA en anillo de 8 bytes |
| `usb_data_tx.c/.h` | TinyUSB: descriptores HID, envío del reporte de entrada y recepción del reporte de salida |
| `actuadores.c/.h` | Motor (PWM 20 kHz), buzzer (PWM de frecuencia variable) y LEDs; se apagan con alarmas |
| `tusb_config.h` | Configuración de TinyUSB (solo dispositivo HID) |
| `CMakeLists.txt`, `pico_sdk_import.cmake` | Proyecto de CMake para el Pico SDK |
| `prueba_actuadores.py` | Prueba de los actuadores desde una PC o desde la Pi (menú interactivo) |

## Conexiones

| Pin de la Pico | Uso |
|---|---|
| GP16 | Q7 (datos) del último 74HC165 |
| GP17 | LD (carga paralela) de los 74HC165 |
| GP18 | CLK de los 74HC165 |
| GP26 / GP27 / GP28 | Ejes X, Y (joystick) y Z (potenciómetro) |
| GP15 | Motor de vibración (a través de transistor NPN + diodo de rueda libre; nunca directo) |
| GP12 | Buzzer |
| GP10 / GP11 | LED 1 / LED 2 (con resistencia de 220 Ω) |
| GP0 / GP1 | UART0 (`printf` de depuración, 115200 baudios); el USB lo usa el HID |

Los botones usan resistencias *pull-down* (`CONTROLS_BUTTONS_ACTIVE_LOW = 0`).

## Compilar

Requisitos: [Pico SDK](https://github.com/raspberrypi/pico-sdk) 2.x (probado con 2.1.1),
`cmake` ≥ 3.13 y el compilador `arm-none-eabi-gcc`. La extensión *Raspberry Pi Pico* de
VS Code instala todo esto.

Desde esta carpeta (`ProyectoFinal/firmware`):

```bash
mkdir build
cd build
cmake ..
make -j4
```

Si `cmake` no encuentra el SDK, indícale dónde está antes de `cmake ..`:

```bash
export PICO_SDK_PATH=/ruta/al/pico-sdk          # Linux / macOS
$env:PICO_SDK_PATH = "C:\ruta\al\pico-sdk"      # Windows (PowerShell)
```

El resultado queda en `build/arcade_ctrl.uf2`. Tamaño con el SDK 2.1.1:

```
   text    data     bss     dec     hex filename
  23476       0    3520   26996    6974 arcade_ctrl.elf
```

## Grabar en la Pico

1. Desconecta la Pico, mantén presionado **BOOTSEL** y conéctala por USB.
2. Aparece como una unidad llamada `RPI-RP2`.
3. Copia `build/arcade_ctrl.uf2` a esa unidad. La Pico se reinicia sola con el firmware nuevo.

## Protocolo USB HID

**Reporte de entrada** (Pico → Pi), 10 bytes, sin *Report ID*, cada 1 ms:

| Bytes | Contenido |
|---|---|
| 0-1, 2-3, 4-5 | Ejes X, Y, Z (`uint16_t`, 0 a 4095) |
| 6-7 | Constante (ADC3 / VSYS, diagnóstico; el host lo ignora) |
| 8-9 | 10 botones (bits 0-9) + 6 bits de relleno |

**Reporte de salida** (Pi → Pico), 8 bytes, enteros de 16 bits en *little-endian*:

| Byte 0 | Orden | Bytes siguientes |
|---|---|---|
| `1` | Vibrar | 1-2 = duración en ms (1 a 5000) |
| `2` | Buzzer | 1-2 = frecuencia en Hz (100 a 5000), 3-4 = duración en ms (1 a 5000) |
| `3` | LED | 1 = LED (1 o 2), 2 = estado (0 o 1) |

Ejemplo: vibrar 300 ms → `01 2c 01 00 00 00 00 00` (300 = `0x012C`, byte bajo primero).
La Pico lo recibe en `tud_hid_set_report_cb()` (`usb_data_tx.c`).

## Probar

**Botones y ejes** (en la Pi, con el control conectado):

```bash
lsusb | grep -i cafe                      # debe aparecer cafe:4001
sudo apt install evtest && sudo evtest    # elegir "Arcade Controller Equipo Dinamita"
```

**Actuadores** con `prueba_actuadores.py`:

```bash
pip install hidapi
python3 prueba_actuadores.py     # en Linux puede requerir sudo o la regla de udev de pi/instalar.sh
```

**Actuadores** sin Python (en la Pi, después de correr `pi/instalar.sh`):

```bash
# vibrar 300 ms (el primer \x00 es el "report ID" que pide hidraw; el kernel lo quita)
echo -ne '\x00\x01\x2c\x01\x00\x00\x00\x00\x00' | sudo tee /dev/arcade_hid >/dev/null
```

## Notas

- **Watchdog:** el lazo solo lo alimenta si los DMA de botones y ADC siguen avanzando
  (revisión cada 25 ms). Si se detienen 4 revisiones seguidas, la Pico se reinicia a los 250 ms.
  Al arrancar imprime por UART si el último reinicio fue por el *watchdog*.
- **Periodo de lectura de botones:** lo fija el divisor de la PIO (`BTN_SM_CLKDIV` en
  `read_74hc165.h`). Con 125 la trama dura 3417 ciclos de 1 µs = **3.417 ms**; con 182.91
  dura 5.000 ms (el valor comprometido en el Avance 1). Se mide en GP17 (LD) con osciloscopio.
- **VID/PID** `cafe:4001` son de pruebas (en `usb_data_tx.c`); la regla de udev de la Pi los usa.
