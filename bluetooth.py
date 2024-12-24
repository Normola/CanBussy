import sys

sys.path.append("")

import asyncio
import aioble
import bluetooth

import random
import struct

import machine

_BINARY_DATA_SERVICE = bluetooth.UUID(0x183B)
_GENERIC_LEVEL = bluetooth.UUID(0x2AF9)
_ADV_APPEARANCE_SENSOR = const(0x015)

_ADV_INTERVAL_MS = 250_000

temp_service = aioble.Service(_BINARY_DATA_SERVICE)
temp_characteristic = aioble.Characteristic(
    temp_service, _GENERIC_LEVEL, read=True, notify=True
)
aioble.register_services(temp_service)

def _encode_data(data):
    return struct.pack("<h", int(data))

async def sensor_task():
    t = 24.5
    while True:
        temp_characteristic.write(_encode_data(t), send_update=True)
        t = random.uniform(0,100)
        await asyncio.sleep_ms(10)
        
async def peripheral_task():
    while True:
        print("Name can-data")
        print("Services {0}".format([_BINARY_DATA_SERVICE]))
        print("Appearance: {_ADV_APPEARANCE_SENSOR}")
        async with await aioble.advertise(
            _ADV_INTERVAL_MS,
            name="can-data",
            services=[_BINARY_DATA_SERVICE],
            appearance=_ADV_APPEARANCE_SENSOR,
        ) as connection:
            print("Connection from", connection.device)
            await connection.disconnected(timeout_ms=None)
           
async def led_task():
    led = machine.Pin("LED", machine.Pin.OUT)
    
    ledStatus = False
    
    while True:
        
        if (ledStatus):
            led.on()
            ledStatus = False
        else:
            led.off()
            ledStatus = True
    
        await asyncio.sleep_ms(1000)

        
async def main():
    taskOne = asyncio.create_task(sensor_task())
    taskTwo = asyncio.create_task(peripheral_task())
    taskThree = asyncio.create_task(led_task())
    await asyncio.gather(taskOne, taskTwo, taskThree)
    
asyncio.run(main())