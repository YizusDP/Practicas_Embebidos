# Terminal de Juegos Retro con Mando Embebido

Proyecto integrador de Fundamentos de Sistemas Embebidos (FI UNAM, grupo 6, equipo 2).

Una Raspberry Pi Pico lee los 10 botones y el joystick del mando y se presenta como control USB HID.
Una Raspberry Pi 4 corre RetroArch (core Nestopia) en una pantalla TFT ST7796S de 3.5'' por SPI.
Un proceso de telemetría lee la RAM del juego y manda órdenes a la Pico para activar el motor,
el buzzer y los LEDs. Todo arranca solo al encender, sin teclado.

```
[10 botones] -> 2x74HC165 -> PIO+DMA -+
[Joystick X/Y] -> ADC + DMA ----------+-> Pico -> USB HID -> Pi 4: RetroArch -> TFT ST7796S (SPI)
                                                                 | UDP 55355
Pico <- HID (reporte de salida) <- puente_hid.py <- AF_UNIX DGRAM <- telemetria.py
  |
  +-> motor, buzzer, LEDs
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `firmware/` | Firmware de la Pico (Pico SDK). Detalle en `firmware/README.md` |
| `pi/` | Telemetría, puente HID, servicios de systemd e instalador |
| `pantalla/` | Configuración de la TFT y de RetroArch (`ra_gl.cfg`). Detalle en `pantalla/README.md` |
| `Entrega_FInal_E2/` | Reporte técnico final (LaTeX) |

## Material necesario

- Raspberry Pi 4 Model B con microSD de 8 GB o más y fuente de 5 V / 3 A.
- Pantalla TFT SPI de 3.5'' con controlador ST7796S (480x320).
- Raspberry Pi Pico (RP2040) con el mando: 2 registros 74HC165, 10 botones con *pull-down*,
  joystick analógico, motor de vibración con transistor, buzzer pasivo y 2 LEDs.
- Cable USB de la Pico a la Pi 4.
- Una PC con el Pico SDK para compilar el firmware (solo la primera vez).

## Paso 1: compilar y grabar el firmware de la Pico

Requisitos: [Pico SDK](https://github.com/raspberrypi/pico-sdk) 2.x (probado con 2.1.1),
`cmake` 3.13 o mayor y `arm-none-eabi-gcc`. La extensión *Raspberry Pi Pico* de VS Code instala todo.

```bash
git clone https://github.com/YizusDP/Practicas_Embebidos.git
cd Practicas_Embebidos/ProyectoFinal/firmware
mkdir build
cd build
cmake ..
make -j4
```

Si `cmake` no encuentra el SDK, antes de `cmake ..`:

```bash
export PICO_SDK_PATH=/ruta/al/pico-sdk          # Linux / macOS
$env:PICO_SDK_PATH = "C:\ruta\al\pico-sdk"      # Windows (PowerShell)
```

Para grabarla: mantener presionado **BOOTSEL** en la Pico, conectarla por USB y copiar
`build/arcade_ctrl.uf2` a la unidad `RPI-RP2` que aparece.
La Pico se reinicia sola y queda como control USB (VID `cafe`, PID `4001`).
Las conexiones de cada pin están en `firmware/README.md`.

## Paso 2: preparar la Raspberry Pi 4

1. Grabar **Raspberry Pi OS Lite de 64 bits** (Debian 13) con Raspberry Pi Imager.
   En las opciones del Imager crear el usuario **`konan`** y activar SSH.
   > Los servicios usan el usuario `konan`. Si usas otro nombre, cámbialo en
   > `pi/instalar.sh` (variable `USUARIO`) y en los `User=`, `Group=` y `HOME=` de `pi/systemd/*.service`.
2. Conectar la pantalla según la tabla de `pantalla/README.md`
   (SPI0: SCLK pin 23, MOSI pin 19, RST pin 18, DC pin 22, CS pin 24, 5 V pin 2/4, GND pin 6).
3. Encender la Pi, entrar por SSH y clonar el repo:
   ```bash
   sudo apt-get update
   sudo apt-get install -y git
   git clone https://github.com/YizusDP/Practicas_Embebidos.git
   cd Practicas_Embebidos/ProyectoFinal
   ```
4. Ejecutar el instalador:
   ```bash
   sudo bash pi/instalar.sh
   ```
5. Copiar las ROMs a `/home/konan/roms/`. **Las ROMs no se incluyen en el repo.**
   El juego por defecto es `/home/konan/roms/pacman.nes`; para cambiarlo, editar `ARCADE_ROM`
   en `/etc/default/arcade`. Los juegos con telemetría son `pacman.nes`, `pong.nes` y `tetris.nes`.
6. Conectar la Pico a un puerto USB de la Pi y reiniciar:
   ```bash
   sudo reboot
   ```

Al encender, el juego aparece solo en la pantalla y el mando funciona sin configurar nada más.

### Qué hace el instalador

- Instala RetroArch, el core Nestopia y Python 3.
- Genera el firmware de la pantalla (`/lib/firmware/st7796s.bin`) y agrega su configuración a
  `/boot/firmware/config.txt`.
- Copia `telemetria.py`, `puente_hid.py` y `ra_gl.cfg` a `/opt/arcade`.
- Crea la regla de udev que expone el mando en `/dev/arcade_hid`.
- Instala y habilita los servicios de `pi/systemd/`.

Se puede correr varias veces sin problema.

## Paso 3: comprobar que funciona

```bash
systemctl status arcade.target
ls -l /dev/arcade_hid
journalctl -u arcade-retroarch -u arcade-puente -u arcade-telemetria -f
```

- `arcade.target` debe estar `active`.
- `/dev/arcade_hid` debe apuntar a un `hidraw` cuando la Pico está conectada.
- Al perder una vida en Pac-Man, el motor vibra, suena el buzzer y se encienden los LEDs.

## Uso

| Acción | Cómo |
|---|---|
| Jugar | Cruceta o joystick para mover; A y B son los botones grandes |
| Cambiar de juego | **Select + Start** abre el menú de RetroArch; el juego se elige en *Historial* |
| Apagar el arcade al arrancar | `sudo systemctl disable --now arcade.target` |
| Volver a encenderlo | `sudo systemctl enable --now arcade.target` |

## Servicios

| Servicio | Qué hace | Prioridad |
|---|---|---|
| `arcade-retroarch` | RetroArch con el juego en la TFT (DRM/KMS, sin escritorio) | `Nice=-5` (alta) |
| `arcade-puente` | Único proceso que escribe en el mando (`/dev/arcade_hid`) | normal |
| `arcade-telemetria` | Lee la RAM del juego y manda órdenes al puente | `Nice=10` (baja) |

Los tres tienen `Restart=always` y se agrupan en `arcade.target`.

## Telemetría por juego

| Juego | Dirección RAM | Evento que activa los actuadores |
|---|---|---|
| Pac-Man | `0x067` | Baja el contador de vidas |
| Pong | `0x013` | Sube el marcador del oponente |
| Tetris | `0x048` | Estado igual a 10 (fin de la partida) |

## Protocolo Pi -> Pico

La telemetría manda texto al puente (`VIB 500`, `BUZ 2700 500`, `LED 1 1`) por el socket
`/tmp/arcade_act.sock`, y el puente lo traduce a un **reporte de salida HID de 8 bytes**
(enteros en little-endian):

| Byte 0 | Orden | Bytes siguientes | Efecto |
|---|---|---|---|
| `1` | VIB | 1-2 = ms | Vibra el motor |
| `2` | BUZ | 1-2 = Hz, 3-4 = ms | Suena el buzzer |
| `3` | LED | 1 = id (1 o 2), 2 = estado (0 o 1) | Apaga o enciende un LED |

La Pico lo recibe en `tud_hid_set_report_cb()` (`firmware/usb_data_tx.c`).

## Notas de RetroArch

- Comandos de red en UDP `127.0.0.1:55355` (`network_cmd_enable = "true"`).
- Con Nestopia funciona `READ_CORE_RAM`; `READ_CORE_MEMORY` no.
- **No mandar `GET_STATUS`**: tumba RetroArch 1.20.0 con este core.
- No hay salida de audio: `audio_driver = "null"`.

## Pruebas de robustez

| Falla | Cómo inducirla | Recuperación |
|---|---|---|
| F1: proceso muerto | `sudo kill -9 $(pidof retroarch)` | systemd lo relanza (3.4 s medidos) |
| F2: mando desconectado | Desconectar el USB de la Pico en plena partida | RetroArch lo reconoce al reconectar; el puente reabre `/dev/arcade_hid` cada 1 s |

## Problemas comunes

| Síntoma | Solución |
|---|---|
| Pantalla en blanco | Revisar cables y que `config.txt` tenga la sección `mipi-dbi-spi`; reiniciar |
| No aparece `/dev/arcade_hid` | Revisar que la Pico tenga el firmware (`lsusb` debe mostrar `cafe:4001`) |
| RetroArch no arranca | `journalctl -u arcade-retroarch`; revisar que exista la ROM de `/etc/default/arcade` |
| El mando no responde en el juego | Reiniciar con la Pico ya conectada |
