# DhruvaScope ESP32 firmware

This directory contains the ESP32 network controller and the standalone
stepper diagnostic sketch.

## Confirmed GPIO configuration

The current hardware uses three DRV8825 motor drivers with shared control
signals:

| Function | ESP32 GPIO | Notes |
|---|---:|---|
| Driver ENABLE | 25 | Shared by all drivers, active LOW |
| RA STEP / DIR | 26 / 27 | First motor driver |
| DEC STEP / DIR | 14 / 13 | Second motor driver |
| FOCUS STEP / DIR | 18 / 19 | Third motor driver |
| M0 | 32 | Shared, LOW = full step |
| M1 | 33 | Shared, LOW = full step |
| M2 | 4 | Shared, LOW = full step |

The firmware currently reports AUX1 and AUX2 as unavailable because they do
not have assigned STEP/DIR wiring.

## DRV8825 power and control wiring

- `VMOT` connects to the external motor power supply, not to an ESP32 pin.
- Driver logic `VDD` must use the appropriate logic supply.
- ESP32 GND and every driver GND must be connected together.
- `RESET` and `SLEEP` should be tied together and pulled HIGH to the logic
  supply. Leaving them floating or LOW keeps the driver inactive.
- `FAULT` may remain unconnected for this test firmware.
- Never connect or disconnect a motor while `VMOT` is powered.

## Six-wire stepper motors

The four outer coil wires can be used with a DRV8825 as a bipolar motor. The
two center-tap wires must be insulated and left disconnected.

For the currently tested motor wiring:

```text
DRV8825 B2 -> red
DRV8825 B1 -> black
DRV8825 A1 -> green
DRV8825 A2 -> blue
white and yellow -> unused, insulated
```

Wire colors are not universal. Confirm the two coil pairs with a multimeter:
the center tap to either end has about half the resistance of the complete
coil. Do not use a center tap as a motor output.

## Network firmware

File: `dhruvascope_esp32/dhruvascope_esp32.ino`

The default build uses ESP32 access-point mode:

- Wi-Fi network: `DhruvaScope-ESP32-Test`
- ESP32 address: `192.168.4.1`
- TCP command port: `9999`

Connect the computer running Flask to the ESP32 network, then select Wi-Fi in
the control panel and use `192.168.4.1`.

To use router mode, change:

```cpp
#define WIFI_NETWORK_MODE WIFI_NETWORK_STA
```

Upload the firmware and use the IP printed by the Serial Monitor. Keep router
credentials local; do not commit them to a public repository.

## Serial debugging

Open Serial Monitor at `115200 baud`. The firmware prints received commands,
for example:

```text
[RX WiFi] {"v":1,"id":3,"cmd":"MOVE","motor":"RA","direction":"POS","speed":0.03}
MOVE RA POS 0.030 deg/s (continuous until STOP)
```

`MOVE` continues until a `STOP` command is received.

## Standalone motor test

File: `stepper_diagnostic/stepper_diagnostic.ino`

Upload this sketch instead of the network firmware to test the drivers
without Wi-Fi or Flask. Open Serial Monitor at `115200 baud`:

| Command | Test |
|---|---|
| `r` / `R` | RA, positive / negative |
| `d` / `D` | DEC, positive / negative |
| `f` / `F` | FOCUS, positive / negative |
| `x` | Disable shared driver enable |

The diagnostic uses a slow ramp to reduce stepper stalling. Start without a
mechanical load and set the driver current limit conservatively.
