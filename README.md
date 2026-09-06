# DhruvaScope

A modular, open-source telescope automation framework for equatorial mounts.

DhruvaScope provides an HTML5/Flask control panel for controlling RA, DEC,
focus, and auxiliary motors, with support planned for ESP32, Arduino, and
Raspberry Pi.

The framework is designed to grow from basic motor control into:

- Autonomous telescope tracking
- Celestial object selection
- Camera streaming
- Automated image capture
- Observation sessions
- Image stacking
- Multiple controller platforms

## Current Status

🚧 Early development

The first milestone focuses on the software architecture and simulated
hardware before connecting real telescope motors.

## Planned Hardware

- ESP32
- Arduino
- Raspberry Pi


## Initial Mount

The first supported mount type is:

**Equatorial Mount**

Initial motor channels:

- RA / X
- DEC / Y
- Focus
- AUX1
- AUX2

## Technology

- Python
- Flask
- HTML5
- JavaScript
- OpenCV
- Serial communication

## License

MIT License
