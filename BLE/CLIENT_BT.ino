#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#define BOARD_ID 4
#define MOTORINA 26
#define MOTORINB 25

// https://www.uuidgenerator.net/

#define SERVICE_UUID        "394b9eb5-53e6-4a6c-8207-1cac1784d622"
#define SENSOR_CHARACTERISTIC_UUID "4a7a8178-c2ac-40e2-85c8-c13b7aabe0ca"
#define MOTOR_CHARACTERISTIC_UUID "60d025dd-417c-4ee6-8ffb-2993d99fb501"

BLEServer* pServer = NULL;
BLECharacteristic* pSensorCharacteristic = NULL;
BLECharacteristic* pMotorCharacteristic = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;

Adafruit_MPU6050 mpu;
bool motorState = LOW;
byte motorVelocity = 1023;
float vibrationDuration = 1000;

typedef struct struct_message_mpu
{
  int id;
  float acc_x;
  float acc_y;
  float acc_z;
  float gyr_x;
  float gyr_y;
  float gyr_z;
  float readingId;
} struct_message_mpu;

struct_message_mpu thisMPUReadings;

// Función para empaquetar la estructura en un array de bytes
void packStructToBytes(struct_message_mpu *data, uint8_t *buffer) {
  memcpy(buffer, data, sizeof(struct_message_mpu));
}

const long interval = 100;
unsigned int readingMPUId = 0;

void readMPUData(){
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


class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
    }
};

class MyCharacteristicCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* pMotorCharacteristic) {
        std::string value = pMotorCharacteristic->getValue();
        if (value.length() > 0) {
            Serial.print("Characteristic event, written: ");
            Serial.println(static_cast<int>(value[0])); // Print the integer value

            int receivedValue = static_cast<int>(value[0]);
            if (receivedValue == 1) {
                analogWrite(MOTORINA, motorVelocity);
                analogWrite(MOTORINB, 0);
                delay(vibrationDuration);
                analogWrite(MOTORINA, 0);
                analogWrite(MOTORINB, 0);
            }
        }
    }
};

void setup() {
  Serial.begin(115200);
  pinMode(MOTORINA, OUTPUT);
  pinMode(MOTORINB, OUTPUT);

  if (!mpu.begin()){
    Serial.println("Failed to find MPU6050 chip");
    while(1)
      ;
    delay(10);
  }
  Serial.println("MPU6050 Found!");

  // Create the BLE Device
  std::string deviceName = "GaitMelt Device " + std::to_string(BOARD_ID);
  BLEDevice::init(deviceName.c_str());

  // Create the BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create a BLE Characteristic
  pSensorCharacteristic = pService->createCharacteristic(
                      SENSOR_CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_INDICATE
                    );

  // Create the ON button Characteristic
  pMotorCharacteristic = pService->createCharacteristic(
                      MOTOR_CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_WRITE
                    );

  // Register the callback for the ON button characteristic
  pMotorCharacteristic->setCallbacks(new MyCharacteristicCallbacks());

  // https://www.bluetooth.com/specifications/gatt/viewer?attributeXmlFile=org.bluetooth.descriptor.gatt.client_characteristic_configuration.xml
  // Create a BLE Descriptor
  pSensorCharacteristic->addDescriptor(new BLE2902());
  pMotorCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();
  Serial.println("Waiting a client connection to notify...");
}

void loop() {
    // notify changed value
    if (deviceConnected) {
        readMPUData();
        // Convertir estructura a bytes y establecer el valor de la característica BLE
        uint8_t buffer[sizeof(struct_message_mpu)];
        packStructToBytes(&thisMPUReadings, buffer);
        pSensorCharacteristic->setValue(buffer, sizeof(buffer));
        pSensorCharacteristic->notify();
        delay(interval); // bluetooth stack will go into congestion, if too many packets are sent, in 6 hours test i was able to go as low as 3ms
    }
    // disconnecting
    if (!deviceConnected && oldDeviceConnected) {
        Serial.println("Device disconnected.");
        delay(500); // give the bluetooth stack the chance to get things ready
        pServer->startAdvertising(); // restart advertising
        Serial.println("Start advertising");
        oldDeviceConnected = deviceConnected;
    }
    // connecting
    if (deviceConnected && !oldDeviceConnected) {
        // do stuff here on connecting
        oldDeviceConnected = deviceConnected;
        Serial.println("Device Connected");
    }
}
