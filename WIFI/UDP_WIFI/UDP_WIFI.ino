#include <WebServer.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "time.h"

#define BOARD_ID 1 // BOARD_ID 1, 2, 3, 4
const char* deviceName = "GaitMelt Device 1"; // Nombre del dispositivo
#define MOTORINA 26
#define MOTORINB 25

Adafruit_MPU6050 mpu;
float motorPower = 255;
float vibrationDuration = 500;
unsigned long startTime;

// Estructura de datos de MPU
struct struct_message_mpu {
  int board_id;
  float acc_x;
  float acc_y;
  float acc_z;
  float gyr_x;
  float gyr_y;
  float gyr_z;
  unsigned long timestamp;
};

// Inicio de conexión con el MPU6050
void setupMPU() {
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip"); // Falló la detección del chip MPU6050
    while (1);
  }
  Serial.println("MPU6050 Found!"); // MPU6050 detectado
}

// Leer datos del MPU6050
void readMPUData(struct_message_mpu *data) {
  sensors_event_t a, g, temp;
  
  unsigned long currentTime = millis();  // Obtenemos el tiempo actual
  unsigned long epoch_timestamp = currentTime - startTime;  // Calculamos el tiempo transcurrido desde la referencia
  
  mpu.getEvent(&a, &g, &temp);
  data->board_id = BOARD_ID;
  data->acc_x = a.acceleration.x;
  data->acc_y = a.acceleration.y;
  data->acc_z = a.acceleration.z;
  data->gyr_x = g.gyro.x;
  data->gyr_y = g.gyro.y;
  data->gyr_z = g.gyro.z;
  data->timestamp = epoch_timestamp;
}

// Estructura de datos de MPU
struct_message_mpu mpuReadings;

// IP de la máquina a la que envías mensajes - esta debe ser la IP correcta en la mayoría de los casos (ver nota en el código de Python)
#define CONSOLE_IP "192.168.50.82" // IP del receptor
#define CONSOLE_PORT 4210

// Reemplaza con tus credenciales de red
const char* ssid = "Gaitmelt"; // SSID
const char* password = "Gaitmelt"; // Contraseña

WiFiUDP Udp;
WebServer server(80);

unsigned long motorOnTime = 0; // Marca de tiempo cuando el motor se enciende
bool motorState = false; // Estado actual del motor

void setupWIFI() {
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.setHostname(deviceName);
  WiFi.begin(ssid, password);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 10) {
    delay(500);
    Serial.print(".");
    retries++;
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Failed to connect to WiFi"); // Falló la conexión a WiFi
    return;
  }
  Serial.println("");
  Serial.println("WiFi connected."); // WiFi conectado
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  server.begin();
  Udp.begin(CONSOLE_PORT);
}

void setup() {
  Serial.begin(115200);
  pinMode(MOTORINA, OUTPUT);
  pinMode(MOTORINB, OUTPUT);
  setupMPU();
  setupWIFI();
  startTime = millis();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting..."); // WiFi desconectado. Reconectando...
    setupWIFI();
  }
  
  // Enviar datos del MPU
  readMPUData(&mpuReadings);
  uint8_t buffer[sizeof(mpuReadings)];
  memcpy(buffer, &mpuReadings, sizeof(mpuReadings));
  Udp.beginPacket(CONSOLE_IP, CONSOLE_PORT);
  Udp.write(buffer, sizeof(buffer));
  Udp.endPacket();

  // Recibir paquete de control del motor
  int packetSize = Udp.parsePacket();
  if (packetSize) {
      char incomingPacket[255];
      int len = Udp.read(incomingPacket, 255);
      if (len > 0) {
          incomingPacket[len] = 0;
      }

      // Comprobamos si el paquete es "reset"
      if (strcmp(incomingPacket, "reset") == 0) {
          startTime = millis();
      }
      // Comprobamos si el paquete es "motor"
      else if (strcmp(incomingPacket, "motor") == 0) {
          motorState = true;
          analogWrite(MOTORINA, motorPower);
          analogWrite(MOTORINB, 0);
          motorOnTime = millis();
      }
      // Comprobamos si el paquete es "power"
      else if (strncmp(incomingPacket, "power", 5) == 0) {
          // Extraemos el valor de potencia del mensaje
          int powerValue = atoi(incomingPacket + 5);
          if (powerValue >= 0 && powerValue <= 255) {
              motorPower = powerValue;
          }
      }
      // Comprobamos si el paquete es "duration"
      else if (strncmp(incomingPacket, "duration", 8) == 0) {
          // Extraemos el valor de duración del mensaje
          int duration = atoi(incomingPacket + 8);
          if (duration > 0 && duration <= 2000) {
              vibrationDuration = (float)duration;
          }
      }
      // Mensaje no reconocido
      else {
          Serial.println("wrong message");
      }
  }

  // Verificar si el motor debe apagarse
  if (motorState && (millis() - motorOnTime >= vibrationDuration)) {
    analogWrite(MOTORINA, 0);
    analogWrite(MOTORINB, 0);
    motorState = false;
  }

  delay(10);
}
