# Hardware Wiring & Pinout Guide

Complete wiring schematic, pin mapping, and power distribution guide for the IoT Road Hazard Detection Robot.

---

## 1. Power Distribution Schematic

```text
               +----------------------------------+
               |  7.4V - 11.1V LiPo Battery Pack  |
               +-----------------+----------------+
                                 |
        +------------------------+------------------------+
        |                                                 |
        v                                                 v
+------------------+                             +------------------+
| LM2596 Buck #1   |                             | LM2596 Buck #2   |
| (Motor Power)    |                             | (Logic Power)    |
| Out: 7.4V - 9.0V |                             | Out: 5.0V / 3.0A |
+--------+---------+                             +--------+---------+
         |                                                |
         v                                                +-----------+
+------------------+                                      |           |
| L298N Motor Hub  |                                      v           v
| 4x DC Motors     |                               +------------+ +-------+
+------------------+                               | RPi 4 USB-C| | ESP32 |
                                                   | 5V / GND   | | VIN   |
                                                   +------------+ +-------+

* CRITICAL: Connect ALL Grounds (Battery (-), LM2596 (-), RPi GND, ESP32 GND, L298N GND) together!
```

---

## 2. Raspberry Pi 4 GPIO Pinout (BCM Mapping)

| Subsystem | Component Pin | Raspberry Pi 4 Pin | BCM GPIO | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Motors (L298N)** | ENA (PWM Left) | Pin 12 | GPIO 18 | PWM Speed Control (0-100%) |
| | IN1 | Pin 11 | GPIO 17 | Left Forward |
| | IN2 | Pin 13 | GPIO 27 | Left Reverse |
| | IN3 | Pin 15 | GPIO 22 | Right Forward |
| | IN4 | Pin 16 | GPIO 23 | Right Reverse |
| | ENB (PWM Right) | Pin 18 | GPIO 24 | PWM Speed Control (0-100%) |
| **Front Ultrasonic** | Trig | Pin 29 | GPIO 5 | 10µs Trigger pulse |
| | Echo | Pin 31 | GPIO 6 | **Must use voltage divider!** (1kΩ/2kΩ) |
| **Left Ultrasonic** | Trig | Pin 33 | GPIO 13 | 10µs Trigger pulse |
| | Echo | Pin 35 | GPIO 19 | **Must use voltage divider!** (1kΩ/2kΩ) |
| **Right Ultrasonic** | Trig | Pin 37 | GPIO 26 | 10µs Trigger pulse |
| | Echo | Pin 38 | GPIO 20 | **Must use voltage divider!** (1kΩ/2kΩ) |
| **GPS (NEO-6M)** | VCC | Pin 1 or 2 | 3.3V or 5V | Clean supply |
| | GND | Pin 6 | GND | Ground |
| | TX | Pin 10 | GPIO 15 (RXD0) | Pi UART Receive |
| | RX | Pin 8 | GPIO 14 (TXD0) | Pi UART Transmit |
| **ESP32 Uplink** | Pi TX (USB/UART) | Pin 8 or USB-TTL| GPIO 14 or USB | Cross connect to ESP32 RX2 |
| | Pi RX (USB/UART) | Pin 10 or USB-TTL| GPIO 15 or USB | Cross connect to ESP32 TX2 |
| | GND | Pin 14 | GND | Common Ground |

---

## 3. HC-SR04 5V to 3.3V Voltage Divider Protection

> [!CAUTION]
> The HC-SR04 Echo pin outputs 5.0V TTL logic. Connecting it directly to Raspberry Pi 3.3V GPIO will permanently damage the Pi. Always wire a 2-resistor voltage divider.

```text
HC-SR04 Echo (5V) ───────[ 1kΩ Resistor ]───┬───> Raspberry Pi GPIO (3.3V Safe)
                                            │
                                     [ 2kΩ Resistor ]
                                            │
                                           GND
```

---

## 4. ESP32 Gateway Pin Mapping

| ESP32 Pin | Function | Connected To | Notes |
| :--- | :--- | :--- | :--- |
| **VIN** | 5V Power In | LM2596 #2 5V Output | Regulated 5V |
| **GND** | System Ground | Common Ground | Common to Pi and Battery |
| **GPIO 16 (RX2)** | Hardware UART RX | Raspberry Pi TX (GPIO 14) | Receives JSON Frames |
| **GPIO 17 (TX2)** | Hardware UART TX | Raspberry Pi RX (GPIO 15) | Sends JSON ACKs |
| **GPIO 34** | ADC Analog Input | Battery Voltage Divider | 4:1 divider to monitor LiPo pack |
| **GPIO 2** | Built-in Blue LED | Internal | Blinks on Wi-Fi search, Solid when connected |

---

## 5. Camera Module Setup
- **Raspberry Pi Camera v2 / v3**: Connect flat ribbon cable to the CSI port with blue tape facing the Ethernet jack.
- **USB Webcam Alternative**: Plug into any USB 3.0 (blue) port on the Raspberry Pi. Device node: `/dev/video0`.
