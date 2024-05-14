

#include "tasks.h"



void setup() {
  
  Serial.begin(115200);

  pinMode(MOTORINA, OUTPUT);
  pinMode(MOTORINB, OUTPUT);

  setupMPU();
  setupBLE();

  xTaskCreatePinnedToCore(vTaskReadMPUData,
                          "read MPU",
                          20*1024,
                          NULL,
                          1,
                          NULL,
                          0);

  xTaskCreatePinnedToCore(vTaskBLEHandler,
                          "BLE Handler",
                          20*1024,
                          NULL,
                          1,
                          NULL,
                          1);
}

void loop() {
  
}
