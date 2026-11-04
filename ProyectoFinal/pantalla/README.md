# Pantalla ST7796S SPI para el arcade

Raspberry Pi 4 con pantalla TFT de 3.5" en SPI, 480x320 horizontal.

## Conexion
| Pantalla | Pi |
|---|---|
| GND | Pin 6 |
| VCC | Pin 2 |
| SCL | Pin 23 |
| SDA | Pin 19 |
| RST | Pin 18 |
| DC | Pin 22 |
| CS | Pin 24 |
| BL | Pin 4 |
| SDA-0 | Sin conectar |

## Instalacion
1. Generar el firmware con `python3 gen_st7796.py`.
2. Copiar `st7796s.bin` a `/lib/firmware/`.
3. Agregar `config_txt_pantalla.txt` a `/boot/firmware/config.txt` y reiniciar.

## Uso
Video:
sudo mpv --vo=drm --drm-device=/dev/dri/card2 --drm-connector=SPI-1 --no-audio --loop video.mp4

RetroArch:
sudo retroarch --config ~/ra_gl.cfg --menu

## Resultado
18.3 FPS medidos a 50 MHz, con core_freq_min=500.
