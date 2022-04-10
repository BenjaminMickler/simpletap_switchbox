__author__ = "Benjamin Mickler"
__copyright__ = ["Copyright 2018-2022, Benjamin Mickler", "Copyright (c) 2021 Felix Biego"]
__credits__ = ["Benjamin Mickler", "Felix Biego"]
__license__ = ["GPLv3 or later", "MIT"]
__version__ = "0.1.0"
__maintainer__ = "Benjamin Mickler"
__email__ = "ben@benmickler.com"
__status__ = "Prototype"

"""
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
"""

import sys
import asyncio
import platform
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
import json
import shlex
import subprocess
import glob
import os
import math
# Felix Biego's BLE_OTA_Python | Copyright (c) 2021 Felix Biego (MIT license)
UART_SERVICE_UUID = "fb1e4001-54ae-4a28-9f74-dfccb248601d"
UART_RX_CHAR_UUID = "fb1e4002-54ae-4a28-9f74-dfccb248601d"
UART_TX_CHAR_UUID = "fb1e4003-54ae-4a28-9f74-dfccb248601d"
CFG_CHAR_UUID = "881f328a-9254-468f-ae0a-075cfc54e137"
PART = 16000
MTU = 500

end = True
clt = None
fileBytes = None
total = 0
def get_bytes_from_file(filename):
    print("Reading from:", filename)
    return open(filename, "rb").read()
async def set_name(address, name, ci, config):
    try:
        async with BleakClient(address) as client:
            await client.write_gatt_char(CFG_CHAR_UUID, name.encode())
        os.remove("name")
        config["switchboxes"][ci] = name
        with open("config.txt", "w") as f:
            json.dump(config, f)
        return "Success"
    except Exception as e:
        return e
async def start_ota(ble_address: str, file_name: str):
    device = await BleakScanner.find_device_by_address(ble_address, timeout=20.0)
    disconnected_event = asyncio.Event()

    def handle_disconnect(_: BleakClient):
        global disconnect
        disconnect = False
        print(": Device disconnected")
        disconnected_event.set()
            
    async def handle_rx(_: int, data: bytearray):
        if (data[0] == 0xAA):
            print("Transfer mode:", data[1])
            printProgressBar(0, total, prefix = 'Progress:', suffix = 'Complete', length = 50)
            if data[1] == 1:
                for x in range(0, fileParts):
                    await send_part(x, fileBytes, clt)
                    printProgressBar(x + 1, total, prefix = 'Progress:', suffix = 'Complete', length = 50)
            else:
                await send_part(0, fileBytes, clt)
                
        if (data[0] == 0xF1):
            nxt = int.from_bytes(bytearray([data[1], data[2]]), "big")  
            await send_part(nxt, fileBytes, clt)
            printProgressBar(nxt + 1, total, prefix = 'Progress:', suffix = 'Complete', length = 50)
        if (data[0] == 0xF2):
            ins = 'Installing firmware'
            #print("Installing firmware")
        if (data[0] == 0x0F):
            result = bytearray([])
            for s in range(1, len(data)):
                result.append(data[s])
            print("OTA result:", str(result, 'utf-8'))
            global end
            end = False
            if "Success" in str(result, 'utf-8'):
                print(f'Removing "{file_name}"')
                os.remove(file_name)
        #print("received:", data)

    def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
        # Print New Line on Complete
        if iteration == total: 
            print()

    async def send_part(position: int, data: bytearray, client: BleakClient):
        start = (position * PART)
        end = (position + 1) * PART
        if len(data) < end:
            end = len(data)
        parts = (end - start) / MTU
        for i in range(0, int(parts)):
            toSend = bytearray([0xFB, i])
            for y in range(0, MTU):
                toSend.append(data[(position*PART)+(MTU * i) + y])
            await send_data(client, toSend, False)
        if (end - start)%MTU != 0:
            rem = (end - start)%MTU
            toSend = bytearray([0xFB, int(parts)])
            for y in range(0, rem):
                toSend.append(data[(position*PART)+(MTU * int(parts)) + y])
            await send_data(client, toSend, False)
        update = bytearray([0xFC, int((end - start)/256), int((end - start) % 256), int(position/256), int(position % 256) ])
        await send_data(client, update, True)

    async def send_data(client: BleakClient, data: bytearray, response: bool):
        await client.write_gatt_char(UART_RX_CHAR_UUID, data, response)
        
    if not device:
        print("-----------Failed--------------")
        print(f"Device with address {ble_address} could not be found.")
        return
        #raise BleakError(f"A device with address {ble_address} could not be found.")
    async with BleakClient(device, disconnected_callback=handle_disconnect) as client:
        await client.start_notify(UART_TX_CHAR_UUID, handle_rx)
        await asyncio.sleep(1.0)
        
        await send_data(client, bytearray([0xFD]), False)
        
        global fileBytes
        fileBytes = get_bytes_from_file(file_name)
        global clt
        clt = client
        fileParts = math.ceil(len(fileBytes) / PART)
        fileLen = len(fileBytes)
        fileSize = bytearray([0xFE, fileLen >>  24 & 0xFF, fileLen >>  16 & 0xFF, fileLen >>  8 & 0xFF, fileLen & 0xFF])
        await send_data(client, fileSize, False)
        global total
        total = fileParts
        otaInfo = bytearray([0xFF, int(fileParts/256), int(fileParts%256), int(MTU / 256), int(MTU%256) ])
        await send_data(client, otaInfo, False)
        
        while end:
            await asyncio.sleep(1.0)
        print("Waiting for disconnect... ", end="")
        await disconnected_event.wait()
        print("-----------Complete--------------")
# End BLE_OTA_Python
with open("config.txt") as f:
    config = json.load(f)
if config["wayland/node"] != True:
    from pynput.keyboard import Key, Controller
    keyboard = Controller()
    special_keys = {"enter": Key.enter, "space": Key.space, "F1": Key.f1, "F2": Key.f2, "F3": Key.f3, "F4": Key.f4, "F5": Key.f5}
async def get_mac(wanted_name):
    print("Searching for \""+wanted_name+"\"")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and d.name.lower() == wanted_name.lower()
    )
    return device.address

def notification_handler(sender, data):
    data = data.decode()
    print("Switch "+data+" pressed")
    pd = profile[data].split("|")
    if pd[0] == "KEYBOARD_PRESS":
        if pd[1] in special_keys:
            keyboard.press(special_keys[pd[1]])
            keyboard.release(special_keys[pd[1]])
        else:
            keyboard.press(pd[1])
            keyboard.release(pd[1])
    elif pd[0] == "EXEC":
        subprocess.Popen(shlex.split(pd[1]), start_new_session=True)

async def main(address, char_uuid):
    while True:
        print("Connecting...")
        try:
            async with BleakClient(address) as client:
                print(f"Connected: {client.is_connected}")
                await client.start_notify(char_uuid, notification_handler)
                while True:
                    await asyncio.sleep(2)
                    if bool(client.is_connected) != True:
                        await client.stop_notify(char_uuid)
                        print("Switches disconnected")
                        break
        except Exception as e:
            print(e)

if __name__ == "__main__":
    if len(config["switchboxes"]) > 1:
        print("Select a switchbox: ")
        it = -1
        for i in config["switchboxes"]:
            it += 1
            print(str(it)+" "+i)
        ci = int(input("> "))
        chosen_switchbox = config["switchboxes"][ci]
    else:
        ci = 0
        chosen_switchbox = config["switchboxes"][0]
    mac_addr = asyncio.run(get_mac(chosen_switchbox))
    ADDRESS = (
        mac_addr
        if platform.system() != "Darwin"
        else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
    )
    binaries = glob.glob("*.bin")
    if len(binaries) > 0:
        print("Firmware file found, updating switchbox.")
        asyncio.run(start_ota(ADDRESS, binaries[0]))
    if os.path.isfile("name"):
        with open("name") as f:
            name = f.read().replace('\n','')
        print(f'"name" file found, updating switchbox name to "{name}"')
        print("Result:", asyncio.run(set_name(ADDRESS, name, ci, config)))
    print("Select a profile: ")
    for i in config["profiles"]:
        print(i)
    profile = config["profiles"][input("> ")]
    asyncio.run(main(ADDRESS,config["CHARACTERISTIC_UUID"],))
