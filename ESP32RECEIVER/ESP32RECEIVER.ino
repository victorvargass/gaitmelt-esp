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
#include <Arduino_JSON.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include "SPIFFS.h"

// Set your Board ID (ESP32 Sender #1 = BOARD_ID 1, ESP32 Sender #2 = BOARD_ID 2, etc)
#define BOARD_ID 4

Adafruit_MPU6050 mpu;
const int ledPin = 2;
String ledState;

// Replace with your network credentials (STATION)
const char *ssid = "WIFI_SSID";
const char *password = "WIFI_PASS";

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

struct_message_mpu incomingMPUReading;

unsigned int readingMPUId = 0;
JSONVar mpu1;
JSONVar mpu2;
JSONVar mpu3;
JSONVar mpu4;

AsyncWebServer server(80);
AsyncEventSource events("/events");

// callback function that will be executed when data is received
void OnDataRecv(const uint8_t *mac_addr, const uint8_t *incomingData, int len)
{
  // Copies the sender mac address to a string
  char macStr[18];
  Serial.print("Packet received from: ");
  snprintf(macStr, sizeof(macStr), "%02x:%02x:%02x:%02x:%02x:%02x",
           mac_addr[0], mac_addr[1], mac_addr[2], mac_addr[3], mac_addr[4], mac_addr[5]);
  Serial.println(macStr);
  memcpy(&incomingMPUReading, incomingData, sizeof(incomingMPUReading));

  JSONVar mpuJSON;
  mpuJSON["id"] = incomingMPUReading.id;
  mpuJSON["acc_x"] = incomingMPUReading.acc_x;
  mpuJSON["acc_y"] = incomingMPUReading.acc_y;
  mpuJSON["acc_z"] = incomingMPUReading.acc_z;
  mpuJSON["gyr_x"] = incomingMPUReading.gyr_x;
  mpuJSON["gyr_y"] = incomingMPUReading.gyr_y;
  mpuJSON["gyr_z"] = incomingMPUReading.gyr_z;
  mpuJSON["readingId"] = String(incomingMPUReading.readingId);

  String jsonString = JSON.stringify(mpuJSON);

  events.send(jsonString.c_str(), "new_readings", millis());

  Serial.printf("Board ID %u: %u bytes\n", incomingMPUReading.id, len);
  Serial.printf("acc_x value: %4.2f \n", incomingMPUReading.acc_x);
  Serial.printf("acc_y value: %4.2f \n", incomingMPUReading.acc_y);
  Serial.printf("acc_z value: %4.2f \n", incomingMPUReading.acc_z);
  Serial.printf("gyr_x value: %4.2f \n", incomingMPUReading.gyr_x);
  Serial.printf("gyr_y value: %4.2f \n", incomingMPUReading.gyr_y);
  Serial.printf("gyr_z value: %4.2f \n", incomingMPUReading.gyr_z);
  Serial.printf("readingID value: %d \n", incomingMPUReading.readingId);
  Serial.println();
}

float readMPUData()
{
  // Sensor readings may also be up to 2 seconds 'old' (its a very slow sensor)
  // Read temperature as Celsius (the default)

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  JSONVar mpuJSON;
  mpuJSON["id"] = BOARD_ID;
  mpuJSON["acc_x"] = a.acceleration.x;
  mpuJSON["acc_y"] = a.acceleration.y;
  mpuJSON["acc_z"] = a.acceleration.z;
  mpuJSON["gyr_x"] = g.gyro.x;
  mpuJSON["gyr_y"] = g.gyro.y;
  mpuJSON["gyr_z"] = g.gyro.z;
  readingMPUId++;
  mpuJSON["readingId"] = readingMPUId;

  String jsonString = JSON.stringify(mpuJSON);

  events.send(jsonString.c_str(), "new_readings", millis());
}

String processor(const String &var)
{
  Serial.println(var);
  if (var == "STATE")
  {
    if (digitalRead(ledPin))
    {
      ledState = "ON";
    }
    else
    {
      ledState = "OFF";
    }
    Serial.print(ledState);
    return ledState;
  }
  return String();
}

void setup(void)
{
  // Initialize Serial Monitor
  Serial.begin(115200);

  /* Initialize the sensor */
  if (!mpu.begin())
  {
    Serial.println("Failed to find MPU6050 chip");
    while (1)
      ;
    delay(10);
  }
  Serial.println("MPU6050 Found!");

  // mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  // mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  // mpu.setFilterBandwidth(MPU6050_BAND_5_HZ);
  // Serial.println("");

  // Init the motor settings
  //

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

  // Init ESP-NOW
  if (esp_now_init() != ESP_OK)
  {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Once ESPNow is successfully Init, we will register for recv CB to
  // get recv packer info
  esp_now_register_recv_cb(OnDataRecv);

  // Route for root / web page
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request)
            { request->send(SPIFFS, "/index.html", String(), false, processor); });

  // Route to load style.css file
  server.on("/style.css", HTTP_GET, [](AsyncWebServerRequest *request)
            { request->send(SPIFFS, "/style.css", "text/css"); });

  // Route to set GPIO to HIGH
  server.on("/on", HTTP_GET, [](AsyncWebServerRequest *request)
            {
    digitalWrite(ledPin, HIGH);    
    request->send(SPIFFS, "/index.html", String(), false, processor); });

  // Route to set GPIO to LOW
  server.on("/off", HTTP_GET, [](AsyncWebServerRequest *request)
            {
    digitalWrite(ledPin, LOW);    
    request->send(SPIFFS, "/index.html", String(), false, processor); });

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
  // Set values for this MPU
  readMPUData();
}