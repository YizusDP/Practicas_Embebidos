#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/adc.h"
#include "hardware/dma.h"
#include "hardware/clocks.h" 

#define ADC_PIN 26
#define CAPTURE_DEPTH 100

uint16_t adc_buffer[CAPTURE_DEPTH];
int dma_chan;

void setup_adc_dma() {

    clock_configure(clk_adc, 0, CLOCKS_CLK_ADC_CTRL_AUXSRC_VALUE_XOSC_CLKSRC, 12 * MHZ, 48 * KHZ);
    
    adc_init();
    adc_gpio_init(ADC_PIN);
    adc_select_input(0);

   
    adc_fifo_setup(
        true,    
        true,   
        1,       
        false,   
        false    
    );

  
    adc_set_clkdiv(47999.0f);

  
    dma_chan = dma_claim_unused_channel(true);
    dma_channel_config cfg = dma_channel_get_default_config(dma_chan);

    channel_config_set_transfer_data_size(&cfg, DMA_SIZE_16);
    channel_config_set_read_increment(&cfg, false); 
    channel_config_set_write_increment(&cfg, true);  
    channel_config_set_dreq(&cfg, DREQ_ADC);        

    dma_channel_configure(
        dma_chan,
        &cfg,
        adc_buffer,        
        &adc_hw->fifo,      
        CAPTURE_DEPTH,      
        false               
    );
}

int main() {
    stdio_init_all();
    sleep_ms(2000);

    setup_adc_dma();

    printf("Iniciando muestreo ADC por DMA a 1 Hz...\n");
    printf("El búfer se completará cada %d segundos.\n\n", CAPTURE_DEPTH);

    dma_channel_start(dma_chan);
    adc_run(true);

    while (true) {
        dma_channel_wait_for_finish_blocking(dma_chan);

   
        printf("¡Bloque completo recibido! (Pasaron %d segundos).\n", CAPTURE_DEPTH);
        printf("Muestra[0]: %u | Muestra[%d]: %u\n\n", adc_buffer[0], CAPTURE_DEPTH / 2, adc_buffer[CAPTURE_DEPTH / 2]);

      
        adc_run(false);
        adc_fifo_drain();


        dma_channel_set_write_addr(dma_chan, adc_buffer, false);
        dma_channel_set_trans_count(dma_chan, CAPTURE_DEPTH, true); 


        adc_run(true);
    }

    return 0;
}


