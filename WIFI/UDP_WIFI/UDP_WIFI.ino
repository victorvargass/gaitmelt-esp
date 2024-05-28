#include <WebServer.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "time.h"

#define BOARD_ID 1 // BOARD_ID 1, 2, 3, 4
#define MOTORINA 26
#define MOTORINB 25

Adafruit_MPU6050 mpu;
float vibrationDuration = 100;
const char* ntpServer = "pool.ntp.org";
unsigned long long epoch_timestamp;

// Estructura de datos de MPU
struct struct_message_mpu {
  int board_id;
  float acc_x;
  float acc_y;
  float acc_z;
  float gyr_x;
  float gyr_y;
  float gyr_z;
  unsigned long long timestamp;
};

// Obtener la marca de tiempo en milisegundos
unsigned long long getTimestampMillis() {
  struct timeval tv;
  gettimeofday(&tv, NULL);
  unsigned long long milliseconds = (unsigned long long)(tv.tv_sec) * 1000ULL + (unsigned long long)(tv.tv_usec) / 1000ULL;
  return milliseconds;
}

// Configuración del servidor NTP para sincronizar la hora
void setupNTP() {
  configTime(-10800, 0, ntpServer);
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to obtain time"); // Falló la obtención de la hora
  }
  Serial.println("Time synchronized"); // Hora sincronizada
}

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
  epoch_timestamp = getTimestampMillis();

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
#define CONSOLE_IP "192.168.1.14" // IP del receptor
#define CONSOLE_PORT 4210

// Reemplaza con tus credenciales de red
const char* ssid = "MEPL"; // SSID
const char* password = "5843728K"; // Contraseña

WiFiUDP Udp;
IPAddress local_IP(192, 168, 1, 18); // IP fija, cambiar para cada ESP
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 0, 0);
IPAddress dns(8, 8, 8, 8);
WebServer server(80);

unsigned long motorOnTime = 0; // Marca de tiempo cuando el motor se enciende
bool motorState = false; // Estado actual del motor

void setupWIFI() {
  Serial.print("Connecting to ");
  Serial.println(ssid);
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
  setupNTP();
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
    // Suponiendo que el paquete es un solo valor booleano
    motorState = incomingPacket[0] == '1';

    if (motorState) {
      Serial.println("Motor on");
      digitalWrite(MOTORINA, HIGH);
      digitalWrite(MOTORINB, LOW);
      motorOnTime = millis();
    }
  }

  // Verificar si el motor debe apagarse
  if (motorState && (millis() - motorOnTime >= vibrationDuration)) {
    Serial.println("Motor off");
    digitalWrite(MOTORINA, LOW);
    digitalWrite(MOTORINB, LOW);
    motorState = false;
  }


  delay(10);
}
