#!/bin/bash
MISO=9
pinctrl set $MISO ip pd

probar() {   # nombre color pin gpio
  read -p "Conecta la punta suelta del cable $2 ($1, pin $3) al PIN 21 y presiona Enter..."
  local ok=0 i a b
  for i in 1 2 3 4 5; do
    pinctrl set "$4" op dh; sleep 0.02
    if pinctrl get $MISO | grep -q "| hi"; then a=1; else a=0; fi
    pinctrl set "$4" op dl; sleep 0.02
    if pinctrl get $MISO | grep -q "| lo"; then b=1; else b=0; fi
    if (( a && b )); then ok=$((ok + 1)); fi
  done
  echo "$1 ($2): $ok de 5"
  read -p "Quita esa punta del pin 21 y presiona Enter..."
}

probar CS blanco 24 8
probar DC gris 22 25
probar RST morado 18 24
probar SDA naranja 19 10
probar SCL verde 23 11
echo "Listo. Reinicia con: sudo reboot"
