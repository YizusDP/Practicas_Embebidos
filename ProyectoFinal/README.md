# Terminal de Juegos Retro con Mando Embebido

Proyecto integrador de Fundamentos de Sistemas Embebidos (FI UNAM, grupo 6, equipo 2).

Una Raspberry Pi Pico lee los botones y el potenciómetro del control y se presenta como control USB.
Una Raspberry Pi 4 corre RetroArch en una pantalla TFT de 3.5''. Un proceso de telemetría lee la RAM
del juego y manda órdenes a la Pico para activar el motor, el buzzer y los LEDs.

```
[10 botones] -> 2x74HC165 -> PIO+DMA -+
[Potenciómetro] -> ADC ---------------+-> Pico -> USB HID -> Pi 4: RetroArch -> TFT ST7796S (SPI)
                                                                 | UDP 55355
Pico <- HID (reporte de salida) <- puente_hid.py <- AF_UNIX DGRAM <- telemetria.py
  |
  +-> motor, buzzer, LEDs
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `firmware/` | Firmware de la Pico (Pico SDK) |
| `pi/` | Telemetría, puente HID, servicios de systemd e instalador |
| `pantalla/` | Configuración de la TFT y de RetroArch (`ra_gl.cfg`) |
| `avance3/` | Reporte del Avance 3 |

## Reproducir la consola (Raspberry Pi 4)

Probado en Raspberry Pi 4 Model B Rev 1.5 con Raspberry Pi OS Lite (Debian 13 trixie),
kernel 6.18 y RetroArch 1.20.0, usuario `konan`.

1. Conectar la pantalla según `pantalla/README.md`.
2. Clonar el repo e instalar:
   ```bash
   git clone https://github.com/YizusDP/Practicas_Embebidos.git
   cd Practicas_Embebidos/ProyectoFinal
   sudo bash pi/instalar.sh
   ```
3. Copiar la ROM a `~/roms/pacman.nes`. **Las ROMs no se incluyen en el repo.**
   Para otro juego, cambiar `ARCADE_ROM` en `/etc/default/arcade`.
4. Reiniciar: `sudo reboot`. Al encender, el juego aparece solo en la pantalla.

El instalador:
- instala RetroArch y el core Nestopia;
- genera el firmware de la pantalla y agrega su configuración a `/boot/firmware/config.txt`;
- copia los programas y `ra_gl.cfg` a `/opt/arcade`;
- instala y habilita los servicios de `pi/systemd/`.

## Servicios

| Servicio | Qué hace | Prioridad |
|---|---|---|
| `arcade-retroarch` | RetroArch con el juego en la TFT | `Nice=-5` (alta) |
| `arcade-puente` | Único proceso que escribe en el control (`/dev/arcade_hid`) | normal |
| `arcade-telemetria` | Lee las vidas (`0x067`) y manda órdenes al puente | `Nice=10` (baja) |

Los tres tienen `Restart=always` y se agrupan en `arcade.target`.

```bash
systemctl status arcade.target                         # estado
journalctl -u arcade-retroarch -u arcade-puente -u arcade-telemetria -f   # logs
sudo systemctl disable --now arcade.target             # apagar el arcade (la Pi se comparte con otro proyecto)
sudo systemctl enable --now arcade.target              # volver a encenderlo
```

## Protocolo Pi -> Pico

Todo viaja por el mismo USB HID del control. La telemetría manda texto al puente
(`VIB 300`, `BUZ 220 300`, `LED 1 1`) y el puente lo traduce a un **reporte de salida HID
de 8 bytes** (enteros en little-endian) que escribe en `/dev/arcade_hid`:

| Byte 0 | Orden | Bytes siguientes | Efecto |
|---|---|---|---|
| `1` | VIB | 1-2 = ms | Vibra el motor |
| `2` | BUZ | 1-2 = Hz, 3-4 = ms | Suena el buzzer |
| `3` | LED | 1 = id (1 o 2), 2 = estado (0 o 1) | Apaga o enciende un LED |

Ejemplo: `VIB 300` viaja como `01 2c 01 00 00 00 00 00`. La Pico lo recibe en
`tud_hid_set_report_cb()` (`firmware/usb_data_tx.c`). La regla de udev
`/etc/udev/rules.d/99-arcade.rules` crea `/dev/arcade_hid` y permite escribirlo sin root.

## Notas de RetroArch

- Los comandos de red están en UDP `127.0.0.1:55355` (`network_cmd_enable = "true"`).
- Con Nestopia funciona `READ_CORE_RAM`; `READ_CORE_MEMORY` no (el core no define mapa de memoria).
- **No mandar `GET_STATUS`**: tumba RetroArch 1.20.0 con este core.
- `pi/herramientas/buscar_vidas.py` ubica la dirección de las vidas comparando la RAM entre muertes.

## Pruebas de robustez

| Falla | Cómo inducirla | Recuperación |
|---|---|---|
| F1: proceso muerto | `sudo kill -9 $(pidof retroarch)` | systemd lo relanza en unos 2 s |
| F2: control desconectado | Desconectar el USB de la Pico en plena partida | RetroArch lo reconoce al reconectar; el puente reabre `/dev/arcade_hid` cada 1 s |
