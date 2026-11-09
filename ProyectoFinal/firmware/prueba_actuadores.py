import time
import sys

# Intentar importar la librería hid
try:
    import hid
except ImportError:
    print("Error: Requiere la librería 'hid'. Instálala ejecutando: pip install hidapi")
    sys.exit(1)

# Constantes del Dispositivo (según tu desc_device)
VENDOR_ID = 0xCafe
PRODUCT_ID = 0x4001
REPORT_SIZE = 8

# Constantes de Comandos (Asumiendo valores estándar basados en tu código)
CMD_VIB = 0x01
CMD_BUZ = 0x02
CMD_LED = 0x03

def enviar_reporte(dispositivo, datos_comando):
    """
    Formatea el comando a 8 bytes y lo envía.
    En USB HID, si el dispositivo NO usa Report ID (tu caso), 
    el primer byte enviado al método write() DEBE SER 0x00. El buffer 
    real del reporte comienza en el segundo byte.
    """
    # Rellenamos con ceros hasta cumplir con el tamaño del reporte (8 bytes)
    buffer_salida = [0x00] + datos_comando + [0x00] * (REPORT_SIZE - len(datos_comando))
    
    try:
        dispositivo.write(buffer_salida)
    except Exception as e:
        print(f"❌ Error al enviar datos: {e}")

def probar_actuadores():
    print("Buscando Raspberry Pi Pico (HID)...")
    try:
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        print(f"✅ Conectado exitosamente al dispositivo {hex(VENDOR_ID)}:{hex(PRODUCT_ID)}")
    except Exception as e:
        print(f"❌ No se pudo abrir el dispositivo: {e}")
        print("Asegúrate de que la Pico esté conectada y que tengas permisos de lectura/escritura (en Linux podrías requerir sudo o reglas udev).")
        return

    try:
        while True:
            print("\n--- MENÚ DE PRUEBAS ---")
            print("1. Encender LED 1")
            print("2. Apagar LED 1")
            print("3. Encender LED 2")
            print("4. Apagar LED 2")
            print("5. Probar Buzzer (Tono)")
            print("6. Secuencia rápida de test")
            print("0. Salir")
            
            opcion = input("Selecciona una opción: ")
            
            if opcion == '1':
                print("Enviando: LED 1 ENCENDIDO")
                # [CMD_LED, id_led, estado]
                enviar_reporte(device, [CMD_LED, 1, 1])
                
            elif opcion == '2':
                print("Enviando: LED 1 APAGADO")
                enviar_reporte(device, [CMD_LED, 1, 0])
                
            elif opcion == '3':
                print("Enviando: LED 2 ENCENDIDO")
                enviar_reporte(device, [CMD_LED, 2, 1])
                
            elif opcion == '4':
                print("Enviando: LED 2 APAGADO")
                enviar_reporte(device, [CMD_LED, 2, 0])
                
            elif opcion == '5':
                try:
                    hz = int(input("Introduce frecuencia (Hz, ej: 440): "))
                    ms = int(input("Introduce duración (ms, ej: 500): "))
                    
                    # Estructura del buzzer según tu código:
                    # buffer[0] = CMD_BUZ
                    # buffer[1] = hz (Tu código recibe buffer[1], ten en cuenta que si es uint16_t podría estar truncado o mapeado como Little Endian)
                    # buffer[3] = ms
                    # Ajusta estos índices en la lista si tu mapeo de bytes en C cambia.
                    paquete_buzzer = [CMD_BUZ, hz & 0xFF, (hz >> 8) & 0xFF, ms & 0xFF, (ms >> 8) & 0xFF]
                    
                    print(f"Enviando: Buzzer {hz}Hz por {ms}ms")
                    enviar_reporte(device, paquete_buzzer)
                except ValueError:
                    print("⚠️ Por favor introduce números válidos.")
                    
            elif opcion == '6':
                print("Iniciando secuencia...")
                # Alternar LEDs y hacer sonar el buzzer
                enviar_reporte(device, [CMD_LED, 1, 1])
                time.sleep(0.2)
                enviar_reporte(device, [CMD_LED, 2, 1])
                # Tono de 880Hz por 200ms
                enviar_reporte(device, [CMD_BUZ, 880 & 0xFF, (880 >> 8) & 0xFF, 200 & 0xFF, (200 >> 8) & 0xFF])
                time.sleep(0.3)
                enviar_reporte(device, [CMD_LED, 1, 0])
                enviar_reporte(device, [CMD_LED, 2, 0])
                print("Secuencia terminada.")
                
            elif opcion == '0':
                break
            else:
                print("Opción no válida.")
                
    except KeyboardInterrupt:
        print("\nPrueba cancelada por el usuario.")
    finally:
        print("Cerrando dispositivo...")
        device.close()
        print("¡Adiós!")

if __name__ == "__main__":
    probar_actuadores()
