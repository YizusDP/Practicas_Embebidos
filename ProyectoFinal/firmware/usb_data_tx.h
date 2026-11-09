#ifndef USB_DATA_TX_H
#define USB_DATA_TX_H

#include "controls_report.h"

//Inicializa TinyUSB (dispositivo HID). src es el tda de los controles
void usb_data_tx_init(const volatile controls_report_t *src);

//Llamar en el lazo principal del core 0: atiende USB y rearma el endpoint.
void usb_data_tx_task(void);


#endif 