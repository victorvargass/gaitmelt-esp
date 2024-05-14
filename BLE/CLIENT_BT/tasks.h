
#include "BLE.h"

void vTaskReadMPUData(void *pvParameters){
  
  while(1){

    
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
      
    }
    
  }
}

void vTaskBLEHandler(void *pvParameters){
  while(1){
      if(deviceConnected){
          // Solo enviar cuando hayamos leído suficientes estructuras
          if (structsRead >= NUM_STRUCTS_TO_SEND) {
            // Convertir estructuras a bytes y establecer el valor de la característica BLE
            uint8_t buffer[sizeof(struct_message_mpu) * NUM_STRUCTS_TO_SEND];
            packStructsToBytes(mpuReadings, buffer, NUM_STRUCTS_TO_SEND);
            pMPUCharacteristic->setValue(buffer, sizeof(buffer));
            pMPUCharacteristic->notify();

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
}