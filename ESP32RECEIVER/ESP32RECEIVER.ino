/*
  Rui Santos
  Complete project details at https://RandomNerdTutorials.com/esp32-esp-now-wi-fi-web-server/

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files.

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.
*/
#include <esp_now.h>
#include "ESPAsyncWebServer.h"
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include "SPIFFS.h"

// Set your Board ID (ESP32 Sender #1 = BOARD_ID 1, ESP32 Sender #2 = BOARD_ID 2, etc)
#define BOARD_ID 1
#define MOTORINA 25
#define MOTORINB 26

Adafruit_MPU6050 mpu;
bool motorState = LOW;
byte motorVelocity = 1023;
float vibrationDuration = 2000;

uint8_t broadcastAddress[6] = {};

/*
uint8_t broadcastAddress_2[] = {0xA0, 0xB7, 0x65, 0xDD, 0x9E, 0xA0};
uint8_t broadcastAddress_3[] = {0xE0, 0x5A, 0x1B, 0x75, 0x6C, 0x1C};
uint8_t broadcastAddress_4[] = {0xE0, 0x5A, 0x1B, 0x75, 0x6C, 0x1C};
*/

// Replace with your network credentials (STATION)
const char *ssid = "MEPL";
const char *password = "5843728K";

//const char *ssid = "WIFI_14000";
//const char *password = "wifi14000";

// Structure example to receive data
// Must match the sender structure
typedef struct struct_message_mpu
{
  int id; // must be unique for each sender board
  float acc_x;
  float acc_y;
  float acc_z;
  float gyr_x;
  float gyr_y;
  float gyr_z;
  float readingId;
} struct_message_mpu;

typedef struct struct_message_motor
{
  int id;
  bool state;
  float speed;
} struct_message_motor;

struct_message_motor thisMotor;
struct_message_motor incomingMotor;

struct_message_mpu incomingMPUReading;

unsigned int readingMPUId = 0;

// Tamaño del búfer de caracteres para las cadenas JSON
const int JSON_BUFFER_SIZE = 256;
char jsonString[JSON_BUFFER_SIZE];
char macStr[18];

AsyncWebServer server(80);
AsyncEventSource events("/events");

void OnDataRecv(const uint8_t *mac_addr, const uint8_t *incomingData, int len)
{
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02x:%02x:%02x:%02x:%02x:%02x",
           mac_addr[0], mac_addr[1], mac_addr[2], mac_addr[3], mac_addr[4], mac_addr[5]);
  // Serial.print("Packet received from: ");
  // Serial.println(macStr);

  memcpy(&incomingMPUReading, incomingData, sizeof(incomingMPUReading));

  const int JSON_BUFFER_SIZE = 256;
  char *jsonString = (char *)malloc(JSON_BUFFER_SIZE * sizeof(char));

  snprintf(jsonString, JSON_BUFFER_SIZE,
           "{\"board_id\": %d, \"acc_x\": %.2f, \"acc_y\": %.2f, \"acc_z\": %.2f, \"gyr_x\": %.2f, \"gyr_y\": %.2f, \"gyr_z\": %.2f, \"readingId\": %.2f}",
           incomingMPUReading.id, incomingMPUReading.acc_x, incomingMPUReading.acc_y, incomingMPUReading.acc_z,
           incomingMPUReading.gyr_x, incomingMPUReading.gyr_y, incomingMPUReading.gyr_z, incomingMPUReading.readingId);

  events.send(jsonString, "mpu_readings", millis());

  free(jsonString);
}

// callback when data is sent
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status)
{
  Serial.print("\r\nLast Packet Send Status:\t");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

void readMPUData()
{

  static const int JSON_BUFFER_SIZE = 256;
  static char jsonString[JSON_BUFFER_SIZE];

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  readingMPUId++;
  snprintf(jsonString, JSON_BUFFER_SIZE,
           "{\"board_id\": %d, \"acc_x\": %.2f, \"acc_y\": %.2f, \"acc_z\": %.2f, \"gyr_x\": %.2f, \"gyr_y\": %.2f, \"gyr_z\": %.2f, \"readingId\": %d}",
           BOARD_ID, a.acceleration.x, a.acceleration.y, a.acceleration.z,
           g.gyro.x, g.gyro.y, g.gyro.z, readingMPUId);

  events.send(jsonString, "mpu_readings", millis());
}

void sendMotor(int id)
{
  incomingMotor.id = id;
  incomingMotor.state = true;
  incomingMotor.speed = 1023;
  /*
  if (id == 2)
  {
    memcpy(broadcastAddress, broadcastAddress_2, sizeof(broadcastAddress));
  }
  if (id == 3)
  {
    memcpy(broadcastAddress, broadcastAddress_3, sizeof(broadcastAddress));
  }
  if (id == 4)
  {
    memcpy(broadcastAddress, broadcastAddress_4, sizeof(broadcastAddress));
  }
  */
  esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *)&incomingMotor, sizeof(incomingMotor));
  if (result == ESP_OK)
  {
    Serial.println("Sent with success");
  }
  else
  {
    Serial.println("Error sending the data");
  }
}

void add_peer(const uint8_t *mac_addr)
{
  // Register peer
  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, mac_addr, 6);
  peerInfo.encrypt = false;

  // Add peer
  if (esp_now_add_peer(&peerInfo) != ESP_OK)
  {
    Serial.println("Failed to add peer");
    return;
  }
}

void setup(void)
{
  Serial.begin(115200);
  pinMode(MOTORINA, OUTPUT);
  pinMode(MOTORINB, OUTPUT);
  while (!Serial)
    delay(10); // will pause Zero, Leonardo, etc until serial console opens

  Serial.println("Adafruit MPU6050 test!");

  // Try to initialize!
  if (!mpu.begin())
  {
    Serial.println("Failed to find MPU6050 chip");
    while (1)
    {
      delay(10);
    }
  }
  Serial.println("MPU6050 Found!");

  // Initialize SPIFFS
  if (!SPIFFS.begin(true))
  {
    Serial.println("An Error has occurred while mounting SPIFFS");
    return;
  }

  // Set the device as a Station and Soft Access Point simultaneously
  WiFi.mode(WIFI_AP_STA);

  // Set device as a Wi-Fi Station
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(1000);
    Serial.println("Setting as a Wi-Fi Station..");
  }
  Serial.print("Station IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Wi-Fi Channel: ");
  Serial.println(WiFi.channel());
  Serial.println(ESP.getFreeHeap());
  // Init ESP-NOW
  if (esp_now_init() != ESP_OK)
  {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_send_cb(OnDataSent);

  // add_peer(broadcastAddress_2);
  // add_peer(broadcastAddress_3);
  // add_peer(broadcastAddress_4);

  // esp_now_register_recv_cb(OnDataRecv);

  // Route for root / web page
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request)
            {
              Serial.println("/");
              request->send(SPIFFS, "/index.html", "text/html"); });

  // Route for root / web page
  server.on("/script.js", HTTP_GET, [](AsyncWebServerRequest *request)
            { request->send(SPIFFS, "/script.js", "text/javascript"); });

  // Route to load style.css file
  server.on("/styles.css", HTTP_GET, [](AsyncWebServerRequest *request)
            { request->send(SPIFFS, "/styles.css", "text/css"); });

  server.on("/motor1", HTTP_GET, [](AsyncWebServerRequest *request)
            {
    motorState = !motorState;
    analogWrite(MOTORINA, motorVelocity);
    analogWrite(MOTORINB, 0);
    delay(vibrationDuration);
    motorState = !motorState;
    analogWrite(MOTORINA, 0);
    analogWrite(MOTORINB, 0);
    request->send(SPIFFS, "/index.html", String(motorState), true); });

  server.on("/motor2", HTTP_GET, [](AsyncWebServerRequest *request)
            { 
              sendMotor(2);
              request->send(SPIFFS, "/index.html", String(), true); });

  server.on("/motor3", HTTP_GET, [](AsyncWebServerRequest *request)
            { 
              sendMotor(3);
              request->send(SPIFFS, "/index.html", String(), true); });

  server.on("/motor4", HTTP_GET, [](AsyncWebServerRequest *request)
            { 
              sendMotor(4);
              request->send(SPIFFS, "/index.html", String(), true); });

  events.onConnect([](AsyncEventSourceClient *client)
                   {
    if(client->lastId()){
      Serial.printf("Client reconnected! Last message ID that it got is: %u\n", client->lastId());
    }
    // send event with message "hello!", id current millis
    // and set reconnect delay to 1 second
    client->send("hello!", NULL, millis(), 10000); });

  server.addHandler(&events);
  server.begin();
}

void loop()
{
  static unsigned long lastEventTime = millis();
  static const unsigned long EVENT_INTERVAL_MS = 5000;
  if ((millis() - lastEventTime) > EVENT_INTERVAL_MS)
  {
    events.send("ping", NULL, millis());
    lastEventTime = millis();
  }

  readMPUData();
  delay(100);
}
