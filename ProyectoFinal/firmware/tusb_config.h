#ifndef TUSB_CONFIG_H_
#define TUSB_CONFIG_H_

#ifdef __cplusplus
extern "C" {
#endif

#ifndef CFG_TUSB_MCU
#error CFG_TUSB_MCU must be defined
#endif

#ifndef CFG_TUSB_OS
#define CFG_TUSB_OS               OPT_OS_NONE
#endif

#define CFG_TUSB_DEBUG            0

// Solo dispositivo (la Pico es el periférico; la RPi es el host)
#define CFG_TUD_ENABLED           1
#define CFG_TUSB_RHPORT0_MODE     (OPT_MODE_DEVICE)

#define CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_ALIGN        __attribute__((aligned(4)))

#define CFG_TUD_ENDPOINT0_SIZE    64

// Clases: solo HID
#define CFG_TUD_HID               1
#define CFG_TUD_CDC               0
#define CFG_TUD_MSC               0
#define CFG_TUD_MIDI              0
#define CFG_TUD_VENDOR            0

#define CFG_TUD_HID_EP_BUFSIZE    16   // >= CONTROLS_REPORT_SIZE (10)

#ifdef __cplusplus
}
#endif

#endif /* TUSB_CONFIG_H_ */