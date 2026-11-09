#ifndef READ_74HC165_H
#define READ_74HC165_H

#include <stdint.h>
#include <stdbool.h>
#include "hardware/pio.h"

#define PIN_DATA_Q7  16
#define PIN_LD_PL    17
#define PIN_CLK      18

//Bits por trama (autopush del PIO). Una palabra de la RX FIFO = una trama completa. 
#define BTN_FRAME_BITS   10

//Transferencias por bloque de cada canal DMA del ping-pong (ver .c).
#define BTN_DMA_BLOCK    256

//Divisor del reloj del state machine
#define BTN_SM_CLKDIV    125.0f

//Función que establece el comportamiento del encadenamiento de los dma para este módulo. Ver .c para más información
static void dma_pair_setup(PIO pio, uint sm, volatile uint16_t *dst);

/*
Configura la state machine del 74HC165 y la cadena DMA que copia cada trama
(RX FIFO del PIO) directamente a *dst, sin intervención de la CPU.
dst debe apuntar a un uint16_t (en nuetro caso a &g_controls.buttons).
*/
void read_74hc165_init(PIO pio, volatile uint16_t *dst);

//Función para avisar a la cpu que los dma siguen avanzando.
bool read_74hc165_is_alive(void);


#endif