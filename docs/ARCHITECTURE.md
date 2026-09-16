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

The catalog endpoint is local and offline-first. External providers can later
extend it without changing the UI selection contract.

## M9 GoTo boundary

`GoToPlanner` consumes the open-loop M6.6 alignment reference and produces a
shortest-path RA delta plus a DEC delta. The M9 planning endpoint does not
command `TelescopeDevice`; motor execution remains a later safety-gated slice.

## M6.6 alignment boundary

Mount alignment is stored in host `TelescopeState` as an open-loop RA/DEC
reference. It is deliberately independent of firmware feedback and does not
claim that the motor position is measured. GoTo may use this reference later;
M6.6 itself only records the manually established coordinate.

## M10 Visual Tracker boundary

Visual Tracker mode is currently a manual, camera-optional calibration surface.
The browser sends bounded RA/DEC jog commands while an arrow is held and sends
a stop on release. Confirmed objects are stored as alignment references; no
camera, encoder, position sensor, computer-vision detection, or autonomous
correction is required or performed yet.

## M11 calibration boundary

Calibration mode logs browser-side manual nudge durations and associates them
with manually confirmed catalog coordinates. It estimates independent RA/DEC
scale values without requiring encoders. These values are advisory until
validated and persisted as a mount configuration; calibration does not alter
normal one-reference positioning automatically.
