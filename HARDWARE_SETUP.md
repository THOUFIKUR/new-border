# BorderPulse — Hardware Setup Guide

> Complete hardware reference: camera, ESP32, buzzer, future sensors

---

## Overview of Hardware Components

| Component | Required Now | Future | Purpose |
|-----------|-------------|--------|---------|
| Laptop webcam | ✅ | — | Primary camera — YOLO detection |
| ESP32 DevKit | ✅ | — | Wi-Fi controller + buzzer driver |
| Active buzzer (3.3V) | ✅ | — | Audible alarm |
| 100Ω resistor | Recommended | — | GPIO protection |
| Radar module | ❌ | ✅ | Motion/presence evidence |
| Ground vibration sensor | ❌ | ✅ | Physical disturbance evidence |

> Radar and ground sensor are **simulated in software** until hardware is wired and verified.

---

## Camera Setup

### Laptop Webcam (Current)
- No wiring needed
- Connected via USB or built-in
- BorderPulse uses OpenCV index `CAMERA_INDEX=0` (default)
- Detected at 1280×720 resolution
- If you have multiple cameras, change `CAMERA_INDEX` in `.env`

### External USB Camera
- Plug in before starting backend
- Check `CAMERA_INDEX=1` or `2` if built-in camera takes index 0
- Test: `python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.read()[0])"`

---

## ESP32 Hardware

### Recommended Board: DOIT ESP32 DevKit v1 (30-pin)

This is the most common ESP32 development board. If you have a different board, see the variant table in `ESP32_SETUP.md`.

### Full Pinout (DOIT ESP32 DevKit v1)

```
                            ┌─────────────┐
                            │   USB Port  │
     3.3V (power output) ───┤ 3V3   GND  ├─── GND
                        EN ─┤ EN    IO23 ├─── IO23
        Sensor VP (input) ──┤ VP    IO22 ├─── IO22 
        Sensor VN (input) ──┤ VN    TX0  ├─── IO1/TX
                     IO34 ──┤ IO34  RX0  ├─── IO3/RX
                     IO35 ──┤ IO35  IO21 ├─── IO21
                     IO32 ──┤ IO32  IO19 ├─── IO19
                     IO33 ──┤ IO33  IO18 ├─── IO18
    BUZZER (+) ──── IO25  ──┤ IO25  IO5  ├─── IO5
                     IO26 ──┤ IO26  IO17 ├─── IO17
      Future:GND_SENSOR ───┤ IO27  IO16 ├─── IO16
                     IO14 ──┤ IO14  IO4  ├─── IO4
                     IO12 ──┤ IO12  IO0  ├─── IO0
                     IO13 ──┤ IO13  IO2  ├─── IO2
   (UART2) TX       IO9  ──┤ GND   IO15 ├─── IO15
                      5V ──┤ VIN   GND  ├─── GND ─── BUZZER (-)
                            └─────────────┘
```

---

## Buzzer Wiring (Step by Step)

### Parts Needed
- Active buzzer (3.3V DC, two-pin, with built-in oscillator)
- 1× 100Ω resistor
- 2× jumper wires

### Wiring Diagram

```
ESP32 GPIO25 ──────┤100Ω├──────── BUZZER (+) [longer pin / marked +]
ESP32 GND    ─────────────────── BUZZER (-)  [shorter pin / unmarked]
```

### Physical Steps

```
Step 1: Insert ESP32 into a breadboard (straddle the center gap)

Step 2: Find GPIO25
        - On DOIT DevKit v1 (30-pin): it's the 8th pin from TOP on the RIGHT side
        - Labeled "IO25" or "25" on the silkscreen

Step 3: Insert 100Ω resistor
        - One leg into the row connected to GPIO25
        - Other leg into an open row

Step 4: Connect buzzer (+) to the other leg of the resistor

Step 5: Connect buzzer (-) to any GND pin on the ESP32
        - GND pins: bottom-left, or any pin labeled GND

Step 6: Double-check NO shorts, then plug in USB
```

### How to identify active buzzer polarity

```
Active Buzzer looks like:

   Top view:           Bottom view:
   ┌──────┐           ┌──────┐
   │  ●   │           │ PCB  │   ← Has circuit board = ACTIVE buzzer
   └──────┘           └──────┘
    
   + pin = longer leg (or marked with +)
   - pin = shorter leg
```

---

## 5V Buzzer Wiring (if your buzzer needs 5V)

If your buzzer label says "5V" or "DC 5V":

```
ESP32 GPIO25 ─────────── NPN transistor BASE (via 1kΩ resistor)
ESP32 GND    ─────────── NPN transistor EMITTER
                         NPN transistor COLLECTOR ─── BUZZER (-)
ESP32 VIN (5V USB) ──── BUZZER (+)

Recommended transistor: BC547, 2N2222, or S8050
```

**For the prototype, use a 3.3V active buzzer to avoid this complexity.**

---

## Future Sensor Wiring (DO NOT WIRE YET)

These sections describe wiring for Phase 2 hardware integration.  
**Radar and ground sensor GPIO assignments are PROVISIONAL until your exact sensor models are confirmed.**

### Future: Radar Sensor

> Do not wire until you have confirmed: exact radar model, output type (GPIO or UART), and voltage.

```
Common radar modules (e.g., RCWL-0516, LD2410):
- RCWL-0516 output: 3.3V logic HIGH when motion detected → safe for GPIO27
- LD2410: UART output → connect to ESP32 RX2 (GPIO16)

Provisional wiring for RCWL-0516:
  Radar VCC ─── ESP32 VIN (5V) or 3.3V depending on module
  Radar GND ─── ESP32 GND
  Radar OUT ─── ESP32 GPIO27
```

### Future: Ground Vibration Sensor

> Do not wire until confirmed exact model (SW-420, MPU-6050, etc.)

```
SW-420 (simple tilt/vibration switch):
  Sensor VCC ─── ESP32 3.3V
  Sensor GND ─── ESP32 GND
  Sensor DO  ─── ESP32 GPIO26 (digital output, active HIGH)

MPU-6050 (accelerometer, I2C):
  MPU VCC ─── ESP32 3.3V
  MPU GND ─── ESP32 GND
  MPU SDA ─── ESP32 GPIO21 (I2C SDA)
  MPU SCL ─── ESP32 GPIO22 (I2C SCL)
```

---

## Power Requirements

| Component | Power Source | Voltage | Current |
|-----------|-------------|---------|---------|
| ESP32 DevKit | USB 5V from laptop | 5V | ~240mA max |
| Active buzzer (3.3V) | GPIO25 directly | 3.3V | ~20-30mA |
| Active buzzer (5V) | VIN pin | 5V | ~30-100mA |
| RCWL-0516 radar | VIN (5V) | 5V | ~3mA |
| SW-420 ground sensor | 3.3V | 3.3V | ~1mA |

> ESP32 GPIOs can supply **max 40mA per pin** and **total 1200mA** for all GPIOs combined.  
> Always use a resistor with a directly-driven buzzer.

---

## GPIO Safety Rules

1. **Never connect 5V directly to an ESP32 GPIO** — GPIOs are 3.3V tolerant only
2. **Do not short two GPIOs together** without a resistor
3. **Never exceed 40mA on any single GPIO**
4. **IO34, IO35, IO36, IO39** are input-only — no internal pull-up/down, cannot be used as outputs
5. **IO0, IO2, IO12, IO15** are boot-mode pins — avoid connecting to sensors that pull them low at boot

---

## Complete Connection Summary (Current Phase)

```
LAPTOP
  └── USB → ESP32 (power + programming)

ESP32
  ├── GPIO25 → [100Ω resistor] → Buzzer(+)
  ├── GND → Buzzer(-)
  └── Wi-Fi → Your Router → Laptop (BorderPulse backend)

LAPTOP
  └── Built-in webcam → OpenCV → YOLO → BorderPulse backend
```

---

## What the Next AI Agent Needs to Know

When you move to the next AI session, tell it:

1. **Exact ESP32 board model** (look at PCB silkscreen)
2. **Buzzer voltage** (3.3V or 5V)
3. **IP address** assigned to ESP32 (from Serial Monitor)
4. **Future radar model** (if purchased)
5. **Future ground sensor model** (if purchased)
6. That the **provisional GPIO map is GPIO25=Buzzer, GPIO26=Ground, GPIO27=Radar, GPIO34=RadarADC**
7. That the map must be **confirmed and not assumed**
