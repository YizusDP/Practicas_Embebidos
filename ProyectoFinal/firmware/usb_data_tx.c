#include <string.h>
#include "tusb.h"
#include <stddef.h>
#include "pico/unique_id.h"
#include "hardware/dma.h"
#include "hardware/structs/usb.h"
#include "usb_data_tx.h"

static const volatile controls_report_t *s_src = NULL;

/* Snapshot de la imagen de controles 
 Copia con lecturas de 16 bits (una por campo) para que ningún eje salga partido
 si el DMA escribe justo durante la copia. Que un eje sea de una muestra y otro de
  la siguiente es inofensivo.
 */
static void controls_snapshot(controls_report_t *dst) {
    const volatile uint16_t *s = (const volatile uint16_t *)s_src;
    uint16_t *d = (uint16_t *)dst;
    for (unsigned i = 0; i < CONTROLS_REPORT_SIZE / 2; i++) {
        d[i] = s[i];
    }

    dst->buttons &= CONTROLS_BUTTON_MASK;
}


/* Descriptor de reporte HID (10 bytes, sin Report ID)              
  bytes 0-5 : X, Y, Z  (3 x 16 bits, 0..4095)                     
 bytes 6-7 : constante (ADC3 / VSYS, diagnóstico; el host lo omite)
  bytes 8-9 : 10 botones + 6 bits de relleno                        */

static const uint8_t desc_hid_report[] = {
    0x05, 0x01,         // Usage Page (Generic Desktop)
    0x09, 0x04,         // Usage (Joystick)
    0xA1, 0x01,         // Collection (Application)

    0x05, 0x01,         //   Usage Page (Generic Desktop)
    0x09, 0x30,         //   Usage (X)
    0x09, 0x31,         //   Usage (Y)
    0x09, 0x32,         //   Usage (Z)
    0x15, 0x00,         //   Logical Minimum (0)
    0x26, 0xFF, 0x0F,   //   Logical Maximum (4095)
    0x75, 0x10,         //   Report Size (16)
    0x95, 0x03,         //   Report Count (3)
    0x81, 0x02,         //   Input (Data, Var, Abs)

    0x75, 0x10,         //   Report Size (16)
    0x95, 0x01,         //   Report Count (1)
    0x81, 0x03,         //   Input (Const, Var, Abs)  -> relleno / diagnóstico

    0x05, 0x09,         //   Usage Page (Button)
    0x19, 0x01,         //   Usage Minimum (Button 1)
    0x29, 0x0A,         //   Usage Maximum (Button 10)
    0x15, 0x00,         //   Logical Minimum (0)
    0x25, 0x01,         //   Logical Maximum (1)
    0x75, 0x01,         //   Report Size (1)
    0x95, 0x0A,         //   Report Count (10)
    0x81, 0x02,         //   Input (Data, Var, Abs)

    0x75, 0x01,         //   Report Size (1)
    0x95, 0x06,         //   Report Count (6)
    0x81, 0x03,         //   Input (Const, Var, Abs)  -> relleno

    0xC0                // End Collection
};


//Descriptores de dispositivo / configuración / strings          

static const tusb_desc_device_t desc_device = {
    .bLength            = sizeof(tusb_desc_device_t),
    .bDescriptorType    = TUSB_DESC_DEVICE,
    .bcdUSB             = 0x0200,
    .bDeviceClass       = 0x00,
    .bDeviceSubClass    = 0x00,
    .bDeviceProtocol    = 0x00,
    .bMaxPacketSize0    = CFG_TUD_ENDPOINT0_SIZE,

    .idVendor           = 0xCafe,   // PLACEHOLDER de pruebas: cámbialo antes de distribuir
    .idProduct          = 0x4001,
    .bcdDevice          = 0x0100,

    .iManufacturer      = 0x01,
    .iProduct           = 0x02,
    .iSerialNumber      = 0x03,
    .bNumConfigurations = 0x01
};

enum { ITF_NUM_HID = 0, ITF_NUM_TOTAL };
#define EPNUM_HID_IN      0x81
#define CONFIG_TOTAL_LEN  (TUD_CONFIG_DESC_LEN + TUD_HID_DESC_LEN)

static const uint8_t desc_configuration[] = {
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, 0x00, 100),
    // Endpoint IN de interrupción con bInterval = 1 ms (máximo a Full Speed)
    TUD_HID_DESCRIPTOR(ITF_NUM_HID, 0, HID_ITF_PROTOCOL_NONE,
                       sizeof(desc_hid_report), EPNUM_HID_IN,
                       CFG_TUD_HID_EP_BUFSIZE, 1)
};

static const char *const string_desc_arr[] = {
    (const char[]){ 0x09, 0x04 }, //0: idioma (inglés EE. UU.)
    "Proyecto Arcade FI", // 1: fabricante
    "Arcade Controller Equipo Dinamita",// 2: producto
    NULL // 3: número de serie (se arma con el ID único de la Pico)
};
//Callbacks que TinyUSB exige 
const uint8_t *tud_descriptor_device_cb(void) {
    return (const uint8_t *)&desc_device;
}

const uint8_t *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return desc_configuration;
}

const uint8_t *tud_hid_descriptor_report_cb(uint8_t instance) {
    (void)instance;
    return desc_hid_report;
}

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t desc_str[32 + 1];
    char serial[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
    uint8_t chr_count;

    if (index == 0) {
        memcpy(&desc_str[1], string_desc_arr[0], 2);
        chr_count = 1;
    } else {
        const char *str;
        if (index == 3) {
            pico_get_unique_board_id_string(serial, sizeof(serial));
            str = serial;
        } else if (index < 3) {
            str = string_desc_arr[index];
        } else {
            return NULL;
        }
        chr_count = (uint8_t)strlen(str);
        if (chr_count > 31) chr_count = 31;
        for (uint8_t i = 0; i < chr_count; i++) {
            desc_str[1 + i] = str[i];
        }
    }
    desc_str[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * chr_count + 2));
    return desc_str;
}

//GET_REPORT por el endpoint de control (el host pide el reporte "a mano")
uint16_t tud_hid_get_report_cb(uint8_t instance, uint8_t report_id,
                               hid_report_type_t report_type,
                               uint8_t *buffer, uint16_t reqlen) {
    (void)instance;
    (void)report_id;
    if (report_type != HID_REPORT_TYPE_INPUT || s_src == NULL) return 0;

    controls_report_t snap;
    controls_snapshot(&snap);
    uint16_t n = reqlen < CONTROLS_REPORT_SIZE ? reqlen : CONTROLS_REPORT_SIZE;
    memcpy(buffer, &snap, n);
    return n;
}

//SET_REPORT / salida del host. Por acá llegará la telemetría
void tud_hid_set_report_cb(uint8_t instance, uint8_t report_id,
                           hid_report_type_t report_type,
                           const uint8_t *buffer, uint16_t bufsize) {
    (void)instance; (void)report_id; (void)report_type; (void)buffer; (void)bufsize;
}


//Esta sección define el propiamente las funciones del módulo!   

//Tercer canal DMA: SRAM (g_controls) -> DPSRAM (buffer del endpoint) 
#define DPSRAM_SIZE  4096u

static int s_dma_usb = -1;

/*
 * Dirección del buffer del endpoint IN dentro de la DPSRAM. TinyUSB la asigna al abrir el
 * endpoint (SET_CONFIGURATION) y la deja escrita en el registro de control del endpoint,
 * así que se lee de ahí en lugar de depender de estructuras internas de TinyUSB.
 * Devuelve NULL si el endpoint aún no está abierto o la dirección no es creíble; en ese
 * caso simplemente no se hace el refresco por DMA y el reporte sale con la copia de TinyUSB.
 */
static volatile uint16_t *epin_dpram_buffer(void) {
    uint32_t ctrl = usb_dpram->ep_ctrl[(EPNUM_HID_IN & 0x7F) - 1].in;
    uint32_t off  = ctrl & 0xFFC0u;     // dirección relativa a la DPSRAM, alineada a 64 bytes

    if (off < offsetof(usb_device_dpram_t, epx_data) ||
        off + CONTROLS_REPORT_SIZE > DPSRAM_SIZE) {
        return NULL;
    }
    return (volatile uint16_t *)((uint8_t *)usb_dpram + off);
}

static void dma_usb_init(void) {
    s_dma_usb = dma_claim_unused_channel(true);
    dma_channel_config c = dma_channel_get_default_config(s_dma_usb);
    channel_config_set_transfer_data_size(&c, DMA_SIZE_16);   // un campo (16 bits) por transferencia
    channel_config_set_read_increment(&c, true);
    channel_config_set_write_increment(&c, true);
    // Sin DREQ: copia a máxima velocidad (son 5 transferencias)
    dma_channel_set_config(s_dma_usb, &c, false);
}

// La CPU solo da la orden; la copia SRAM -> DPSRAM la ejecuta el DMA.
static void dma_usb_refresh(void) {
    volatile uint16_t *dst = epin_dpram_buffer();
    if (dst == NULL) return;

    dma_channel_set_read_addr(s_dma_usb, (const void *)s_src, false);
    dma_channel_set_write_addr(s_dma_usb, (void *)dst, false);
    dma_channel_set_trans_count(s_dma_usb, CONTROLS_REPORT_SIZE / 2, true); // dispara
    dma_channel_wait_for_finish_blocking(s_dma_usb); // ~100 ns
}

void usb_data_tx_init(const volatile controls_report_t *src) {
    s_src = src;
    dma_usb_init();
    tusb_init();
}

void usb_data_tx_task(void) {
    tud_task();     // atiende los eventos USB pendientes (p. ej. "el host ya leyó el reporte")

    // tud_hid_ready() == true cuando el host ya recogió el reporte anterior.
    if (s_src != NULL && tud_hid_ready()) {
        // 1) TinyUSB arma el endpoint (longitud, PID DATA0/DATA1, bit AVAILABLE). Lo hace
        //    copiando un snapshot válido, así que si el paso 2 se omite el reporte sigue bien.
        controls_report_t snap;
        controls_snapshot(&snap);
        if (tud_hid_report(0, &snap, CONTROLS_REPORT_SIZE)) {
            // 2) El tercer DMA copia g_controls (SRAM) sobre el buffer del endpoint (DPSRAM)
            dma_usb_refresh();
        }
    }
}