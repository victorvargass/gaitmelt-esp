#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "MPU.h"

#define SERVICE_UUID        "6e7f9ca5-5177-4f24-964a-e28e7859ce7e"
#define MPU_CHARACTERISTIC_UUID "894f1b23-1f24-4faf-8e58-04c26db94813"
#define MOTOR_CHARACTERISTIC_UUID "fd2d07fa-0fc2-4ef9-bafc-4cbaf99413c5"

#define MOTORINA 26 
#define MOTORINB 25



BLEServer* pServer = NULL;

BLECharacteristic* pMPUCharacteristic = NULL;
BLECharacteristic* pMotorCharacteristic = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;
float vibrationDuration = 100;
static int structsRead = 0; // Variable para mantener un registro de cuántas estructuras se han leído



// Seteo callbacks BLE
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
    }
};

// Seteo características BLE para el motor
class MotorCharacteristicCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* pMotorCharacteristic) {
      std::string value = pMotorCharacteristic->getValue();
      if (value.length() > 0) {
        Serial.print("Characteristic event, written: ");
        Serial.println(static_cast<int>(value[0])); // Print the integer value

        int receivedValue = static_cast<int>(value[0]);
        if (receivedValue == 1) {
          analogWrite(MOTORINA, 1023);
          analogWrite(MOTORINB, 0);
          delay(vibrationDuration);
          analogWrite(MOTORINA, 0);
          analogWrite(MOTORINB, 0);
        }
      }
    }
};



void setupBLE() {

  std::string deviceName = "GaitMelt Device " + std::to_string(BOARD_ID);
  BLEDevice::init(deviceName.c_str());

  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pMPUCharacteristic = pService->createCharacteristic(
                            MPU_CHARACTERISTIC_UUID,
                            BLECharacteristic::PROPERTY_READ   |
                            BLECharacteristic::PROPERTY_WRITE  |
                            BLECharacteristic::PROPERTY_NOTIFY |
                            BLECharacteristic::PROPERTY_INDICATE
                          );

  pMotorCharacteristic = pService->createCharacteristic(
                           MOTOR_CHARACTERISTIC_UUID,
                           BLECharacteristic::PROPERTY_WRITE
                         );

  pMotorCharacteristic->setCallbacks(new MotorCharacteristicCallbacks());

  pMPUCharacteristic->addDescriptor(new BLE2902());
  pMotorCharacteristic->addDescriptor(new BLE2902());

  pService->start();

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);
  BLEDevice::startAdvertising();
  Serial.println("Waiting a client connection to notify...");

}

