#include <gpiod.h>
#include <stdio.h>
#include <signal.h>
#include <time.h>

#define CHIP "/dev/gpiochip0"
#define ROJO      17
#define AMARILLO  27
#define VERDE     22
#define CRUCE     23
#define BOTON      5

#define T_VERDE     5000
#define T_AMARILLO  2000
#define T_ROJO      5000
#define T_PEATONAL  8000
#define T_PARPADEO   500

/* Decisión de diseño: se usan EVENTOS, no polling.
   El semáforo debe llevar el tiempo de cada fase y parpadear el LED de cruce
   mientras espera, así que no puede quedarse ciego en un sleep() ni quemar un
   núcleo en un bucle de lectura. wait_edge_events() bloquea el proceso con un
   temporizador: el planificador no le da CPU hasta que expira el plazo o el
   kernel detecta un flanco real en GPIO5. Costo en reposo: 0%. */

static volatile sig_atomic_t seguir = 1;

static void parar(int sig) { (void)sig; seguir = 0; }

static int64_t ahora_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

/* Espera `ms` completos. Si llega un flanco antes, levanta *peticion y sigue
   esperando el tiempo restante: la fase en curso nunca se acorta. */
static void esperar(struct gpiod_line_request *req,
                    struct gpiod_edge_event_buffer *buf,
                    int ms, int *peticion)
{
    int64_t fin = ahora_ms() + ms;
    int64_t restante;

    while (seguir && (restante = fin - ahora_ms()) > 0) {
        int r = gpiod_line_request_wait_edge_events(req, restante * 1000000);
        if (r > 0) {
            gpiod_line_request_read_edge_events(req, buf, 8);
            *peticion = 1;
        } else if (r < 0) {
            break;
        }
    }
}

static void luz(struct gpiod_line_request *req, unsigned int pin, int on) {
    gpiod_line_request_set_value(req, pin,
        on ? GPIOD_LINE_VALUE_ACTIVE : GPIOD_LINE_VALUE_INACTIVE);
}

int main(void) {
    static const unsigned int salidas[4] = {ROJO, AMARILLO, VERDE, CRUCE};
    static const unsigned int entradas[1] = {BOTON};

    signal(SIGINT, parar);

    struct gpiod_chip *chip = gpiod_chip_open(CHIP);
    if (!chip) { perror("gpiod_chip_open"); return 1; }

    struct gpiod_line_settings *cfg_out = gpiod_line_settings_new();
    gpiod_line_settings_set_direction(cfg_out, GPIOD_LINE_DIRECTION_OUTPUT);
    gpiod_line_settings_set_output_value(cfg_out, GPIOD_LINE_VALUE_INACTIVE);

    struct gpiod_line_settings *cfg_in = gpiod_line_settings_new();
    gpiod_line_settings_set_direction(cfg_in, GPIOD_LINE_DIRECTION_INPUT);
    gpiod_line_settings_set_edge_detection(cfg_in, GPIOD_LINE_EDGE_RISING);
    gpiod_line_settings_set_debounce_period_us(cfg_in, 20000);

    struct gpiod_line_config *lineas = gpiod_line_config_new();
    gpiod_line_config_add_line_settings(lineas, salidas, 4, cfg_out);
    gpiod_line_config_add_line_settings(lineas, entradas, 1, cfg_in);

    struct gpiod_request_config *cfg_pet = gpiod_request_config_new();
    gpiod_request_config_set_consumer(cfg_pet, "semaforo");

    struct gpiod_line_request *req =
        gpiod_chip_request_lines(chip, cfg_pet, lineas);
    if (!req) { perror("gpiod_chip_request_lines"); return 1; }

    struct gpiod_edge_event_buffer *buf = gpiod_edge_event_buffer_new(8);
    if (!buf) { perror("gpiod_edge_event_buffer_new"); return 1; }

    int peticion = 0;

    while (seguir) {
        luz(req, VERDE, 1); luz(req, AMARILLO, 0); luz(req, ROJO, 0);
        esperar(req, buf, T_VERDE, &peticion);
        if (!seguir) break;

        luz(req, VERDE, 0); luz(req, AMARILLO, 1);
        esperar(req, buf, T_AMARILLO, &peticion);
        if (!seguir) break;

        luz(req, AMARILLO, 0); luz(req, ROJO, 1);

        int cruce = peticion;
        peticion = 0;

        if (cruce) {
            int ciclos = T_PEATONAL / T_PARPADEO;
            for (int i = 0; i < ciclos && seguir; i++) {
                luz(req, CRUCE, i % 2 == 0);
                esperar(req, buf, T_PARPADEO, &peticion);
            }
            luz(req, CRUCE, 0);
        } else {
            esperar(req, buf, T_ROJO, &peticion);
        }
    }

    for (int i = 0; i < 4; i++) luz(req, salidas[i], 0);

    gpiod_edge_event_buffer_free(buf);
    gpiod_line_request_release(req);
    gpiod_request_config_free(cfg_pet);
    gpiod_line_config_free(lineas);
    gpiod_line_settings_free(cfg_in);
    gpiod_line_settings_free(cfg_out);
    gpiod_chip_close(chip);
    return 0;
}
