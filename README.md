# GaitMelt ESP32

## Estructura del Proyecto

- `ESP32SENDER/ESP32SENDER.ino`: Script para los dispositivos ESP32 emisores.
- `ESP32RECEIVER/ESP32RECEIVER.ino`: Script para el dispositivo ESP32 receptor, el cual además monta el servidor web.
- `ESP32RECEIVER/data`: Carpeta donde está alojada la aplicación web que despliega los datos provenientes de los sensores.


## Librerías requeridas
- TwoWayESP
- ESP32 (https://randomnerdtutorials.com/installing-the-esp32-board-in-arduino-ide-windows-instructions/)
- WiFi
- Adafruit Unified Sensor
- Adafruit MPU6050
- ESPAsyncWebSrv
- Arduino_JSON
