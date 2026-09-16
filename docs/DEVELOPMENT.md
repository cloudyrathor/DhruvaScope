# Development Guide

Development is milestone-based.

## Milestone 0
Project skeleton, configuration, logging, motor model, telescope state,
device interface, mock device, and tests.

## Milestone 1
Flask API and HTML5 control panel.

## Milestone 2
Five-channel manual motor control.

## Milestone 3
Versioned serial protocol and ESP32 single-axis control.

## Milestone 5 — Equatorial tracking

The first M5 slice implements host-side sidereal-rate tracking for the RA axis.
`SiderealTracker` uses the existing `TelescopeDevice` abstraction and does not
contain astronomy catalogue, Moon, planetary, GoTo, or database logic.

Available API endpoints:

- `GET /api/tracking`
- `POST /api/tracking/sidereal/start`
- `POST /api/tracking/stop`

The default sidereal rate is `15.041067 / 3600` degrees per second. Hardware
validation remains pending until the ESP32 rate, position, and safety behavior
are verified under load.

## Milestone 6 — Astronomical target calculations

The first M6 slice adds an Astropy-backed coordinate workflow for fixed
equatorial targets. It accepts target RA/DEC, observer latitude/longitude/
elevation, UTC observation time, and equatorial mount configuration. It returns
apparent RA/DEC plus local altitude, azimuth, and horizon visibility.

The endpoint is `POST /api/astronomy/target`. This slice does not query SIMBAD,
VizieR, or Gaia, and does not implement SQLite persistence, Moon/planetary
ephemerides, GoTo, or plate solving.

## M6.5 — Open-loop tracking hardening

M6.5 adds the target-calculation panel, a reusable `MotionController`, and
dynamic signed RA/DEC rate updates through `POST /api/tracking/rates`. The
minimum hardware path uses software enable/speed checks and continuous STEP/DIR
control only. Encoders and position sensors are optional and are not required
by any firmware or host module. The target panel displays a live local/UTC
clock and refreshes the default observation time every second until the user
edits it.

The target panel also uses the offline starter catalog at
`GET /api/catalog/objects`. Selecting an entry fills its fixed RA/DEC values;
this is target selection and calculation only, not GoTo or motor tracking.
The `Visible now` filter applies the observer location and observation time to
the local catalog and sorts matching objects by altitude. It currently covers
the bundled fixed-object catalog; external SIMBAD/VizieR/Gaia expansion will
use the same visibility contract.
The dropdown also includes dynamically calculated Sun, Moon, and planetary
entries when observer location and observation time are supplied; these are
never stored as fixed catalog coordinates.
The UI renders entries as structured options and keeps the selected object in
the loaded catalog cache, avoiding a second lookup when the dropdown changes.
The catalog selector and `Visible now` checkbox use separate layout rules so
they remain readable on narrow and wide screens.

## M6.6 — Mount alignment and position model

M6.6 adds an open-loop mount alignment reference. After manually pointing the
telescope at the selected object, use **Set current position** to store its
RA/DEC in host state. This does not move motors and does not require encoders;
it establishes the reference needed by the future GoTo milestone.

## Milestone 7 — Moon tracking

The first M7 slice calculates the Moon's topocentric apparent RA/DEC,
altitude, azimuth, and distance through `POST /api/astronomy/moon`. The UI
provides a Moon position preview using the observer settings and observation
time from the M6.5 panel. This slice does not start motors or implement
periodic Moon rate updates yet.

Do not skip milestones.

## Milestone 8 — Camera / OpenCV

The first M8 slice adds a hardware-independent `Camera` interface, a
`MockCamera`, and an `OpenCVCamera` adapter. The Flask API supports camera
open/close/status, JPEG capture with JSON metadata sidecars, and an MJPEG
preview stream. The control panel exposes the mock-camera workflow so it can
be tested without physical hardware. Camera code remains separate from motor
and astronomy services.

## Milestone 9 — GoTo planning

The first M9 slice adds `POST /api/goto/plan`. It uses the M6.6 manually stored
RA/DEC reference to calculate the shortest signed RA delta and DEC delta for a
selected target. Planning is hardware-safe and does not move motors; GoTo
execution requires a later slice with mount limits, speed profiles, and an
explicit execution command.

## Milestone 10 — Visual Tracker manual calibration

The first M10 slice adds a UI Visual Tracker mode with optional live camera
assistance, four-direction manual nudge controls, release-to-stop behavior,
and up to three manually confirmed reference objects. The operator may use an
eyepiece alone; confirming a reference stores the selected object's coordinates
as the current open-loop alignment. Automatic image recognition and closed-loop
correction remain future M12/M13 work.

Visual Tracker also provides a separate next-target selector and a safe
prepare action that calculates the target RA/DEC offsets without moving motors.

## Milestone 11 — Telescope calibration

Calibration mode is separate from one-reference positioning. It records up to
six known reference objects and the signed duration of RA/DEC manual nudges
between them, then estimates degrees-per-second scale values for each axis.
The estimate is a starting calibration and must be validated on the physical
mount; backlash, polar alignment, and timing latency can affect accuracy.
