#include "actuadores.h"
#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/clocks.h"

/*
 Motor: PWM fijo a 20 kHz, por encima de lo audible para que no chille.
   f = f_sys / (div * (wrap + 1)) = 125 MHz / (6.25 * 1000) = 20 kHz
 Buzzer: se cambia el wrap en cada orden para fijar la frecuencia.
   wrap = f_sys / (div * f) - 1, con div = 64
   220 Hz -> 8876, 5000 Hz -> 389, 100 Hz -> 19530 (siempre cabe en 16 bits)
*/
#define MOTOR_DIV    6.25f
#define MOTOR_WRAP   999u
#define MOTOR_DUTY   (MOTOR_WRAP * 8u / 10u)   // 80 %
#define BUZ_DIV      64.0f

// volatile: las escribe la alarma (interrupción) y las lee el lazo principal
static volatile alarm_id_t s_alarma_motor  = 0;
static volatile alarm_id_t s_alarma_buzzer = 0;

static int64_t apagar_motor(alarm_id_t id, void *u) {
    (void)id; (void)u;
    pwm_set_gpio_level(PIN_MOTOR, 0);
    s_alarma_motor = 0; // Se limpia al terminar
    return 0;           
}

static int64_t apagar_buzzer(alarm_id_t id, void *u) {
    (void)id; (void)u;
    pwm_set_gpio_level(PIN_BUZZER, 0);
    s_alarma_buzzer = 0; // Se limpia al terminar
    return 0;
}
void actuadores_init(void) {
    // Motor
    gpio_set_function(PIN_MOTOR, GPIO_FUNC_PWM);
    uint s = pwm_gpio_to_slice_num(PIN_MOTOR);
    pwm_set_clkdiv(s, MOTOR_DIV);
    pwm_set_wrap(s, MOTOR_WRAP);
    pwm_set_gpio_level(PIN_MOTOR, 0);
    pwm_set_enabled(s, true);

    // Buzzer (el wrap se ajusta en cada orden)
    gpio_set_function(PIN_BUZZER, GPIO_FUNC_PWM);
    s = pwm_gpio_to_slice_num(PIN_BUZZER);
    pwm_set_clkdiv(s, BUZ_DIV);
    pwm_set_gpio_level(PIN_BUZZER, 0);
    pwm_set_enabled(s, true);

    // LEDs
    gpio_init(PIN_LED1); gpio_set_dir(PIN_LED1, GPIO_OUT); gpio_put(PIN_LED1, 0);
    gpio_init(PIN_LED2); gpio_set_dir(PIN_LED2, GPIO_OUT); gpio_put(PIN_LED2, 0);
}

bool actuadores_vib(uint16_t ms) {
    if (ms == 0 || ms > ACT_MS_MAX) return false;
    
    // Solo cancelamos si la alarma REALMENTE está activa en este momento
    if (s_alarma_motor > 0) {
        cancel_alarm(s_alarma_motor);
        s_alarma_motor = 0;
    }
    
    pwm_set_gpio_level(PIN_MOTOR, MOTOR_DUTY);
    s_alarma_motor = add_alarm_in_ms(ms, apagar_motor, NULL, true);
    return true;
}

bool actuadores_buz(uint16_t hz, uint16_t ms) {
    if (hz < ACT_HZ_MIN || hz > ACT_HZ_MAX || ms == 0 || ms > ACT_MS_MAX) return false;
    
    uint s = pwm_gpio_to_slice_num(PIN_BUZZER);
    
    // Optimización: clock_get_hz devuelve un entero, evitamos dobles castings flotantes recurrentes
    uint32_t f_sys = clock_get_hz(clk_sys);
    uint16_t wrap = (uint16_t)((float)f_sys / (BUZ_DIV * (float)hz)) - 1u;
    
    // Solo cancelamos si está activa
    if (s_alarma_buzzer > 0) {
        cancel_alarm(s_alarma_buzzer);
        s_alarma_buzzer = 0;
    }
    
    pwm_set_wrap(s, wrap);
    pwm_set_gpio_level(PIN_BUZZER, wrap / 2u); // 50% Duty Cycle exacto
    
    s_alarma_buzzer = add_alarm_in_ms(ms, apagar_buzzer, NULL, true);
    return true;
}

bool actuadores_led(uint8_t id, bool encendido) {
    if (id != 1 && id != 2) return false;
    gpio_put(id == 1 ? PIN_LED1 : PIN_LED2, encendido);
    return true;
}
