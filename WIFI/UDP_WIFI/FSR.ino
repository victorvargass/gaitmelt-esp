#include <WebServer.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include "time.h"

#define BOARD_ID 1 // BOARD_ID 1, 2, 3, 4
const char* deviceName = "GaitMelt Device 1"; // Nombre del dispositivo
#define MOTORINA 26
#define MOTORINB 25

#define DERECHA 34
#define TALON 35
#define PULGAR 36
#define IZQUIERDA 39

float motorPower = 255;
float vibrationDuration = 500;
unsigned long startTime;

// Estructura de datos
struct struct_message {
  int board_id;
  int pulgar;
  int izquierda;
  int derecha;
  int talon;
  unsigned long timestamp;
};

// Leer datos del FSR
void readFSRData(struct_message *data) {
  unsigned long currentTime = millis();
  unsigned long epoch_timestamp = currentTime - startTime;
  data->board_id = BOARD_ID;
  data->pulgar = analogRead(PULGAR);
  data->izquierda = analogRead(IZQUIERDA);
  data->derecha = analogRead(DERECHA);
  data->talon = analogRead(TALON);
  data->timestamp = epoch_timestamp;
}

// Estructura de datos FSR
struct_message fsrReading;

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
  pinMode(DERECHA, INPUT);
  pinMode(TALON, INPUT);
  pinMode(PULGAR, INPUT);
  pinMode(IZQUIERDA, INPUT);
  setupWIFI();
  startTime = millis();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting..."); // WiFi desconectado. Reconectando...
    setupWIFI();
  }
  
  // Enviar datos del FSR
  readFSRData(&fsrReading);
  uint8_t buffer[sizeof(fsrReading)];
  memcpy(buffer, &fsrReading, sizeof(fsrReading));
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
      else if (strncmp(incomingPacket, "motor", 5) == 0) {
          motorState = true;
          int vibrationOffset = atoi(incomingPacket + 5);
          Serial.println(vibrationOffset);
          delay(vibrationOffset);
          analogWrite(MOTORINA, motorPower);
          analogWrite(MOTORINB, 0);
          motorOnTime = millis();
      }      
      else if (strcmp(incomingPacket, "stop") == 0) {
          analogWrite(MOTORINA, 0);
          analogWrite(MOTORINB, 0);
          motorState = false;
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
          if (duration > 0) {
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
