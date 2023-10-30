#include <esp_now.h>
#include <esp_wifi.h>
#include <WiFi.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_MPU6050.h>

// Set your Board ID (ESP32 Sender #1 = BOARD_ID 1, ESP32 Sender #2 = BOARD_ID 2, etc)
#define BOARD_ID 3
#define ledPin 2

// Adafruit_MPU6050 mpu;
bool ledState = LOW;

// MAC Address of the receiver
// uint8_t broadcastAddress[] = {0xB0, 0xB2, 0x1C, 0x0A, 0xD0, 0x58};
uint8_t broadcastAddress[] = {0xA0, 0xB7, 0x65, 0xDC, 0xCF, 0x5C};

// Structure example to send data
// Must match the receiver structure
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

// Create a struct_message called thisMPUReadings and thisMotorReadings
struct_message_mpu thisMPUReadings;
struct_message_motor incomingMotor;
struct_message_motor thisMotor;

unsigned long previousMillis = 0; // Stores last time temperature was published
const long interval = 100;        // Interval at which to publish sensor readings

unsigned int readingMPUId = 0;

// Define variables to store incoming readings
float incomingMotorSpeed;

// Insert your SSID
constexpr char WIFI_SSID[] = "MEPL";

int32_t getWiFiChannel(const char *ssid)
{
  if (int32_t n = WiFi.scanNetworks())
  {
    for (uint8_t i = 0; i < n; i++)
    {
      if (!strcmp(ssid, WiFi.SSID(i).c_str()))
      {
        return WiFi.channel(i);
      }
    }
  }
  return 0;
}

void readMPUData()
{
  thisMPUReadings.id = BOARD_ID;
  thisMPUReadings.acc_x = 10.0;
  thisMPUReadings.acc_y = 10.0;
  thisMPUReadings.acc_z = 10.0;
  thisMPUReadings.gyr_x = 0.1;
  thisMPUReadings.gyr_y = 0.1;
  thisMPUReadings.gyr_z = 0.1;
  thisMPUReadings.readingId = readingMPUId++;
}

/*
void readMPUData()
{
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  thisMPUReadings.id = BOARD_ID;
  thisMPUReadings.acc_x = a.acceleration.x;
  thisMPUReadings.acc_y = a.acceleration.y;
  thisMPUReadings.acc_z = a.acceleration.z;
  thisMPUReadings.gyr_x = g.gyro.x;
  thisMPUReadings.gyr_y = g.gyro.y;
  thisMPUReadings.gyr_z = g.gyro.z;
  thisMPUReadings.readingId = readingMPUId++;
}
*/

void setIncomingMotorData()
{
  thisMotor.id = BOARD_ID;
  thisMotor.speed = incomingMotor.speed;
  thisMotor.state = incomingMotor.state;
}

// callback when data is sent
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status)
{
  Serial.print("\r\nLast Packet Send Status:\t");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

// Callback when data is received
void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len)
{
  incomingMotor = *(struct_message_motor *)incomingData;
  setIncomingMotorData();
}

void setup()
{
  // Init Serial Monitor
  Serial.begin(115200);

  /* Initialize the sensor */
  /*
  if (!mpu.begin())
  {
    Serial.println("Failed to find MPU6050 chip");
    while (1)
      ;
    delay(10);
  }
  Serial.println("MPU6050 Found!");
  */

  // Init the motor settings
  //

  // Set device as a Wi-Fi Station and set channel
  WiFi.mode(WIFI_STA);

  int32_t channel = getWiFiChannel(WIFI_SSID);
  Serial.print(channel);

  WiFi.printDiag(Serial); // Uncomment to verify channel number before
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);
  WiFi.printDiag(Serial); // Uncomment to verify channel change after

  // Init ESP-NOW
  if (esp_now_init() != ESP_OK)
  {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Once ESPNow is successfully Init, we will register for Send CB to
  // get the status of Trasnmitted packet
  esp_now_register_send_cb(OnDataSent);

  // Register peer
  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.encrypt = false;

  // Add peer
  if (esp_now_add_peer(&peerInfo) != ESP_OK)
  {
    Serial.println("Failed to add peer");
    return;
  }

  // Register for a callback function that will be called when data is received
  esp_now_register_recv_cb(OnDataRecv);
}

void loop()
{
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval)
  {
    previousMillis = currentMillis;
    readMPUData();

    esp_err_t result = esp_now_send(broadcastAddress, (uint8_t *)&thisMPUReadings, sizeof(thisMPUReadings));
    if (result == ESP_OK)
    {
      Serial.println("Sent with success");
    }
    else
    {
      Serial.println("Error sending the data");
    }
  }
}