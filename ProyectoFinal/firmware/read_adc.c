#include "read_adc.h"
#include "controls_report.h"
#include "hardware/adc.h"
#include "hardware/dma.h"

static int s_dma_a = -1;
static int s_dma_b = -1;


static void dma_pair_setup(volatile uint16_t *ring4) {
    s_dma_a = dma_claim_unused_channel(true);
    s_dma_b = dma_claim_unused_channel(true);

    for (int i = 0; i < 2; i++) {
        int self  = i ? s_dma_b : s_dma_a;
        int other = i ? s_dma_a : s_dma_b;

        dma_channel_config c = dma_channel_get_default_config(self);
        channel_config_set_transfer_data_size(&c, DMA_SIZE_16);
        channel_config_set_read_increment(&c, false);       // siempre la FIFO del ADC
        channel_config_set_write_increment(&c, true);
        channel_config_set_ring(&c, true, 3);               // anillo de escritura: 2^3 = 8 bytes
        channel_config_set_dreq(&c, DREQ_ADC);
        channel_config_set_chain_to(&c, other);

        dma_channel_configure(self, &c,
                              (void *)ring4,
                              &adc_hw->fifo,
                              ADC_DMA_BLOCK,
                              false);
    }
    dma_channel_start(s_dma_a);
}

void read_adc_init(volatile uint16_t *ring4) {
    // El anillo de DMA exige alineación a su tamaño (8 bytes).
    hard_assert(((uintptr_t)ring4 & 0x7u) == 0);

    adc_init();
    adc_gpio_init(ADC_FIRST_GPIO + 0);
    adc_gpio_init(ADC_FIRST_GPIO + 1);
    adc_gpio_init(ADC_FIRST_GPIO + 2);
    // GPIO29 (ADC3 = VSYS/3 en la Pico) no se toca: solo se muestrea.

    adc_run(false);
    adc_set_round_robin(0x0F);// ch0, ch1, ch2, ch3
    adc_select_input(0);// el round-robin arranca en ch0
    // FIFO habilitada, DREQ habilitado, umbral 1, sin bit de error, sin shift (12 bits completos)
    adc_fifo_setup(true, true, 1, false, false);
    adc_fifo_drain();

    // Periodo de conversión = 1 + div ciclos de 48 MHz
    float div = ADC_CLK_HZ / (float)(ADC_RATE_PER_CHANNEL_HZ * CONTROLS_ADC_CHANNELS) - 1.0f;
    adc_set_clkdiv(div);

    dma_pair_setup(ring4);// primero el DMA...
    adc_run(true);// ...y luego el ADC (la 1 ra muestra cae en ring4[0])
}

bool read_adc_is_alive(void) {
    static uint32_t last_a = 0, last_b = 0;
    uint32_t a = dma_channel_hw_addr(s_dma_a)->transfer_count;
    uint32_t b = dma_channel_hw_addr(s_dma_b)->transfer_count;
    bool alive = (a != last_a) || (b != last_b);
    last_a = a;
    last_b = b;
    return alive;
}