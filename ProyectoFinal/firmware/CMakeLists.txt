cmake_minimum_required(VERSION 3.13)

# Usa tu pico_sdk_import.cmake existente
include(pico_sdk_import.cmake)

project(arcade_ctrl C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(arcade_ctrl
    main.c
    read_74hc165.c
    read_adc.c
    usb_data_tx.c
    actuadores.c
)

# Genera read_74hc165.pio.h a partir de tu programa PIO
pico_generate_pio_header(arcade_ctrl ${CMAKE_CURRENT_LIST_DIR}/read_74hc165.pio)

# Para que TinyUSB encuentre tusb_config.h
target_include_directories(arcade_ctrl PRIVATE ${CMAKE_CURRENT_LIST_DIR})

target_link_libraries(arcade_ctrl
    pico_stdlib
    pico_unique_id
    hardware_pio
    hardware_dma
    hardware_adc
    hardware_pwm
    hardware_clocks
    hardware_watchdog
    tinyusb_device

)

# El USB es del HID: la depuración (printf) sale por UART0 (GPIO0/GPIO1)
pico_enable_stdio_usb(arcade_ctrl 0)
pico_enable_stdio_uart(arcade_ctrl 1)

pico_add_extra_outputs(arcade_ctrl)