#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/time.h"
#include "hardware/watchdog.h"

#include "controls_report.h"
#include "read_74hc165.h"
#include "read_adc.h"
#include "usb_data_tx.h"
#include "hardware/sync.h"
#include "actuadores.h"






//CONFIGURACIÓN DEL WACTHDOG
#define WDT_TIMEOUT_MS     250// reinicio si nadie alimenta el watchdog en este tiempo
#define HEALTH_PERIOD_US   25000 // cada cuánto se revisa que los DMA avanzan
#define HEALTH_MAX_BAD     4 // revisiones malas seguidas (~100 ms o 4 veces HELTH_PERIOD_US) antes de dejar de alimentar

//Declaración del TDA para almacenamiento de los controles
static volatile controls_report_t g_controls __attribute__((aligned(8)));

//Esta función despierta al core 0 cada 1ms para que el lazo siga alimentando al watchdog aunque la usb no genere eventeos.
static bool wake_cb(repeating_timer_t *t) {
    (void)t;
    return true;
}

int main(void) {
    stdio_init_all();   // UART (stdio USB debe estar DESHABILITADO: el USB es del HID)

    if (watchdog_enable_caused_reboot()) {
        printf("[WDT] el ultimo reinicio fue causado por el watchdog\n");
    }

    //Adquisición autónoma: a partir de aquí los DMA mantienen g_controls al día
    read_74hc165_init(pio0, &g_controls.buttons); //Iniciando módulo de adquisición de botones digitales
    read_adc_init(g_controls.axis);//iniciando adquisición de controles analógicos

    actuadores_init();


    //Iniciamos el módulo de envío de datos usb.
    usb_data_tx_init(&g_controls);

    //Añadimos un despertador de 1ms
    static repeating_timer_t wake_timer;
    add_repeating_timer_us(-1000, wake_cb, NULL, &wake_timer);

    //Watchdog al final, cuando todo ya está en marcha. Se pausa con el depurador conectado.
    watchdog_enable(WDT_TIMEOUT_MS, true);

    uint32_t t_health = time_us_32();
    unsigned bad = 0;



    //Ciclo principal
    while (true) {
        usb_data_tx_task();// Atiende los eventos del usb pendientes y rearma el endpoint

        uint32_t now = time_us_32();
        if ((uint32_t)(now - t_health) >= HEALTH_PERIOD_US) {
            t_health = now;
            // Verificamos que todo se encuentre funcionando. Ambas módulos deben reportar su estado.
            bool ok = read_74hc165_is_alive() & read_adc_is_alive();
            
            bad = ok ? 0 : bad + 1; //Si ok es 0, bad incrementa en 1
        }
        // Solo se alimenta si el lazo sigue vivo Y los DMA avanzan.
        //OJO, no alimentar desde una interrupción porque taparía un lazo "colgado"
        if (bad < HEALTH_MAX_BAD) {
            watchdog_update();
        }
        __wfi();    // dormir hasta la siguiente interrupción (USB o el despertador de 1 ms)
    }
}