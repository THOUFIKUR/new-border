# BorderPulse — ESP32 Setup Guide

> Complete guide: identify your board → wire the buzzer → flash firmware → connect to BorderPulse

---

## ⚠️ CRITICAL FIRST STEP — Identify Your ESP32 Variant

**Do not wire ANYTHING until you have identified your exact board.**  
Different ESP32 models have different GPIO capabilities, pinouts, and voltage limits.

---

### STEP 1 — Look at your board and find the chip markings

Flip your ESP32 board over and look for these markings on the chip:

| Marking on chip | Your board is |
|----------------|---------------|
| `ESP32-D0WD` or `ESP32-D0WDQ6` | ESP32 classic (most common) |
| `ESP32-S2` | ESP32-S2 (USB only, no Bluetooth) |
| `ESP32-S3` | ESP32-S3 (newer, dual-core) |
| `ESP32-C3` | ESP32-C3 (RISC-V, fewer GPIOs) |
| `ESP32-C6` | ESP32-C6 (newest, Zigbee capable) |

Also look at the **development board** label (usually on the top of the PCB):

| Label | Common board |
|-------|-------------|
| `NodeMCU-32S` or `NODEMCU-32` | ESP32 DevKit |
| `DOIT ESP32 DevKit v1` | DOIT DevKit |
| `ESP32-DevKitC` | Official Espressif DevKit |
| `FireBeetle ESP32` | DFRobot FireBeetle |
| `TTGO T-Display` | T-Display with screen |
| `Wemos D32` | Wemos/LOLIN D32 |

**Tell the next AI agent what board you have so GPIO pins can be confirmed.**

---

### STEP 2 — Count the pins

| Pins visible | Likely board |
|-------------|-------------|
| 30 pins (15 each side) | ESP32 DevKit v1 (DOIT) — 30-pin |
| 38 pins (19 each side) | ESP32 DevKit v4 or NodeMCU-32S — 38-pin |
| 40+ pins | ESP32-S3 or WROVER |

---

## WIRING — Buzzer Only (Minimum Required)

For the current BorderPulse prototype, **only the buzzer is required.**  
Radar and ground sensors are simulated in software.

### What you need:
- ✅ 1× Active buzzer (3.3V or 5V, check your buzzer's label)
- ✅ 1× 100Ω resistor (optional, protects GPIO if using 3.3V buzzer)
- ✅ Jumper wires (male-to-male or male-to-female)

### Active vs. Passive Buzzer

| Type | How to tell | Connection |
|------|-------------|-----------|
| **Active buzzer** (RECOMMENDED) | Has a built-in oscillator. Usually labeled "active" or has a circuit board on the bottom | Just GPIO HIGH = buzz |
| Passive buzzer | Requires PWM signal | More complex — use active buzzer for now |

---

## BUZZER WIRING (ESP32 DevKit v1 — 30-pin DOIT)

```
ESP32 GPIO25  ──────[100Ω resistor]──── BUZZER (+) positive leg
ESP32 GND     ─────────────────────────  BUZZER (-) negative leg
```

### Visual pinout (DOIT ESP32 DevKit v1, 30-pin):

```
                    ┌──────────────────────┐
                    │  [ USB ]             │
              GND  ─┤1                  30├─ VIN (5V)
              IO23 ─┤2                  29├─ GND
              IO22 ─┤3                  28├─ IO13
              IO1  ─┤4                  27├─ IO12
              IO3  ─┤5                  26├─ IO14
              IO21 ─┤6                  25├─ IO27
              IO19 ─┤7                  24├─ IO26
              IO18 ─┤8                  23├─ IO25  ◄── BUZZER (+) here
              IO5  ─┤9                  22├─ IO33
              IO17 ─┤10                 21├─ IO32
              IO16 ─┤11                 20├─ IO35
              IO4  ─┤12                 19├─ IO34
              IO2  ─┤13                 18├─ VN (IO39)
              IO15 ─┤14                 17├─ VP (IO36)
              GND  ─┤15  ◄── BUZZER (-)   16├─ EN
                    └──────────────────────┘
```

### Connection steps (Buzzer only):

1. Connect **ESP32 GPIO25** (pin 23 on DevKit) → **Buzzer (+) leg** (longer leg or "+" marked side)
2. Connect **ESP32 GND** (any GND pin) → **Buzzer (-) leg** (shorter leg or unmarked side)
3. Optionally put a 100Ω resistor between GPIO25 and the buzzer + leg

> If your buzzer is 5V (check the label), connect:
> - Buzzer (+) → ESP32 VIN (5V from USB)  
> - Add a transistor circuit (see HARDWARE_SETUP.md for transistor circuit)

---

## FIRMWARE SETUP

### Required Arduino IDE Libraries

Install these in Arduino IDE before compiling:

1. Open Arduino IDE
2. Go to **File → Preferences**
3. In "Additional boards manager URLs" add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Go to **Tools → Board → Boards Manager**
5. Search "esp32" and install **"esp32" by Espressif Systems**

### Configure the firmware

Open `esp32/firmware/borderpulse_esp32.ino` in Arduino IDE.

Find and edit these lines at the top:

```cpp
// ── USER CONFIGURATION ────────────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";       // ← Your Wi-Fi network name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";    // ← Your Wi-Fi password
const int   BUZZER_PIN    = 25;                      // ← GPIO pin for buzzer
// ─────────────────────────────────────────────────────────────────────────
```

> **Never commit WIFI_SSID or WIFI_PASSWORD to Git.**

### Flash the firmware

1. Connect ESP32 to your laptop via USB cable
2. In Arduino IDE:
   - **Tools → Board** → Select your board  
     (e.g., "ESP32 Dev Module" for DOIT DevKit)
   - **Tools → Port** → Select the COM port that appeared (e.g., COM5, COM6)
   - **Tools → Upload Speed** → 115200
3. Click the **Upload** button (→ arrow)
4. Watch the bottom console — wait for "Hard resetting via RTS pin..."
5. Open **Tools → Serial Monitor**, set baud rate to **115200**
6. You should see:

```
BorderPulse ESP32 v1.0 starting...
Connecting to WiFi: YOUR_NETWORK............
WiFi connected! IP: 192.168.1.105
BorderPulse ESP32 ready. Endpoints:
  GET  http://192.168.1.105/status
  GET  http://192.168.1.105/sensors
  POST http://192.168.1.105/alarm
  POST http://192.168.1.105/test/buzzer
HTTP server started on port 80
```

**Write down the IP address shown (e.g., 192.168.1.105).**

---

## CONNECT ESP32 TO BORDERPULSE

### Update your .env file

Open `d:\hackelite\.env` and set:

```
ESP32_IP=192.168.1.105
ESP32_PORT=80
```

Replace `192.168.1.105` with the IP shown on your ESP32's Serial Monitor.

### Restart the backend

```powershell
# Stop the running backend (Ctrl+C in its terminal)
# Then restart:
cd d:\hackelite
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### Verify connection

Open `http://localhost:5173/devices` in your browser.

You should see:
```
ESP32 ONLINE
IP: 192.168.1.105
Firmware: BorderPulse v1.0
```

### Test the buzzer

1. Go to `http://localhost:5173/devices`
2. Click **"Test Buzzer"** button
3. The buzzer should sound for ~1 second

---

## IMPORTANT NETWORK REQUIREMENT

The ESP32 and your laptop must be on the **same Wi-Fi network**.

```
Your Router (Wi-Fi)
├── Laptop (runs BorderPulse backend)  ← e.g. 192.168.1.10
└── ESP32 (runs HTTP server)           ← e.g. 192.168.1.105
```

If they cannot communicate, check:
- Same Wi-Fi SSID
- Windows Firewall allows Python on port 8000
- The ESP32 IP is not blocked by your router's client isolation setting

---

## GPIO NOTES FOR DIFFERENT BOARDS

> **DO NOT wire sensors until these GPIOs are confirmed for your specific board.**

| Pin | Purpose | Notes |
|-----|---------|-------|
| GPIO25 | Buzzer output | Confirmed safe for both DevKit v1 and v4 |
| GPIO26 | Future: Ground sensor input | Pull-down configuration needed |
| GPIO27 | Future: Radar OUT input | Pull-down configuration needed |
| GPIO34 | Future: Radar ADC | Input only — no pull-up/pull-down on ESP32 |
| GPIO35 | Future: Ground sensor ADC | Input only |

> GPIO25 is not available on ESP32-S2. If you have an S2, use GPIO13 instead.

---

## TROUBLESHOOTING

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| ESP32 not showing in COM ports | No driver | Install CP2102 or CH340 driver |
| Upload fails ("timed out") | Board selection wrong | Hold BOOT button during upload start |
| ESP32 not connecting to Wi-Fi | Wrong password or 5GHz network | ESP32 only supports 2.4GHz |
| Buzzer not sounding | Wrong pin or buzzer type | Test with `digitalWrite(25, HIGH)` in setup() |
| ESP32 shows IP but backend can't reach it | Firewall | Ensure both on same network, router has no client isolation |
| "ESP32 OFFLINE" in dashboard | Wrong IP in .env | Check Serial Monitor for correct IP |

---

## WHAT COMES NEXT (After Buzzer Works)

Once the buzzer is confirmed working:

1. **Radar sensor** (future): Wire to GPIO27, update `sensors/provider.py` to read GPIO via ESP32 `/sensors` endpoint
2. **Ground sensor** (future): Wire to GPIO26, same approach
3. Both sensor classes already have the interface in place — just switch `SENSOR_SIMULATION=false` in `.env`

---

## FULL SYSTEM FLOW WITH ESP32

```
Camera Frame
   ↓
YOLO detects person (confidence 0.85+)
   ↓
Bottom-center point enters restricted polygon
   ↓
Decision Engine: CRITICAL INTRUSION
   ↓
Evidence Capture: snapshot + 5s pre-buffer starts
   ↓
Event Manager creates event in Supabase
   ↓
ESP32 client POSTs to http://192.168.1.105/alarm
   ↓
ESP32 sounds buzzer (3 seconds)
   ↓
Dashboard shows RED ALERT
   ↓
8-second post-event video finalized
   ↓
Video + snapshot uploaded to Supabase Storage
   ↓
Operator acknowledges on dashboard
   ↓
ESP32 alarm stops
```
