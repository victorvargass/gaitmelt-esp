#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#define BOARD_ID 1
#define MOTORINA 26 
#define MOTORINB 25

#define SERVICE_UUID        "6e7f9ca5-5177-4f24-964a-e28e7859ce7e"
#define MPU_CHARACTERISTIC_UUID "894f1b23-1f24-4faf-8e58-04c26db94813"
#define MOTOR_CHARACTERISTIC_UUID "fd2d07fa-0fc2-4ef9-bafc-4cbaf99413c5"
#define NUM_STRUCTS_TO_SEND 16 // Cantidad de structs a enviar por buffer

BLEServer* pServer = NULL;
BLECharacteristic* pMPUCharacteristic = NULL;
BLECharacteristic* pMotorCharacteristic = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;

Adafruit_MPU6050 mpu;
float vibrationDuration = 100;
unsigned int readingMPUId = 0;

// Struct de datos de MPU
struct struct_message_mpu {
  int board_id;
  float acc_x;
  float acc_y;
  float acc_z;
  float gyr_x;
  float gyr_y;
  float gyr_z;
  float readingId;
  unsigned long timestamp;
};

//Buffer de struct de datos de MPU (16)
struct_message_mpu mpuReadings[NUM_STRUCTS_TO_SEND];

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
  unsigned long timestamp = millis();
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  data->board_id = BOARD_ID;
  data->acc_x = a.acceleration.x;
  data->acc_y = a.acceleration.y;
  data->acc_z = a.acceleration.z;
  data->gyr_x = g.gyro.x;
  data->gyr_y = g.gyro.y;
  data->gyr_z = g.gyro.z;
  data->readingId = readingMPUId++;
  data->timestamp = timestamp;
}

// Empaquetar los structs en buffer
void packStructsToBytes(struct_message_mpu *data, uint8_t *buffer, int num_structs) {
  memcpy(buffer, data, sizeof(struct_message_mpu) * num_structs);
}

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

//Inicio conexión BLE
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

void setup() {
  Serial.begin(115200);
  pinMode(MOTORINA, OUTPUT);
  pinMode(MOTORINB, OUTPUT);
  setupMPU();
  setupBLE();
}

void loop() {
  static int structsRead = 0; // Variable para mantener un registro de cuántas estructuras se han leído

  if (deviceConnected) {
    if (structsRead < NUM_STRUCTS_TO_SEND) {
      unsigned long startTime_mpuRead = micros();
      // Leer los datos de la MPU solo si no hemos leído suficientes estructuras aún
      readMPUData(&mpuReadings[structsRead]);
      structsRead++;
      Serial.printf("\r\nMPU read delay: [%lu]\r\n",micros()-startTime_mpuRead);
    }
    if (structsRead >= NUM_STRUCTS_TO_SEND) {
      unsigned long startTime_bleSend = micros();
      uint8_t buffer[sizeof(struct_message_mpu) * NUM_STRUCTS_TO_SEND];
      packStructsToBytes(mpuReadings, buffer, NUM_STRUCTS_TO_SEND);
      pMPUCharacteristic->setValue(buffer, sizeof(buffer));
      pMPUCharacteristic->notify();
      // Reiniciar el contador de estructuras leídas
      structsRead = 0;
      delay(10); //Para evitar la congestion de BT
      Serial.printf("\r\nBLE send delay: [%lu]\r\n",micros()-startTime_bleSend);
    }
  }
  // Desconectando
  if (!deviceConnected && oldDeviceConnected) {
    Serial.println("Device disconnected.");
    delay(500);
    pServer->startAdvertising();
    Serial.println("Start advertising");
    oldDeviceConnected = deviceConnected;
  }
  // Conectando
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = deviceConnected;
    Serial.println("Device Connected");
  }
}
