/*
version 0.1.0
Copyright 2018-2022, Benjamin Mickler
Written by Benjamin Mickler
https://github.com/BenjaminMickler/simpletap_switchbox
Email: ben@benmickler.com

All portions of Felix Biego's ESP32_BLE_OTA_Arduino software in this software
have been released under the MIT license (see LICENSE.MIT) and copyright
for these portions of the software is owned by Felix Biego.

Designed to run on an ESP32
<https://www.espressif.com/en/products/socs/esp32>
<https://en.wikipedia.org/wiki/ESP32>

Must be compiled with the Ardino core header files.

This file is part of The SimpleTap Project.

The SimpleTap Project is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

The SimpleTap Project is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
The SimpleTap Project. If not, see <https://www.gnu.org/licenses/>.
*/
#include <Update.h>
#include "FS.h"
#include "FFat.h"
#include "SPIFFS.h"
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>
using namespace std;
#define FORMAT_SPIFFS_IF_FAILED true
#define FORMAT_FFAT_IF_FAILED true
#define USE_SPIFFS
#ifdef USE_SPIFFS
#define FLASH SPIFFS
#define FASTMODE false
#else
#define FLASH FFat
#define FASTMODE true
#endif
#define NORMAL_MODE   0
#define UPDATE_MODE   1
#define OTA_MODE      2
uint8_t updater[16384];
uint8_t updater2[16384];
#define SERVICE_UUID              "fb1e4001-54ae-4a28-9f74-dfccb248601d"
#define CHARACTERISTIC_UUID_RX    "fb1e4002-54ae-4a28-9f74-dfccb248601d"
#define CHARACTERISTIC_UUID_TX    "fb1e4003-54ae-4a28-9f74-dfccb248601d"
#define sCHARACTERISTIC_UUID_TX   "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
#define cfgCHARACTERISTIC_UUID    "881f328a-9254-468f-ae0a-075cfc54e137"
static BLECharacteristic* pCharacteristicTX;
static BLECharacteristic* spCharacteristicTX;
static BLECharacteristic* pCharacteristicRX;
static BLECharacteristic *cfgpCharacteristic;
static bool deviceConnected = false, sendMode = false, sendSize = true;
bool oldDeviceConnected = false;
static bool writeFile = false, request = false;
static int writeLen = 0, writeLen2 = 0;
static bool current = true;
static int parts = 0, next = 0, cur = 0, MTU = 0;
static int MODE = NORMAL_MODE;
unsigned long rParts, tParts;

static void rebootEspWithReason(String reason) {
    Serial.println(reason);
    delay(1000);
    ESP.restart();
}
class bservercallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
    }
    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
    }
};
vector<String> readFile(fs::FS &fs, const char * path){
   File file = fs.open(path);
   if(!file || file.isDirectory()){
    SPIFFS.remove(path);
    writeFileFunc(SPIFFS, path, "");
   }
   vector<String> v;
   while (file.available()) {
     v.push_back(file.readStringUntil('\n'));
   }
   file.close();
   return v;
}

bool writeFileFunc(fs::FS &fs, const char * path, const char * message){
   File file = fs.open(path, FILE_WRITE);
   if(!file){
      return false;
   }
   if(file.print(message)){
      return true;
   }else {
      return false;
   }
}
class cfgcallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *cfgpCharacteristic) {
      string value = cfgpCharacteristic->getValue();
      writeFileFunc(SPIFFS, "/config.txt", value.c_str());
      ESP.restart();
    }
};
class bcallbacks: public BLECharacteristicCallbacks {
    void onNotify(BLECharacteristic *pCharacteristic) {
        uint8_t* pData;
        std::string value = pCharacteristic->getValue();
        int len = value.length();
        pData = pCharacteristic->getData();
    }
    void onWrite(BLECharacteristic *pCharacteristic) {
        uint8_t* pData;
        std::string value = pCharacteristic->getValue();
        int len = value.length();
        pData = pCharacteristic->getData();
        if (pData != NULL) {
            if (pData[0] == 0xFB) {
                int pos = pData[1];
                for (int x = 0; x < len - 2; x++) {
                    if (current) {
                        updater[(pos * MTU) + x] = pData[x + 2];
                    } else {
                        updater2[(pos * MTU) + x] = pData[x + 2];
                    }
                    }
                } else if  (pData[0] == 0xFC) {
                    if (current) {
                        writeLen = (pData[1] * 256) + pData[2];
                    } else {
                        writeLen2 = (pData[1] * 256) + pData[2];
                    }
                    current = !current;
                    cur = (pData[3] * 256) + pData[4];
                    writeFile = true;
                    if (cur < parts - 1) {
                        request = !FASTMODE;
                    }
                } else if (pData[0] == 0xFD) {
                    sendMode = true;
                    if (FLASH.exists("/update.bin")) {
                        FLASH.remove("/update.bin");
                    }
                } else if (pData[0] == 0xFE) {
                    rParts = 0;
                    tParts = (pData[1] * 256 * 256 * 256) + (pData[2] * 256 * 256) + (pData[3] * 256) + pData[4];
                } else if  (pData[0] == 0xFF) {
                    parts = (pData[1] * 256) + pData[2];
                    MTU = (pData[3] * 256) + pData[4];
                    MODE = UPDATE_MODE;
                } else if (pData[0] == 0xEF) {
                    FLASH.format();
                    sendSize = true;
                }
            }
        }
};
static void writeBinary(fs::FS &fs, const char * path, uint8_t *dat, int len) {
    File file = fs.open(path, FILE_APPEND);
    if (!file) {
        Serial.println("- failed to open file for writing");
        return;
    }
    file.write(dat, len);
    file.close();
    writeFile = false;
    rParts += len;
}
void sendOtaResult(String result) {
    pCharacteristicTX->setValue(result.c_str());
    pCharacteristicTX->notify();
    delay(200);
}
void performUpdate(Stream &updateSource, size_t updateSize) {
    char s1 = 0x0F;
    String result = String(s1);
    if (Update.begin(updateSize)) {
        size_t written = Update.writeStream(updateSource);
        if (written == updateSize) {
            Serial.println("Written: " + String(written) + " successfully");
        }
        else {
            Serial.println("Written only: " + String(written) + "/" + String(updateSize) + ". Retry?");
        }
        result += "Written: " + String(written) + "/" + String(updateSize) + " [" + String((written / updateSize) * 100) + "%] \n";
        if (Update.end()) {
            Serial.println("OTA done!");
            result += "OTA Done: ";
            if (Update.isFinished()) {
                Serial.println("Update successfully completed. Rebooting...");
                result += "Success!\n";
            }
            else {
                Serial.println("Update not finished? Something went wrong!");
                result += "Failed!\n";
            }

        }
        else {
            Serial.println("Error Occurred. Error #: " + String(Update.getError()));
            result += "Error #: " + String(Update.getError());
        }
    }
    else
    {
        Serial.println("Not enough space to begin OTA");
        result += "Not enough space for OTA";
    }
    if (deviceConnected) {
        sendOtaResult(result);
        delay(5000);
    }
}
void updateFromFS(fs::FS &fs) {
    File updateBin = fs.open("/update.bin");
    if (updateBin) {
        if (updateBin.isDirectory()) {
            Serial.println("Error, update.bin is not a file");
            updateBin.close();
            return;
        }
        size_t updateSize = updateBin.size();
        if (updateSize > 0) {
            Serial.println("Trying to start update");
            performUpdate(updateBin, updateSize);
        }
        else {
            Serial.println("Error, file is empty");
        }
        updateBin.close();
        Serial.println("Removing update file");
        fs.remove("/update.bin");
        rebootEspWithReason("Rebooting to complete OTA update");
    }
    else {
        Serial.println("Could not load update.bin from spiffs root");
    }
}
BLEServer *pServer = NULL;
void setup() {
    Serial.begin(115200);
    pinMode(5, INPUT_PULLUP);
    pinMode(0, INPUT_PULLUP);
    pinMode(18, INPUT_PULLUP);
    pinMode(19, INPUT_PULLUP);
    pinMode(4, INPUT_PULLUP);
#ifdef USE_SPIFFS
    if (!SPIFFS.begin(FORMAT_SPIFFS_IF_FAILED)) {
        Serial.println("SPIFFS Mount Failed");
        return;
    }
#else
    if (!FFat.begin()) {
        Serial.println("FFat Mount Failed");
        if (FORMAT_FFAT_IF_FAILED) FFat.format();
        return;
    }
#endif
    if (SPIFFS.exists("/config.txt") == 0) {
      writeFileFunc(SPIFFS, "/config.txt", "SimpleTap SwitchBox\n500");
     // while (w != true) {
      //  w = writeFileFunc(SPIFFS, "/config.txt", "SimpleTap SwitchBox\n500");
      //}
    }
    vector<String> cfg = readFile(SPIFFS, "/config.txt");
    BLEDevice::init(cfg[0].c_str());
    BLEServer *pServer = BLEDevice::createServer();
    pServer->setCallbacks(new bservercallbacks());
    BLEService *pService = pServer->createService(SERVICE_UUID);
    pCharacteristicTX = pService->createCharacteristic(CHARACTERISTIC_UUID_TX, BLECharacteristic::PROPERTY_NOTIFY );
    spCharacteristicTX = pService->createCharacteristic(sCHARACTERISTIC_UUID_TX, BLECharacteristic::PROPERTY_NOTIFY );
    pCharacteristicRX = pService->createCharacteristic(CHARACTERISTIC_UUID_RX, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
    pCharacteristicRX->setCallbacks(new bcallbacks());
    pCharacteristicTX->setCallbacks(new bcallbacks());
    spCharacteristicTX->setCallbacks(new bcallbacks());
    pCharacteristicTX->addDescriptor(new BLE2902());
    pCharacteristicTX->setNotifyProperty(true);
    spCharacteristicTX->addDescriptor(new BLE2902());
    spCharacteristicTX->setNotifyProperty(true);
    cfgpCharacteristic = pService->createCharacteristic(cfgCHARACTERISTIC_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
    cfgpCharacteristic->setCallbacks(new cfgcallbacks());
    cfgpCharacteristic->setValue(cfg[0].c_str());
    pService->start();
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();
}
void loop() {
    switch (MODE) {
        case NORMAL_MODE:
            if (deviceConnected) {
                int switch0val = digitalRead(5);
                int switch1val = digitalRead(0);
                int switch2val = digitalRead(18);
                int switch3val = digitalRead(19);
                int switch4val = digitalRead(4);
                if (switch0val == LOW) {
                    spCharacteristicTX->setValue("0");
                    spCharacteristicTX->notify();
                    delay(500);
                }
                if (switch1val == LOW) {
                    spCharacteristicTX->setValue("1");
                    spCharacteristicTX->notify();
                    delay(500);
                }
                if (switch2val == LOW) {
                    spCharacteristicTX->setValue("2");
                    spCharacteristicTX->notify();
                    delay(500);
                }
                if (switch3val == LOW) {
                    spCharacteristicTX->setValue("3");
                    spCharacteristicTX->notify();
                    delay(500);
                }
                if (switch4val == LOW) {
                    spCharacteristicTX->setValue("4");
                    spCharacteristicTX->notify();
                    delay(500);
                }
                if (sendMode) {
                    uint8_t fMode[] = {0xAA, FASTMODE};
                    pCharacteristicTX->setValue(fMode, 2);
                    pCharacteristicTX->notify();
                    delay(50);
                    sendMode = false;
                }
                if (sendSize) {
                  unsigned long x = FLASH.totalBytes();
                  unsigned long y = FLASH.usedBytes();
                  uint8_t fSize[] = {0xEF, (uint8_t) (x >> 16), (uint8_t) (x >> 8), (uint8_t) x, (uint8_t) (y >> 16), (uint8_t) (y >> 8), (uint8_t) y};
                  pCharacteristicTX->setValue(fSize, 7);
                  pCharacteristicTX->notify();
                  delay(50);
                  sendSize = false;
                }
                delay(10);
            } else {

            }
            if (!deviceConnected && oldDeviceConnected) {
                delay(500);
                pServer->startAdvertising();
                oldDeviceConnected = deviceConnected;
            }
            if (deviceConnected && !oldDeviceConnected) {
                oldDeviceConnected = deviceConnected;
            }
            break;
        case UPDATE_MODE:
            if (request) {
                uint8_t rq[] = {0xF1, (cur + 1) / 256, (cur + 1) % 256};
                pCharacteristicTX->setValue(rq, 3);
                pCharacteristicTX->notify();
                delay(50);
                request = false;
            }
            if (cur + 1 == parts) { // received complete file
                uint8_t com[] = {0xF2, (cur + 1) / 256, (cur + 1) % 256};
                pCharacteristicTX->setValue(com, 3);
                pCharacteristicTX->notify();
                delay(50);
                MODE = OTA_MODE;
            }
            if (writeFile) {
                if (!current) {
                    writeBinary(FLASH, "/update.bin", updater, writeLen);
                } else {
                    writeBinary(FLASH, "/update.bin", updater2, writeLen2);
                }
            }
            break;
        case OTA_MODE:
            if (writeFile) {
                if (!current) {
                  writeBinary(FLASH, "/update.bin", updater, writeLen);
                } else {
                  writeBinary(FLASH, "/update.bin", updater2, writeLen2);
                }
              }
              if (rParts == tParts) {
                delay(5000);
                updateFromFS(FLASH);
              } else {
                writeFile = true;
                delay(2000);
              }
            break;
    }
}
