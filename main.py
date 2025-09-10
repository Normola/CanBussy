import board
import busio
import digitalio
import adafruit_mcp2515
import time
import network
import socket

# Wi-Fi Access Point setup
ap_ssid = "PicoCAN"
ap_password = "canbus123"

wlan = network.WLAN(network.AP_IF)
wlan.active(True)
wlan.config(essid=ap_ssid, password=ap_password)
print("Access Point started. SSID:", ap_ssid)
print("IP address:", wlan.ifconfig()[0])

# SPI and CS setup (adjust pins for your board)
#spi = busio.SPI(board.GP18, board.GP19, board.GP16)  # SCK, MOSI, MISO
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs = digitalio.DigitalInOut(board.GPIO19)

# MCP2515 CAN controller setup
can = adafruit_mcp2515.MCP2515(spi, cs, crystal_freq=8_000_000)
can.bitrate = 500000

# Send a CAN message (ID: 0x123, data: [0x11, 0x22, 0x33, 0x44])
message = adafruit_mcp2515.Message(id=0x123, data=bytes([0x11, 0x22, 0x33, 0x44]))
can.send(message)

def format_can_for_wireshark(msg):
    # Example: timestamp,id,data_length,data_bytes (CSV)
    timestamp = time.monotonic()
    can_id = msg.id
    data = ','.join([str(b) for b in msg.data])
    return f"{timestamp},{can_id},{len(msg.data)},{data}\n"

# TCP server setup
tcp_port = 1234
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", tcp_port))
server_socket.listen(1)
print(f"TCP server listening on port {tcp_port}")

while True:
    print("Waiting for client connection...")
    client, addr = server_socket.accept()
    print("Client connected from", addr)
    try:
        while True:
            msg = can.receive()
            if msg is not None:
                stream = format_can_for_wireshark(msg)
                client.send(stream.encode('utf-8'))
                print("Sent over Wi-Fi:", stream.strip())
    except Exception as e:
        print("Client disconnected:", e)
        client.close()
