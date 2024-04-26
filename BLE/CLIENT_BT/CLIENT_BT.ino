#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#define BOARD_ID 3
#define MOTORINA 26
#define MOTORINB 25

// https://www.uuidgenerator.net/

#define SERVICE_UUID        "54095b1e-941e-4d7c-8465-e29a70b84f5a"
#define SENSOR_CHARACTERISTIC_UUID "4ce979b1-4717-4b37-af73-f83605649e2c"
#define MOTOR_CHARACTERISTIC_UUID "6688009e-3db8-4fa9-8027-af5bdc0fcf4d"
#define NUM_STRUCTS_TO_SEND 16

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
struct_message_mpu mpuReadings[NUM_STRUCTS_TO_SEND]; // Arreglo para almacenar las lecturas

void packStructsToBytes(struct_message_mpu *data, uint8_t *buffer, int num_structs) {
  memcpy(buffer, data, sizeof(struct_message_mpu) * num_structs);
}

const long interval = 10;
unsigned int readingMPUId = 0;

void readMPUData() {
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

  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1)
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
   static int structsRead = 0; // Variable para mantener un registro de cuántas estructuras se han leído
  // notify changed value
  if (deviceConnected) {
    if (structsRead < NUM_STRUCTS_TO_SEND) {
      // Leer los datos de la MPU solo si no hemos leído suficientes estructuras aún
      readMPUData();
      // Almacenar los datos en el arreglo
      mpuReadings[structsRead] = thisMPUReadings;
      // Incrementar el contador de estructuras leídas
      structsRead++;
    }
    // Solo enviar cuando hayamos leído suficientes estructuras
    if (structsRead >= NUM_STRUCTS_TO_SEND) {
      // Convertir estructuras a bytes y establecer el valor de la característica BLE
      uint8_t buffer[sizeof(struct_message_mpu) * NUM_STRUCTS_TO_SEND];
      packStructsToBytes(mpuReadings, buffer, NUM_STRUCTS_TO_SEND);
      pSensorCharacteristic->setValue(buffer, sizeof(buffer));
      pSensorCharacteristic->notify();

      // Reiniciar el contador de estructuras leídas
      structsRead = 0;
      delay(interval); // bluetooth stack will go into congestion, if too many packets are sent, in 6 hours test i was able to go as low as 3ms
    }
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