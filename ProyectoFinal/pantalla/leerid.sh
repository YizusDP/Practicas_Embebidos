#!/bin/bash
# Lee la ID del panel ST7796 por bit-bang: CS=8 MISO=9 MOSI=10 SCK=11 RST=24 DC=25
CS=8; MISO=9; MOSI=10; SCK=11; RST=24; DC=25

alto() { pinctrl set "$1" op dh; }
bajo() { pinctrl set "$1" op dl; }

enviar() {   # manda un byte, primero el bit mas significativo
  local v=$1 i
  for i in 7 6 5 4 3 2 1 0; do
    if (( (v >> i) & 1 )); then alto $MOSI; else bajo $MOSI; fi
    alto $SCK
    bajo $SCK
  done
}

leer() {     # lee N bits y los imprime como 0 y 1
  local n=$1 i salida=""
  for (( i = 0; i < n; i++ )); do
    alto $SCK
    if pinctrl get "$MISO" | grep -q "| hi"; then salida+="1"; else salida+="0"; fi
    bajo $SCK
  done
  echo "$salida"
}

comando() {  # cmd bits
  alto $DC
  bajo $CS
  bajo $DC
  enviar "$1"
  alto $DC
  printf "0x%02X: " "$1"
  leer "$2"
  alto $CS
}

pinctrl set $MISO ip pd
alto $CS; bajo $SCK; bajo $MOSI; alto $DC

bajo $RST; sleep 0.1; alto $RST; sleep 0.15   # reset

comando 0x04 40    # ID del panel
comando 0xD3 40    # ID del controlador
