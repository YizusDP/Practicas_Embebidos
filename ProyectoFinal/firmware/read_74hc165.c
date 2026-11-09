#include "read_74hc165.h"
#include "read_74hc165.pio.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "controls_report.h"

static int s_dma_a = -1;
static int s_dma_b = -1;

//CONFIGURACIÓN DE LA MÁQUINA DE ESTADOS
static uint sm_setup(PIO pio) {
    uint offset = pio_add_program(pio, &read_74hc165_program);
    uint sm = (uint)pio_claim_unused_sm(pio, true);

    pio_sm_config c = read_74hc165_program_get_default_config(offset);

    // SET: GPIO17 = LD, GPIO18 = CLK
    sm_config_set_set_pins(&c, PIN_LD_PL, 2);
    // IN: GPIO16 = Q7
    sm_config_set_in_pins(&c, PIN_DATA_Q7);

    pio_gpio_init(pio, PIN_LD_PL);
    pio_gpio_init(pio, PIN_CLK);
    pio_gpio_init(pio, PIN_DATA_Q7);

    pio_sm_set_consecutive_pindirs(pio, sm, PIN_LD_PL, 2, true);   // LD, CLK salidas
    pio_sm_set_consecutive_pindirs(pio, sm, PIN_DATA_Q7, 1, false); // Q7 entrada

    // Shift izquierda, AUTOPUSH al completar BTN_FRAME_BITS bits:
    // cada trama queda como UNA palabra en la RX FIFO, con los 10 bits en los bits bajos.
    sm_config_set_in_shift(&c, false, true, BTN_FRAME_BITS);

    sm_config_set_clkdiv(&c, BTN_SM_CLKDIV);//Ajustación frecuencia de máqina de estados
    

    pio_sm_init(pio, sm, offset, &c);
    return sm;                           // se habilita DESPUÉS de armar el DMA
}

/* DMA: dos canales encadenados A -> B -> A 
Origen y destino son fijos (no se incrementan), así que no hay nada 
que reconfigurar: cada canal, al terminar su bloque, dispara al     
otro por hardware y su contador se recarga solo. Un único canal con 
una cuenta enorme se acabaría en días; esto corre indefinidamente.
Esta es un nueva entrada para bitácora de diseño (Actualizar bitácora)*/

static void dma_pair_setup(PIO pio, uint sm, volatile uint16_t *dst) {
    s_dma_a = dma_claim_unused_channel(true);
    s_dma_b = dma_claim_unused_channel(true);

    for (int i = 0; i < 2; i++) {
        int self  = i ? s_dma_b : s_dma_a;
        int other = i ? s_dma_a : s_dma_b;

        dma_channel_config c = dma_channel_get_default_config(self);
        channel_config_set_transfer_data_size(&c, DMA_SIZE_16);
        channel_config_set_read_increment(&c, false);
        channel_config_set_write_increment(&c, false);
        channel_config_set_dreq(&c, pio_get_dreq(pio, sm, false));  // RX FIFO
        channel_config_set_chain_to(&c, other);

        dma_channel_configure(self, &c,
                              (void *)dst,        // destino: g_controls.buttons
                              &pio->rxf[sm],      // origen: RX FIFO
                              BTN_DMA_BLOCK,
                              false);             // sin disparo todavía
    }
    dma_channel_start(s_dma_a);
}


void read_74hc165_init(PIO pio, volatile uint16_t *dst) {
    uint sm = sm_setup(pio);
    dma_pair_setup(pio, sm, dst);
    pio_sm_set_enabled(pio, sm, true);
}


bool read_74hc165_is_alive(void) {
    static uint32_t last_a = 0, last_b = 0;
    uint32_t a = dma_channel_hw_addr(s_dma_a)->transfer_count;
    uint32_t b = dma_channel_hw_addr(s_dma_b)->transfer_count;
    bool alive = (a != last_a) || (b != last_b);
    last_a = a;
    last_b = b;
    return alive;
}