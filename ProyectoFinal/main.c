#include <stdio.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "read_74hc165.pio.h"

#define PIN_DATA_Q7  16   
#define PIN_LD_PL    17   
#define PIN_CLK      18   

void pio_74hc165_debug_init(PIO pio, uint32_t sm, uint32_t offset) {
    pio_sm_config c = read_74hc165_program_get_default_config(offset);

    // Configuración de pines para las instrucciones SET (GPIO 17 = LD, GPIO 18 = CLK)
    sm_config_set_set_pins(&c, PIN_LD_PL, 2);
    // Mapeo de pin para las instrucciones IN (GPIO 16 = Q7). Estas instrucciones se ingresan al ISR del PIO y se empujan al FIFO.
    sm_config_set_in_pins(&c, PIN_DATA_Q7);
    //Se inicializan los pines GPIO para el PIO
    pio_gpio_init(pio, PIN_LD_PL); 
    pio_gpio_init(pio, PIN_CLK);
    pio_gpio_init(pio, PIN_DATA_Q7);

    //Se establecen las direcciones de los pines: LD y CLK como salida, Q7 como entrada
    pio_sm_set_consecutive_pindirs(pio, sm, PIN_LD_PL, 2, true);
    pio_sm_set_consecutive_pindirs(pio, sm, PIN_DATA_Q7, 1, false);

    // IN_SHIFT: lsb_first = false (desplazamiento a la izquierda), autopush = FALSE, threshold = 32
    sm_config_set_in_shift(&c, false, false, 32);

    // Divisor de reloj cerca del máximo para reducir velocidad del estado PIO
    // A 125 MHz con div=65535, cada ciclo de instrucción PIO toma ~0.52 ms.
    // Con las demoras [31], los flancos tomarán aproximadamente 1 segundo. De momento se usa esta frecuencia para depuración bit a bit.
    sm_config_set_clkdiv(&c, 1000.0f);

    //Se inicializa el estado de la máquina de estado PIO con la configuración y se habilita su ejecución
    pio_sm_init(pio, sm, offset, &c);
    pio_sm_set_enabled(pio, sm, true);
}

int main() {
    stdio_init_all();
    
    
    sleep_ms(3000);
    printf("\nIniciando Depuración Bit a Bit 74HC165 (1 Hz)\n\n");

    PIO pio = pio0;
    uint32_t offset = pio_add_program(pio, &read_74hc165_program);
    uint32_t sm = pio_claim_unused_sm(pio, true);

    pio_74hc165_debug_init(pio, sm, offset);

    const char nombres_bits[10][5] = {"H1", "G1", "F1", "E1", "D1", "C1", "B1", "A1", "H2", "G2"};

    while (true) {
        printf("Nueva Captura (Parallel Load):\n");
        uint16_t registro_completo = 0;

        for (int i = 0; i <10; i++) {
            // Espera bloqueante hasta que el PIO haga 'push block' de 1 bit
            uint32_t bit_raw = pio_sm_get_blocking(pio, sm);
            uint8_t valor_bit = (uint8_t)(bit_raw & 0x01);

            // Reconstruimos el Byte (MSB a LSB: H es el bit 7, A es el bit 0)
            registro_completo = (registro_completo << 1) | valor_bit;

            //printf("Bit %s: %d\n", nombres_bits[i], valor_bit);
        }

        printf("--> Resultado acumulado en Hex: 0x%03X\n\n", registro_completo);
    }

    return 0;
}

