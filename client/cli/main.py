__author__ = "Benjamin Mickler"
__copyright__ = "Copyright 2018-2022, Benjamin Mickler"
__credits__ = ["Benjamin Mickler"]
__license__ = "GPLv3 or later"
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
import json
import shlex
import subprocess
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

if len(config["switchboxes"]) > 1:
    print("Select a switchbox: ")
    it = -1
    for i in config["switchboxes"]:
        it += 1
        print(str(it)+" "+i)
    chosen_box = config["switchboxes"][int(input("> "))]
else:
    chosen_switchbox = config["switchboxes"][0]

print("Select a profile: ")
for i in config["profiles"]:
    print(i)
profile = config["profiles"][input("> ")]

mac_addr = asyncio.run(get_mac(chosen_switchbox))

ADDRESS = (
    mac_addr
    if platform.system() != "Darwin"
    else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
)

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
    asyncio.run(main(ADDRESS,config["CHARACTERISTIC_UUID"],))
