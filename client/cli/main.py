import sys
import asyncio
import platform
from bleak import BleakClient, BleakScanner
import json
from pynput.keyboard import Key, Controller
with open("config.txt") as f:
    config = json.load(f)
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
    pd = profile[data].split("-")
    if pd[0] == "KEYBOARD_PRESS":
        if pd[1] in special_keys:
            keyboard.press(special_keys[pd[1]])
            keyboard.release(special_keys[pd[1]])
        else:
            keyboard.press(pd[1])
            keyboard.release(pd[1])

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
    asyncio.run(
        main(
            ADDRESS,
            config["CHARACTERISTIC_UUID"],
        )
    )
