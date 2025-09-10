import board
import busio
import digitalio
import time
import wifi
import socketpool
from adafruit_mcp2515 import MCP2515 as CAN
from adafruit_mcp2515.canio import Message, RemoteTransmissionRequest

# Immediate startup message
print("Starting CAN Bridge - Wi-Fi Mode...")

# Status LED setup (Pico Plus 2W onboard LED)
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = False
print("LED initialized")

# Wi-Fi Access Point setup
ap_ssid = "PicoCAN"
ap_password = "canbus12345"  # Changed to longer password for better compatibility

def set_led_status(state):
    """Control LED for status indication"""
    led.value = state
    print(f"LED set to: {'ON' if state else 'OFF'}")
    
def blink_led(times=1, delay=0.1):
    """Blink LED for status indication"""
    print(f"Blinking LED {times} times")
    for _ in range(times):
        led.value = True
        time.sleep(delay)
        led.value = False
        time.sleep(delay)

# Heartbeat tracking
heartbeat_interval = 30  # seconds
last_heartbeat = time.time()

print("=== CAN Bus Wi-Fi Bridge ===")
print("Starting Wi-Fi Access Point...")

# Initialize Wi-Fi in AP mode with Android-compatible settings
import ipaddress

# Start AP with specific channel for better Android compatibility
try:
    wifi.radio.start_ap(ap_ssid, ap_password, channel=6, max_connections=4)
except TypeError:
    # Fallback if channel/max_connections not supported
    wifi.radio.start_ap(ap_ssid, ap_password)

# Set IP configuration
wifi.radio.set_ipv4_address_ap(
    ipv4=ipaddress.IPv4Address("192.168.4.1"),
    netmask=ipaddress.IPv4Address("255.255.255.0"),
    gateway=ipaddress.IPv4Address("192.168.4.1")
)

print(f"Access Point started. SSID: {ap_ssid}")
print(f"AP IP address: {wifi.radio.ipv4_address_ap}")
print("Network: 192.168.4.0/24")
print("DHCP range: 192.168.4.2 - 192.168.4.254")
print("DNS server: 192.168.4.1")
print("")
print("Android troubleshooting:")
print("If connection fails, try setting static IP on Android:")
print("IP: 192.168.4.2, Gateway: 192.168.4.1, DNS: 192.168.4.1")
print("Then connect to 192.168.4.1:1234 for CAN data")

set_led_status(True)  # LED on: AP active

# CAN setup
print("Initializing CAN controller...")
cs = digitalio.DigitalInOut(board.GP5)
cs.switch_to_output()
spi = busio.SPI(board.GP6, board.GP7, board.GP4)  # SCK, MOSI, MISO
can_bus = CAN(spi, cs, loopback=False, silent=True)
print("CAN controller initialized")

def format_can_for_wireshark(msg):
    """Format CAN message for Wireshark analysis"""
    timestamp = time.time()
    can_id = msg.id
    
    if isinstance(msg, Message):
        data = ','.join([str(b) for b in msg.data])
        return f"{timestamp},{can_id},{len(msg.data)},{data}\n"
    
    if isinstance(msg, RemoteTransmissionRequest):
        return f"{timestamp},{can_id},RTR,{msg.length}\n"
    
    return f"{timestamp},{can_id},UNKNOWN,0\n"

def check_heartbeat():
    """Check if heartbeat should be printed"""
    global last_heartbeat
    current_time = time.time()
    if current_time - last_heartbeat >= heartbeat_interval:
        uptime = int(current_time)
        print(f"💓 Heartbeat - System running, uptime: {uptime}s")
        last_heartbeat = current_time
        return True
    return False

def process_can_messages(listener, client):
    """Process CAN messages and send to client"""
    message_count = listener.in_waiting()
    if not message_count:
        return
        
    print(f"Processing {message_count} CAN messages")
    
    for _ in range(message_count):
        msg = listener.receive()
        print(f"CAN ID: 0x{msg.id:03X}", end="")
        
        if isinstance(msg, Message):
            print(f", Data: {[hex(b) for b in msg.data]}")
        
        if isinstance(msg, RemoteTransmissionRequest):
            print(f", RTR Length: {msg.length}")
        
        # Send to Wi-Fi client
        stream = format_can_for_wireshark(msg)
        client.send(stream.encode('utf-8'))
        
        # Quick blink for each message
        blink_led(1, 0.05)

def handle_client_connection(client, addr):
    """Handle individual client connection"""
    print(f"*** Client connected from {addr} ***")
    blink_led(3, 0.2)  # Blink 3 times: client connected
    set_led_status(False)  # LED off: client active
    
    try:
        while True:
            with can_bus.listen(timeout=1.0) as listener:
                process_can_messages(listener, client)
                # Check heartbeat during client connection
                if check_heartbeat():
                    blink_led(1, 0.05)  # Heartbeat blink
                
    except Exception as e:
        print(f"*** Client disconnected: {e} ***")
        client.close()
        blink_led(5, 0.1)  # Blink 5 times: error/disconnect
        set_led_status(True)  # Back to waiting state

# TCP server setup
tcp_port = 1234
print(f"Starting TCP server on port {tcp_port}...")
pool = socketpool.SocketPool(wifi.radio)
server_socket = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
server_socket.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", tcp_port))
server_socket.listen(1)
print(f"TCP server listening on port {tcp_port}")
print("=== System Ready ===")
print(f"Heartbeat every {heartbeat_interval} seconds")

while True:
    print("\n--- Waiting for client connection ---")
    set_led_status(True)  # LED on: waiting for client
    
    # Set socket to non-blocking for heartbeat
    server_socket.settimeout(1.0)
    
    try:
        client, addr = server_socket.accept()
        handle_client_connection(client, addr)
    except OSError:
        # Timeout - check heartbeat while waiting
        if check_heartbeat():
            blink_led(2, 0.1)  # Double blink for heartbeat while waiting

