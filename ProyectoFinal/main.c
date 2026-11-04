#include <stdio.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "read_74hc165.pio.h"

#define PIN_DATA_Q7  16   
#define PIN_LD_PL    17   
#define PIN_CLK      18   

// Mantenemos EXACTAMENTE la configuración original de la SM sin alterar nada
void pio_74hc165_debug_init(PIO pio, uint32_t sm, uint32_t offset) {
    pio_sm_config c = read_74hc165_program_get_default_config(offset);

    // Configuración de pines para las instrucciones SET (GPIO 17 = LD, GPIO 18 = CLK)
    sm_config_set_set_pins(&c, PIN_LD_PL, 2);
    // Mapeo de pin para las instrucciones IN (GPIO 16 = Q7). Estas instrucciones se ingresan al ISR del PIO y se empujan al FIFO.
    sm_config_set_in_pins(&c, PIN_DATA_Q7);
    // Se inicializan los pines GPIO para el PIO
    pio_gpio_init(pio, PIN_LD_PL); 
    pio_gpio_init(pio, PIN_CLK);
    pio_gpio_init(pio, PIN_DATA_Q7);

    // Se establecen las direcciones de los pines: LD y CLK como salida, Q7 como entrada
    pio_sm_set_consecutive_pindirs(pio, sm, PIN_LD_PL, 2, true);
    pio_sm_set_consecutive_pindirs(pio, sm, PIN_DATA_Q7, 1, false);

    // IN_SHIFT original: lsb_first = false, autopush = FALSE, threshold = 32
    sm_config_set_in_shift(&c, false, false, 32);

    // Frecuencia original de depuración (div = 1000.0f)
    sm_config_set_clkdiv(&c, 125.0f);

    // Se inicializa el estado de la máquina de estado PIO con la configuración y se habilita su ejecución
    pio_sm_init(pio, sm, offset, &c);
    pio_sm_set_enabled(pio, sm, true);
}

int main() {
    stdio_init_all();
    
    sleep_ms(3000);
    printf("\nIniciando Depuración 74HC165 con DMA (Frecuencia Original)\n\n");

    PIO pio = pio0;
    uint32_t offset = pio_add_program(pio, &read_74hc165_program);
    uint32_t sm = pio_claim_unused_sm(pio, true);

    // Llamamos a la función original sin modificar un solo parámetro de la SM
    pio_74hc165_debug_init(pio, sm, offset);

    // Arreglo en SRAM para recibir los 10 bits que la PIO empuja de forma individual
    uint32_t dma_buffer[10];
    
    // Reclamar y configurar el canal DMA
    int dma_chan = dma_claim_unused_channel(true);
    dma_channel_config c = dma_channel_get_default_config(dma_chan);

    channel_config_set_transfer_data_size(&c, DMA_SIZE_32);
    channel_config_set_read_increment(&c, false);   // Leer siempre de la misma dirección de la FIFO RX del PIO
    channel_config_set_write_increment(&c, true);   // Escribir incrementando en el arreglo dma_buffer de la SRAM
    channel_config_set_dreq(&c, pio_get_dreq(pio, sm, false)); // Sincronizado con las peticiones de la FIFO RX

    while (true) {
        printf("Nueva Captura (Parallel Load):\n");

        // Configuramos y disparamamos el DMA para que capture exactamente 10 elementos (los 10 bits de la trama)
        dma_channel_configure(
            dma_chan,
            &c,
            dma_buffer,          // Destino en SRAM
            &pio->rxf[sm],       // Origen: FIFO RX del PIO
            10,                  // Conteo de transferencias: 10 bits
            true                 // Iniciar inmediatamente
        );

        // El CPU espera a que el canal DMA termine de recolectar los 10 bits de manera autónoma
        dma_channel_wait_for_finish_blocking(dma_chan);

        uint16_t registro_completo = 0;

        // La parte de la CPU: extracción y reconstrucción limpia desde la SRAM
        for (int i = 0; i < 10; i++) {
            uint8_t valor_bit = (uint8_t)(dma_buffer[i] & 0x01);
            registro_completo = (registro_completo << 1) | valor_bit;
        }

        printf("--> Resultado acumulado en Hex: 0x%03X\n\n", registro_completo);
    }

    return 0;
}
