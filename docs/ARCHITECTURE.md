# DhruvaScope Architecture

Host:
- Flask
- HTML5/JavaScript
- telescope state
- motion service
- tracking
- OpenCV
- configuration

Device:
- motor control
- low-level safety
- telemetry
- heartbeat

The host communicates with hardware through a device interface and transport
interface. Board-specific GPIO code must remain outside Flask routes.
