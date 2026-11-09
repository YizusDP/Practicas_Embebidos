#ifndef CONTROLS_REPORT_H
#define CONTROLS_REPORT_H

#include <stdint.h>

/*
Imagen única del estado de los controles en SRAM.

 - axis[0..3] la escribe el DMA del ADC (anillo de 8 bytes, round-robin ch0..ch3)
    axis[0] = GPIO26 -> X  (joystick)
    axis[1] = GPIO27 -> Y  (joystick)
    axis[2] = GPIO28 -> Z  (potenciómetro de volante / paddle)
    axis[3] = ADC3   -> VSYS/3. Se usa para completar el anillo
 - buttons la escribe el DMA del PIO (10 bits útiles)
 
 */
typedef struct {
    uint16_t axis[4];
    uint16_t buttons;
} controls_report_t;

#define CONTROLS_ADC_CHANNELS   4    //potencia de 2 -> anillo de DMA de 8 bytes 
#define CONTROLS_NUM_BUTTONS    10
#define CONTROLS_BUTTON_MASK    0x03FFu
#define CONTROLS_REPORT_SIZE    10   //bytes que viajan por USB

//Configuración para mis resistencias pulldown
#define CONTROLS_BUTTONS_ACTIVE_LOW  0


_Static_assert(sizeof(controls_report_t) == CONTROLS_REPORT_SIZE, "controls_report_t debe medir 10 bytes");


#endif /* CONTROLS_REPORT_H */
