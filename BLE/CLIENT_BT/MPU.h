#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#define BOARD_ID 1

Adafruit_MPU6050 mpu;

unsigned int readingMPUId = 0;
const long interval = 10;


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

#define NUM_STRUCTS_TO_SEND 16 // Cantidad de structs a enviar por buffer
//Buffer de struct de datos de MPU (16)
struct_message_mpu mpuReadings[NUM_STRUCTS_TO_SEND]; // Arreglo para almacenar las lecturas
struct_message_mpu thisMPUReadings;


//Inicio conexión MPU
void setupMPU() {
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1);
  }
  Serial.println("MPU6050 Found!");
}

void packStructsToBytes(struct_message_mpu *data, uint8_t *buffer, int num_structs) {
  memcpy(buffer, data, sizeof(struct_message_mpu) * num_structs);
}

void readMPUData(){
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  thisMPUReadings.board_id = BOARD_ID;
  thisMPUReadings.acc_x = a.acceleration.x;
  thisMPUReadings.acc_y = a.acceleration.y;
  thisMPUReadings.acc_z = a.acceleration.z;
  thisMPUReadings.gyr_x = g.gyro.x;
  thisMPUReadings.gyr_y = g.gyro.y;
  thisMPUReadings.gyr_z = g.gyro.z;
  thisMPUReadings.readingId = readingMPUId++;
}


