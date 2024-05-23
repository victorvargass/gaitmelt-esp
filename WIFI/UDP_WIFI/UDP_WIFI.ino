#include <WebServer.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "time.h"

#define BOARD_ID 1 //BOARD_ID 1, 2, 3, 4
#define MOTORINA 26
#define MOTORINB 25

String MOTORINAState = "off";
String MOTORINBState = "off";

Adafruit_MPU6050 mpu;
float vibrationDuration = 100;
const char* ntpServer = "pool.ntp.org";
unsigned long long epoch_timestamp;

// Struct de datos de MPU
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

unsigned long long getTimestampMillis() {
  struct timeval tv;
  gettimeofday(&tv, NULL);
  unsigned long long milliseconds = (unsigned long long)(tv.tv_sec) * 1000ULL + (unsigned long long)(tv.tv_usec) / 1000ULL;
  return milliseconds;
}

void setupNTP() {
  configTime(-10800, 0, ntpServer);
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to obtain time");
  }
  Serial.println("Time synchronized");
}

//Inicio conexión MPU
void setupMPU() {
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1);
  }
  Serial.println("MPU6050 Found!");
}
// Leer datos MPU
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

//Struct de datos de MPU
struct_message_mpu mpuReadings;

// the IP of the machine to which you send msgs - this should be the correct IP in most cases (see note in python code)
#define CONSOLE_IP "192.168.1.18" //IP RECEIVER
#define CONSOLE_PORT 4210

// Replace with your network credentials
const char* ssid     = "MEPL"; //SSID
const char* password = "5843728K"; //PASSWORD

// Variable to store the HTTP request
String header;

WiFiUDP Udp;
IPAddress local_IP(192, 168, 1, 184); //IP FIJA, CAMBIAR PARA CADA ESP
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 0, 0);
IPAddress dns(8,8,8,8);
WebServer server(80);

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
    Serial.println("Failed to connect to WiFi");
    return;
  }
  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  server.begin();
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
    Serial.println("WiFi disconnected. Reconnecting...");
    setupWIFI();
  }
  readMPUData(&mpuReadings);
  uint8_t buffer[sizeof(mpuReadings)];
  memcpy(buffer, &mpuReadings, sizeof(mpuReadings));
  Udp.beginPacket(CONSOLE_IP, CONSOLE_PORT);
  Udp.write(buffer, sizeof(buffer));
  Udp.endPacket();
  delay(10);
}