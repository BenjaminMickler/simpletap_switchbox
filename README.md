# SimpleTap SwitchBox
The SimpleTap SwitchBox is part of The SimpleTap Project.

It is switchbox designed for the SimpleTap (but works with other devices too). It currently supports up to 5 switches.

## Client
### Configuration
A file named `config.json` must be present in the same directory as the switchbox client.
#### Example configuration:
```json
{
  "extensions": ["os"],
  "default_profile": "Sarepta",
  "switch_notify_UUID": "6E400003-B5A3-F393-E0A9-E50E24DCCA9E",
  "config_UUID": "881f328a-9254-468f-ae0a-075cfc54e137",
  "update_RX": "fb1e4002-54ae-4a28-9f74-dfccb248601d",
  "update_TX": "fb1e4003-54ae-4a28-9f74-dfccb248601d",
  "switchboxes": ["SimpleTap switchbox"],
  "profiles": {
    "Sarepta": {
      "0": {
        "extension": "gui",
        "function": "press_key",
        "args": "F1"
      },
      "1": {
        "extension": "gui",
        "function": "press_key",
        "args": "F2"
      },
      "2": {
        "extension": "gui",
        "function": "press_key",
        "args": "F3"
      },
      "3": {
        "extension": "gui",
        "function": "press_key",
        "args": "F4"
      },
      "4": {
        "extension": "gui",
        "function": "press_key",
        "args": "F5"
      }
    },
    "do nothing": {
      "0": {
        "extension": ""
      },
      "1": {
        "extension": ""
      },
      "2": {
        "extension": ""
      },
      "3": {
        "extension": ""
      },
      "4": {
        "extension": ""
      }
    }
  }
}
```
### Setting name
The name of the switchbox can be changed. The switchbox's name must be unique to any other devices in range as it is used by the client to get the switchbox's MAC address. To change a switchbox's name, create a text file called `name` (no extension) in the same directory as the client. Write the new name into the text file and save. When the client is started, it checks for the file `name`. If it is found, `name` will be read and the data inside will be written to the configuration characteristic of the chosen switchbox. If the new name is sucessfully written to the characteristic, the file `name` will be deleted. The switchbox will then save the new name and then reboot. The new name comes into effect after the reboot.

### Updating firmware
The client can update the switchbox's firmware over BLE. To update a switchbox's firmware, place the firmware file in the same directory as the client. The only requirement is that the firmware file's extension is `.bin`. When the client is started, it checks for any files with the `.bin` extension. If there are multiple, the firmware file used is arbitrary. If found, the client will upload it to the chosen switchbox and the switchbox will install it. If the update is sucessful, the client will delete the firmware file.

## SwitchBox firmware
### UUIDs
Service: `fb1e4001-54ae-4a28-9f74-dfccb248601d`

Switch notifications: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E`

Configuration: `881f328a-9254-468f-ae0a-075cfc54e137`

Update RX: `fb1e4002-54ae-4a28-9f74-dfccb248601d`

Update TX: `fb1e4003-54ae-4a28-9f74-dfccb248601d`

## BLE OTA
The SimpleTap SwitchBox supports firmware updates over Bluetooth Low Energy.

The client's BLE OTA functionality is built on the [BLE_OTA_Python](https://github.com/fbiego/BLE_OTA_Python) project by Felix Biego and the switchbox firmware's BLE OTA functionality is built on the [ESP32_BLE_OTA_Arduino](https://github.com/fbiego/ESP32_BLE_OTA_Arduino) project by Felix Biego.

All portions of Felix Biego's BLE_OTA_Python software in the switchbox client and Felix Biego's ESP32_BLE_OTA_Arduino software in the switchbox firmware have been released under the MIT license (see [LICENSE.MIT](https://github.com/BenjaminMickler/simpletap_switchbox/blob/main/LICENSE.MIT)) and copyright for these portions of the software is owned by Felix Biego.

The rest of the software has been released under the GNU GPLv3 (or later) license (see [LICENSE](https://github.com/BenjaminMickler/simpletap_switchbox/blob/main/LICENSE)) and copyright is owned by Benjamin Mickler.
