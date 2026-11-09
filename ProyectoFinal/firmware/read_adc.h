#ifndef READ_ADC_H
#define READ_ADC_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

//GPIO26..28 = ADC0..2 (X, Y, Z). El canal 3 (VSYS/3) se muestrea solo para completar el anillo y hacer sentido en el tamaño del anillo. (8 bytes potencia de 2)
#define ADC_FIRST_GPIO            26
#define ADC_NUM_POTS              3

//Tasa de muestreo POR CANAL. Con 4 canales el ADC trabaja a 4x esta cifra. 
#define ADC_RATE_PER_CHANNEL_HZ   4000
#define ADC_CLK_HZ                48000000.0f

//Transferencias por bloque de cada canal DMA del ping-pong (múltiplo de 4). 
#define ADC_DMA_BLOCK             4096

/*
 * Configura el ADC en round-robin (ch0..ch3) y la cadena DMA que escribe las
 * muestras en un anillo de 8 bytes en `ring4` (4 x uint16_t, alineado a 8 bytes).
 * Cada muestra es de 12 bits (0..4095).
 */
void read_adc_init(volatile uint16_t *ring4);

//true si la cadena ADC->DMA ha avanzado desde la última llamada (para el watchdog). Avisamos al watch dog
bool read_adc_is_alive(void);

#ifdef __cplusplus
}
#endif

#endif /* READ_ADC_H */