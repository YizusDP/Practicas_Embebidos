#include <stdio.h>
#include "pico/stdlib.h"

#define PIN_DATA_Q7  16   
#define PIN_LD_PL    17   
#define PIN_CLK      18   

int main() {
    stdio_init_all();
    sleep_ms(2000);

    gpio_init(PIN_LD_PL);
    gpio_set_dir(PIN_LD_PL, GPIO_OUT);
    gpio_init(PIN_CLK);
    gpio_set_dir(PIN_CLK, GPIO_OUT);
    gpio_init(PIN_DATA_Q7);
    gpio_set_dir(PIN_DATA_Q7, GPIO_IN);

    gpio_put(PIN_CLK, 0);
    gpio_put(PIN_LD_PL, 1);

    while (true) {
        gpio_put(PIN_LD_PL, 0);
        sleep_ms(1000);
        gpio_put(PIN_LD_PL, 1);
        sleep_ms(1000);

        uint8_t registro = 0;

        for (int i = 0; i < 8; i++) {
            uint8_t bit = gpio_get(PIN_DATA_Q7) ? 1 : 0;
            registro = (registro << 1) | bit;

            if (i < 7) {
                gpio_put(PIN_CLK, 1);
                sleep_us(1);
                gpio_put(PIN_CLK, 0);
                sleep_us(1);
            }
        }

        printf("Hex: 0x%02X\n", registro);
        sleep_ms(1000);
    }

    return 0;
}