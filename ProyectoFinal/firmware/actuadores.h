#ifndef ACTUADORES_H
#define ACTUADORES_H

#include <stdint.h>
#include <stdbool.h>

/*
 Actuadores del control: motor de vibración, buzzer y 2 LEDs.
 Las órdenes llegan de la Pi como reportes de salida HID (ver usb_data_tx.c).
 Ninguna función bloquea: el apagado del motor y del buzzer lo hace una alarma.
*/

#define PIN_MOTOR    15   // PWM slice 7, canal B (con transistor NPN + diodo de rueda libre)
#define PIN_BUZZER   12   // PWM slice 6, canal A (otro slice: frecuencia propia)
#define PIN_LED1     10
#define PIN_LED2     11

// Límites que se aceptan en las órdenes (lo que llegue fuera de rango se ignora)
#define ACT_MS_MAX   5000
#define ACT_HZ_MIN   100
#define ACT_HZ_MAX   5000

void actuadores_init(void);
bool actuadores_vib(uint16_t ms);               // motor encendido 'ms' milisegundos
bool actuadores_buz(uint16_t hz, uint16_t ms);  // buzzer a 'hz' durante 'ms'
bool actuadores_led(uint8_t id, bool encendido); // id = 1 o 2

#endif
