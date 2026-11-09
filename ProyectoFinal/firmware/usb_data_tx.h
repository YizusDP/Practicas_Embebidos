#ifndef USB_DATA_TX_H
#define USB_DATA_TX_H

#include <stdbool.h>
#include <stdint.h>
#include "controls_report.h"

/* Telemetría Pi -> Pico: reporte de salida HID de 8 bytes, enteros little-endian.
 * (mismo formato que arma pi/puente_hid.py)
 *   byte 0 = comando
 *   1 VIB : bytes 1-2 = ms
 *   2 BUZ : bytes 1-2 = Hz, bytes 3-4 = ms
 *   3 LED : byte 1 = id (1 o 2), byte 2 = estado (0 o 1)                      */
#define TELEMETRY_REPORT_SIZE  8
#define TELEMETRY_NUM_LEDS     2

typedef enum {
    TELEMETRY_CMD_VIB = 1,
    TELEMETRY_CMD_BUZ = 2,
    TELEMETRY_CMD_LED = 3,
} telemetry_cmd_type_t;

typedef struct {
    uint8_t  type;    // telemetry_cmd_type_t
    uint16_t ms;      // VIB y BUZ: duración en ms
    uint16_t hz;      // BUZ: frecuencia
    uint8_t  led_id;  // LED: 1 o 2
    uint8_t  led_on;  // LED: 0 apagar, 1 encender
} telemetry_cmd_t;

//Inicializa TinyUSB (dispositivo HID). src es el tda de los controles
void usb_data_tx_init(const volatile controls_report_t *src);

//Llamar en el lazo principal del core 0: atiende USB y rearma el endpoint.
void usb_data_tx_task(void);

//Saca el siguiente comando de telemetría recibido. false si no hay ninguno pendiente.
//Llamar en el lazo principal (mismo core que usb_data_tx_task) hasta que regrese false.
bool usb_data_tx_get_command(telemetry_cmd_t *out);


#endif 