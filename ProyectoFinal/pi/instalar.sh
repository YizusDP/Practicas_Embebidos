#!/usr/bin/env bash
# Instala el arcade en una Raspberry Pi 4 con Raspberry Pi OS Lite (Debian 13).
# Uso, desde la carpeta ProyectoFinal del repo:
#     sudo bash pi/instalar.sh
# Es seguro correrlo varias veces.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Correr con sudo: sudo bash pi/instalar.sh" >&2
    exit 1
fi

USUARIO="konan"
PF="$(cd "$(dirname "$0")/.." && pwd)"     # carpeta ProyectoFinal
DESTINO="/opt/arcade"
CONFIG_TXT="/boot/firmware/config.txt"

echo "== 1/5 Paquetes"
apt-get update -qq
apt-get install -y -qq retroarch libretro-nestopia python3

echo "== 2/5 Pantalla TFT ST7796S"
python3 "$PF/pantalla/gen_st7796.py"            # genera st7796s.bin en la carpeta actual
install -m 644 st7796s.bin /lib/firmware/st7796s.bin
rm -f st7796s.bin
if ! grep -q "mipi-dbi-spi" "$CONFIG_TXT"; then
    { echo; echo "# Pantalla del arcade"; cat "$PF/pantalla/config_txt_pantalla.txt"; } >> "$CONFIG_TXT"
    echo "   config.txt actualizado (requiere reinicio)"
else
    echo "   config.txt ya tenía la pantalla"
fi

echo "== 3/5 Programas en $DESTINO"
install -d -o "$USUARIO" -g "$USUARIO" "$DESTINO"
install -m 755 -o "$USUARIO" -g "$USUARIO" "$PF/pi/telemetria.py" "$PF/pi/puente_hid.py" "$DESTINO/"
install -m 644 -o "$USUARIO" -g "$USUARIO" "$PF/pantalla/ra_gl.cfg" "$DESTINO/ra_gl.cfg"
usermod -aG video,render,input "$USUARIO"
# Regla de udev: el hidraw del control (VID cafe, PID 4001) queda en /dev/arcade_hid
# y lo puede escribir el grupo input, así el puente no necesita root
cat > /etc/udev/rules.d/99-arcade.rules <<'REGLA'
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="cafe", ATTRS{idProduct}=="4001", MODE="0660", GROUP="input", SYMLINK+="arcade_hid"
REGLA
udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw

echo "== 4/5 Juego por defecto"
if [ ! -f /etc/default/arcade ]; then
    cat > /etc/default/arcade <<EOF
# Core y ROM que abre arcade-retroarch.service
ARCADE_CORE=/usr/lib/aarch64-linux-gnu/libretro/nestopia_libretro.so
ARCADE_ROM=/home/$USUARIO/roms/pacman.nes
EOF
fi
. /etc/default/arcade
if [ ! -f "$ARCADE_ROM" ]; then
    echo "   AVISO: falta la ROM $ARCADE_ROM (no se incluye en el repo; copiarla a mano)"
fi

echo "== 5/5 Servicios de systemd"
install -m 644 "$PF"/pi/systemd/arcade.target "$PF"/pi/systemd/arcade-*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable arcade.target arcade-retroarch.service arcade-puente.service arcade-telemetria.service

echo
echo "Listo. Reinicia con: sudo reboot"
echo "Estado:  systemctl status arcade.target"
echo "Logs:    journalctl -u arcade-retroarch -u arcade-puente -u arcade-telemetria -f"
echo "Apagar el arcade al arrancar: sudo systemctl disable --now arcade.target"
