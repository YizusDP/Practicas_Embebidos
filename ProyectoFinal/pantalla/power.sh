#!/bin/bash
MISO=9
SALIDA=23
pinctrl set $MISO ip pd

probar() {
  read -p "Conecta el cable $1 entre el PIN 16 y el PIN 21, y presiona Enter..."
  local ok=0 i a b
  for i in 1 2 3 4 5; do
    pinctrl set $SALIDA op dh; sleep 0.02
    if pinctrl get $MISO | grep -q "| hi"; then a=1; else a=0; fi
    pinctrl set $SALIDA op dl; sleep 0.02
    if pinctrl get $MISO | grep -q "| lo"; then b=1; else b=0; fi
    if (( a && b )); then ok=$((ok + 1)); fi
  done
  echo "$1: $ok de 5"
  read -p "Quita ese cable y presiona Enter..."
}

probar negro
probar amarillo-1
probar amarillo-2
echo "Listo."
