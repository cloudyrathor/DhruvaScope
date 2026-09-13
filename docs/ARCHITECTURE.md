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

## M5 tracking boundary

Sidereal tracking is initiated by the host `SiderealTracker` service. It sends
the RA direction and sidereal rate through `TelescopeDevice`; it does not drive
GPIO or generate individual step pulses. The device remains responsible for
low-level pulse generation, limits, and emergency stop behavior.

The M5 implementation is intentionally limited to sidereal RA tracking. Object
providers, SQLite catalog persistence, Astropy coordinate calculations, and
Moon/planetary tracking belong to later milestones.

## M6 astronomy boundary

The M6 `AstronomyService` accepts a fixed ICRS RA/DEC target and observer
location, then uses Astropy to calculate apparent equatorial and horizontal
coordinates. It is a calculation service only; it does not access providers,
the database, or device GPIO. Provider and local-catalog integration remains a
later Object Service concern.

## M6.5 hardware independence

The motion boundary is open-loop capable. `MotionController` validates motor
enable state and software speed limits, then delegates movement and rate
updates to `TelescopeDevice`. Firmware generates STEP/DIR pulses without
requiring encoder or position feedback. Feedback may be added as an optional
telemetry capability later; it must not become a prerequisite for UI movement,
sidereal tracking, or safety stop commands.

## M7 Moon boundary

`MoonService` owns Moon ephemeris calculation and returns a position solution.
It has no dependency on `MotionController`, `TelescopeDevice`, or firmware.
The first M7 UI/API slice is calculation-only; motor tracking will be added
after position refresh and rate-conversion behavior are validated.
