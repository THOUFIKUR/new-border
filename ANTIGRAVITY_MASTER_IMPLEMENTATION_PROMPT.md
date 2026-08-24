# ANTIGRAVITY MASTER IMPLEMENTATION PROMPT

## Mission

You are the primary implementation and testing agent for the AI-based multi-sensor restricted-area security and intrusion-detection prototype.

Use:
1. `01_MASTER_PROJECT_SPECIFICATION.pdf` as the engineering source of truth.
2. `02_UI_UX_FIGMA_STITCH_HANDOFF.pdf` and the connected Stitch/Figma project as the visual source of truth.
3. `03_SYSTEM_VALIDATION_AND_TEST_PLAN.pdf` as the acceptance/test source of truth.
4. The connected Supabase project as the database/storage source of truth.
5. Any Claude review document as architectural review guidance, not as a competing implementation.

Build a real working prototype, not a static mockup.

## Current target

Windows laptop + built-in camera + YOLO + polygon restricted zone + ESP32-S development board + buzzer + Supabase.

Radar and ground sensors are not physically available yet. Implement them through clearly labelled simulation controls.

Future target:
Raspberry Pi 5 + camera + real radar + real ground/vibration sensor + optional environment sensor.

## Required engineering rules

- Do not use a strict camera AND radar AND ground rule for every alarm.
- RCWL-0516 is motion/presence evidence, not a coordinate/identity sensor.
- Normal YOLO object detection does not prove fighting or abnormal behaviour.
- Use tracking, temporal rules and measurable activity analytics; leave a plugin interface for a future behaviour model.
- Do not store large videos in PostgreSQL; use Supabase Storage.
- Do not block camera/UI processing on YOLO, database calls, video encoding or cloud uploads.
- Never hard-code secrets.
- Never put a Supabase service-role secret in the frontend.
- Never apply a 5 V signal directly to an ESP32 GPIO.
- Verify the exact ESP32 chip/board before physically wiring sensors.

## Software architecture

Camera capture -> bounded frame queue -> YOLO -> tracking -> restricted-zone engine -> activity/camera-health analytics -> sensor state -> temporal fusion -> decision engine -> alerts/evidence -> Supabase -> UI.

Use provider interfaces so the runtime can switch between laptop and Raspberry Pi without rewriting the decision engine.

## AI

Initial model: Ultralytics YOLO11n or compatible.

Support pretrained COCO classes including person, bird, common animals and vehicles.

Use ByteTrack or supported Ultralytics tracking.

For a person:
- high confidence (default >= 0.85) + inside restricted polygon => immediate critical intrusion;
- otherwise use configurable temporal confirmation and sensor evidence.

Do not call grouping/fighting an actual fight without a dedicated behaviour model.

## Restricted zone

Use an editable polygon.

Operator:
1. opens Live Monitor;
2. selects Configure Zone;
3. clicks 3+ vertices;
4. finishes polygon;
5. names and saves zone;
6. enables/disables zone.

Store normalized 0–1 coordinates.

Use the tracked person's bottom-center/foot point for point-in-polygon intrusion testing.

## Evidence

Use a 3–5 second rolling pre-event buffer.

On critical trigger:
PREBUFFER -> SNAPSHOT -> CONTINUE RECORDING -> FINALIZE CLIP -> UPLOAD -> DATABASE METADATA.

Default post-event duration: 5–10 seconds.

For the laptop webcam, digital crop/zoom is allowed; never claim optical/PTZ movement. Create a PTZ abstraction for future hardware.

## ESP32

ESP32 controls the buzzer, reads future sensors, reports health and receives alarm commands.

Preferred communication: Wi-Fi + HTTP REST.

Implement:
GET /api/status
GET /api/sensors
POST /api/buzzer
POST /api/config

Implement heartbeat and explicit ESP32 OFFLINE state.

Pin mappings must be configurable and board-verified before wiring. Earlier project material contains different provisional maps for classic ESP32 and ESP32-S3, so do NOT blindly wire from a generic table. Inspect the exact board/chip and freeze the correct pin map in `HARDWARE_SETUP.md`.

## Supabase

Use the already connected project.

Inspect schema before modification.

Expected project tables include:
devices
cameras
zones
sensor_readings
detections
events
event_media
camera_health
system_settings

Use private storage buckets such as:
event-images
event-videos
event-clips

Store media in Storage and metadata in Postgres.

Keep RLS enabled.

## Frontend

Use React + Vite + TailwindCSS.

Use Stitch/Figma design directly.

Required pages:
Overview
Live Monitor
Events
Event Details
Zones
Sensors
Devices
Camera Health
Analytics
Settings

Live Monitor must show:
live camera
bounding boxes
labels
confidence
track IDs
restricted polygon
sensor states
decision state
FPS/latency diagnostics

## Performance

Separate:
camera capture
inference
UI rendering
recording
uploads

Use bounded queues and drop stale frames under overload.

Never allow cloud/database operations to freeze the camera.

## Simulation

Provide controls:
Radar OFF/ON
Ground OFF/ON
Rain OFF/ON

Clearly label SIMULATED versus REAL HARDWARE.

## Environment

Create `.env.example` and `.gitignore`.

Include configurable values for:
Supabase URL/key
ESP32 IP/port
camera index
YOLO model/confidence/image size
runtime mode
sensor simulation
pre/post event duration
cooldown
temporal frame/window thresholds

Never commit `.env`.

## Testing

Run the application. Do not merely generate files.

Test:
camera
YOLO
tracking
polygon zone
temporal confirmation
event creation
snapshot
video
Supabase insertion
Storage upload
ESP32 communication
buzzer
sensor simulation
failure recovery
performance

Use `03_SYSTEM_VALIDATION_AND_TEST_PLAN.pdf`.

## Documentation

Create:
README.md
ARCHITECTURE.md
HARDWARE_SETUP.md
SOFTWARE_SETUP.md
ESP32_SETUP.md
SUPABASE_SETUP.md
TESTING.md
TROUBLESHOOTING.md
RASPBERRY_PI_MIGRATION.md
PROJECT_STATE.md

## Continuation

After every major phase update `PROJECT_STATE.md` with:
- current phase
- implemented features
- tested features
- failures
- current errors
- configuration
- files changed
- next task
- known limitations

If a new chat starts, read `PROJECT_STATE.md` before doing anything else and continue from the recorded phase. Do not restart or recreate completed work.

## First implementation sequence

1. Inspect workspace, connected Supabase and connected Figma/Stitch.
2. Do not delete useful existing work.
3. Build UI shell.
4. Implement camera.
5. Implement YOLO.
6. Implement tracking.
7. Implement polygon zone editor.
8. Implement decision/event state machine.
9. Implement evidence capture.
10. Integrate Supabase.
11. Integrate ESP32/buzzer.
12. Add sensor simulation.
13. Run complete acceptance tests.
14. Document exact setup and remaining limitations.
15. Prepare Raspberry Pi migration abstraction.

Before saying DONE, show:
project tree, install commands, run commands, `.env.example`, verified ESP32 pin table, firmware, API, frontend URL, Supabase tables/buckets, zone procedure, tests, troubleshooting, working features, simulated features and future hardware requirements.
ANTIGRAVITY INPUTS
│
├── 1. MASTER PROJECT PROMPT
│
├── 2. Existing project/workspace
│
├── 3. Stitch/Figma design
│
├── 4. Supabase connected project
│
├── 5. ESP32 hardware photos
│
├── 6. Existing GitHub/project code if available
│
└── 7. Claude review document



============================================================
ANTIGRAVITY MASTER IMPLEMENTATION PROMPT
============================================================

PROJECT NAME:

AI-BASED MULTI-SENSOR RESTRICTED-AREA SECURITY,
INTRUSION DETECTION AND EDGE-AI MONITORING SYSTEM

============================================================
ROLE
============================================================

You are the PRIMARY IMPLEMENTATION AGENT for this project.

You are responsible for:

- inspecting the existing workspace
- understanding the project requirements
- implementing the frontend
- implementing the backend
- implementing YOLO vision
- implementing camera processing
- implementing restricted-zone logic
- implementing object tracking
- implementing temporal confirmation
- implementing sensor fusion
- implementing ESP32 communication
- implementing ESP32 firmware
- implementing event management
- implementing evidence capture
- integrating Supabase
- integrating Supabase Storage
- implementing testing
- fixing errors
- writing documentation
- preparing the system for future Raspberry Pi deployment

Do NOT create a toy/demo application.

Build a modular working prototype.

The FIRST working target is:

WINDOWS LAPTOP
+
LAPTOP BUILT-IN CAMERA
+
YOLO
+
RESTRICTED POLYGON
+
ESP32
+
BUZZER
+
SUPABASE

Radar and ground sensors are currently unavailable.

Therefore they must initially operate through SENSOR SIMULATION.

The architecture must allow the real sensors to be connected later without rewriting the application.

============================================================
IMPORTANT SOURCE-OF-TRUTH RULE
============================================================

You may receive information from:

1. This master prompt
2. Existing project files
3. Figma/Stitch UI design
4. Existing Supabase project
5. Existing code
6. Claude architecture/review documents

Priority:

ENGINEERING REQUIREMENTS:
Master project specification

VISUAL DESIGN:
Figma/Stitch design

DATABASE:
Existing Supabase schema

IMPLEMENTATION:
Actual working code and tests

Do NOT independently redesign the project unless required to fix
a technical problem.

If you discover a contradiction:

STOP and identify the contradiction.

Do not silently choose an arbitrary interpretation.

============================================================
AVAILABLE CONNECTED SERVICES
============================================================

The following services may already be connected:

FIGMA / STITCH
SUPABASE

Use the existing connections.

Do NOT create duplicate services.

Do NOT create another Supabase project.

Do NOT recreate an existing database blindly.

First inspect the current project and Supabase schema.

============================================================
CURRENT HARDWARE
============================================================

Available now:

1. Windows laptop
2. Laptop built-in camera
3. ESP32-S development board
4. Buzzer

Not currently available:

1. Raspberry Pi 5
2. Radar sensor
3. Ground sensor
4. PTZ camera
5. IR camera

Therefore:

RUNTIME_MODE=laptop

SENSOR_SIMULATION=true

============================================================
FUTURE HARDWARE
============================================================

Future system:

USB/CSI Camera
       ↓
Raspberry Pi 5
       ↓
YOLO / Vision
       ↓
Tracking
       ↓
Restricted Zone
       ↓
Decision Engine
       ↓
ESP32
       ↓
Radar + Ground Sensor + Buzzer

The architecture must support:

RUNTIME_MODE=laptop

and

RUNTIME_MODE=raspberry_pi

============================================================
IMPORTANT SENSOR PRINCIPLE
============================================================

Do NOT incorrectly describe:

RADAR = HUMAN DETECTOR

RADAR only provides motion/presence evidence.

GROUND SENSOR does not identify a human.

GROUND SENSOR provides local physical/contact evidence.

YOLO provides object classification.

The decision engine combines evidence.

============================================================
VISION
============================================================

Use an Ultralytics YOLO model.

Initial model:

YOLO11n or compatible current Ultralytics model.

Model path must be configurable.

Example:

models/yolo11n.pt

Initial relevant classes:

person
bird
cat
dog
horse
sheep
cow
elephant
bear
zebra
giraffe
car
motorcycle
bus
truck
bicycle

Do not claim pretrained COCO YOLO can identify arbitrary:

fighting
military combat
suspicious behavior
specific tactical activity

For group activity:

Implement measurable analytics such as:

- multiple people in same zone
- people proximity
- crowding
- loitering
- repeated entry
- rapid movement

These must be labelled as:

GROUP ACTIVITY
ABNORMAL ACTIVITY

not automatically:

FIGHTING

A dedicated action-recognition model can be added later.

============================================================
CAMERA
============================================================

Current camera:

Laptop built-in camera.

Use OpenCV.

Camera capture must run independently from:

YOLO inference
database operations
file writing
Supabase uploads
frontend communication

Architecture:

Camera Thread
      ↓
Bounded Frame Queue
      ↓
Inference Worker
      ↓
Detection Queue
      ↓
Decision Engine
      ↓
Frontend / ESP32

Never allow unlimited frame queues.

If inference is slower than capture:

drop old frames.

Always prioritize the latest frame.

============================================================
OBJECT TRACKING
============================================================

Use ByteTrack or the tracking mechanism supported by the selected
Ultralytics version.

Each detection should contain:

class
confidence
bounding box
track_id
timestamp

Do not treat every frame as a new object.

============================================================
RESTRICTED ZONE
============================================================

Restricted areas MUST be polygon-based.

Do NOT restrict the system to rectangles.

Operator workflow:

1. Open Live Monitor
2. Click Configure Zone
3. Click points on camera image
4. Draw polygon
5. Finish
6. Name zone
7. Save
8. Enable zone

Support:

Create
Edit
Delete
Enable
Disable
Rename

Store normalized coordinates:

0.0 - 1.0

Example:

[
  {"x":0.12,"y":0.18},
  {"x":0.78,"y":0.15},
  {"x":0.92,"y":0.72},
  {"x":0.30,"y":0.90}
]

This allows camera resolution changes.

============================================================
ZONE DETECTION
============================================================

For each detected person:

calculate bounding box.

Use:

bottom-center point of bounding box

as the approximate ground/contact point.

Then perform:

POINT-IN-POLYGON

If inside:

person_inside_zone = TRUE

Do not simply check full bounding-box overlap.

============================================================
CRITICAL HUMAN LOGIC
============================================================

Human detection inside restricted zone is highest priority.

Default:

HUMAN_HIGH_CONFIDENCE = 0.85

If:

person confidence >= 0.85

AND

person is inside restricted zone

THEN:

IMMEDIATE CRITICAL INTRUSION

Actions:

1. ESP32 buzzer ON
2. Dashboard critical alert
3. Snapshot
4. Video evidence
5. Supabase event
6. Event timeline
7. Evidence metadata

Do NOT require radar or ground confirmation in this case.

============================================================
NORMAL / LOW CONFIDENCE LOGIC
============================================================

For lower-confidence person detections:

Use:

YOLO
+
Radar
+
Ground
+
Temporal confirmation

Do not blindly calculate a simple average.

Implement an evidence/fusion score.

Initial configurable weights:

vision = 0.55
radar = 0.20
ground = 0.15
temporal = 0.10

These are engineering starting values.

Clearly mark them as:

CONFIGURABLE
NOT SCIENTIFICALLY VALIDATED

============================================================
TEMPORAL CONFIRMATION
============================================================

Do not trigger normal alerts from a single frame.

Default:

minimum_frames = 3

window = 1 second

Track the same object across frames.

Possible state:

NO_DETECTION
      ↓
POSSIBLE_DETECTION
      ↓
TEMPORAL_CONFIRMATION
      ↓
CONFIRMED
      ↓
ALARM_ACTIVE
      ↓
EVIDENCE_CAPTURE
      ↓
EVENT_ACTIVE
      ↓
EVENT_RESOLVED

Also support:

FALSE_POSITIVE

============================================================
EVENT COOLDOWN
============================================================

Default:

10 seconds

Do not create hundreds of events for one continuous intrusion.

One continuous intrusion should remain one event.

============================================================
NON-HUMAN OBJECTS
============================================================

Animal:

dashboard event

Bird:

dashboard event

Vehicle:

dashboard event

Default:

NO BUZZER

unless configured otherwise.

============================================================
CAMERA HEALTH
============================================================

Monitor:

camera online/offline
brightness
blur
contrast
visibility
FPS
resolution
last frame

Possible statuses:

HEALTHY
WARNING
DARK
BLURRED
BLOCKED
LOW_VISIBILITY
OFFLINE

Do not falsely claim perfect rain/fog detection.

Use image-quality indicators.

Rain/fog classification should be marked:

EXPERIMENTAL

unless a dedicated model is added.

============================================================
PTZ
============================================================

Current laptop camera is fixed.

Do NOT fake PTZ movement.

Create abstraction:

CameraController

Methods:

zoom_in()
zoom_out()
pan()
tilt()
focus()

For laptop:

return:

PTZ_NOT_SUPPORTED

Future PTZ camera can implement these methods.

============================================================
EVIDENCE CAPTURE
============================================================

When confirmed intrusion occurs:

capture:

1. pre-event frames
2. trigger snapshot
3. post-event frames
4. video clip
5. event metadata

Default:

pre_event_seconds = 5
post_event_seconds = 8

Use circular frame buffer.

Do not continuously write every frame to disk.

============================================================
ESP32
============================================================

ESP32 responsibilities:

1. Read future radar
2. Read future ground sensor
3. Read optional environment sensor
4. Control buzzer
5. Send sensor state
6. Receive alarm commands
7. Report health

ESP32 does NOT run YOLO.

============================================================
ESP32 PIN PLAN
============================================================

Initial provisional mapping:

GPIO25 → BUZZER

GPIO26 → GROUND SENSOR

GPIO27 → RADAR OUT

GPIO34 → OPTIONAL ANALOG / ENVIRONMENT INPUT

IMPORTANT:

These are configurable provisional mappings.

Before physical connection verify the actual sensor module.

Never connect a 5V signal directly to an ESP32 GPIO.

ESP32 GPIO logic is 3.3V.

All devices must share common ground where electrically appropriate.

GPIO34 is input-only on standard ESP32.

============================================================
ESP32 COMMUNICATION
============================================================

Preferred prototype:

ESP32 Wi-Fi + HTTP REST

API:

GET /status

GET /sensors

POST /alarm

POST /alarm/stop

POST /test/buzzer

POST /sensor/config

Example:

POST /alarm

{
  "active": true,
  "reason": "human_intrusion",
  "duration_ms": 5000
}

If ESP32 is disconnected:

VISION SYSTEM MUST CONTINUE RUNNING.

Dashboard:

ESP32 OFFLINE

============================================================
SENSOR SIMULATION
============================================================

Create simulation controls.

Radar:

OFF
ON

Ground:

OFF
ON

Rain:

OFF
ON

Simulation must be visually different from real hardware.

Example:

SIMULATED

When actual sensor is connected:

REAL HARDWARE

============================================================
SUPABASE
============================================================

Use the EXISTING connected Supabase project.

DO NOT create another project.

First inspect:

tables
columns
relationships
RLS
storage
policies

Existing expected tables:

devices
cameras
zones
sensor_readings
detections
events
event_media
camera_health
system_settings

Do not recreate tables without checking first.

============================================================
SUPABASE STORAGE
============================================================

Use:

event-images

event-videos

Snapshot:

event-images

Video:

event-videos

Store metadata in:

event_media

Do not store large videos directly inside PostgreSQL.

============================================================
SUPABASE SECURITY
============================================================

Never put:

service-role key

inside React/Vite frontend.

Never hardcode:

database password
API secrets
service keys

Use environment variables.

Do not disable RLS merely to make development easier.

============================================================
DATABASE EVENT FLOW
============================================================

YOLO
 ↓
Tracking
 ↓
Zone Check
 ↓
Temporal Logic
 ↓
Sensor Fusion
 ↓
Decision Engine
 ↓
Event
 ↓
Snapshot / Video
 ↓
Supabase Storage
 ↓
event_media
 ↓
Dashboard

============================================================
EVENT TYPES
============================================================

human_intrusion
animal
bird
vehicle
group_activity
abnormal_activity
camera_blocked
low_visibility
sensor_trigger
system_error
test

Severity:

info
low
medium
high
critical

Status:

active
acknowledged
resolved
false_positive

============================================================
FRONTEND
============================================================

Use:

React
Vite
TailwindCSS

The Figma/Stitch design is the visual source of truth.

Do not replace it with a generic admin dashboard.

The frontend must look like:

professional security operations center
industrial monitoring system
AI surveillance platform

============================================================
FRONTEND PAGES
============================================================

Overview
Live Monitor
Events
Event Details
Zones
Sensors
Devices
Camera Health
Analytics
Settings

============================================================
OVERVIEW
============================================================

Show:

System Status
Active Alerts
Events Today
People Detected
Connected Devices
Camera Health

Large live camera.

Show:

bounding boxes
confidence
track ID
restricted polygon

Threat status panel.

Sensor fusion panel.

Recent events.

============================================================
LIVE MONITOR
============================================================

Large live video.

Detection inspector.

Show:

class
confidence
track ID
zone
status

Sensor evidence:

VISION
RADAR
GROUND
TEMPORAL

Decision:

FUSED THREAT

============================================================
ZONE EDITOR
============================================================

Interactive polygon editor.

Controls:

Create
Save
Cancel
Reset
Edit
Delete
Enable
Disable

Show polygon directly over live camera.

============================================================
EVENT INVESTIGATION
============================================================

Show:

snapshot
video
event metadata
timeline
sensor evidence
confidence
camera
zone
track ID

Actions:

ACKNOWLEDGE
RESOLVE
FALSE POSITIVE

============================================================
SENSOR PAGE
============================================================

Show:

Radar
Ground
Environment

For each:

state
last reading
health
connection
simulation/real status

============================================================
CAMERA HEALTH
============================================================

Show:

FPS
brightness
blur
visibility
resolution
last frame
health score

============================================================
ANALYTICS
============================================================

Show:

events/hour
event types
human detections
false positives
sensor confirmations
average confidence
camera uptime

============================================================
SETTINGS
============================================================

Configurable:

YOLO model
YOLO confidence
human critical threshold
temporal frames
temporal window
event cooldown
pre-event duration
post-event duration
fusion weights
camera
ESP32
sensor simulation

============================================================
PERFORMANCE
============================================================

CRITICAL:

The camera must remain responsive.

Never block the camera because of:

YOLO
Supabase
video encoding
file uploads
database operations
ESP32 requests

Use:

background workers
bounded queues
async/background network operations

The UI must remain responsive.

============================================================
STARTUP HEALTH CHECK
============================================================

At startup check:

Camera
YOLO
Supabase
ESP32
Storage
Configuration

Display:

CAMERA ✓
YOLO ✓
SUPABASE ✓
ESP32 ✓/OFFLINE
RADAR SIMULATED/OFFLINE
GROUND SIMULATED/OFFLINE

============================================================
TEST MODE
============================================================

Create:

Test Camera
Test YOLO
Test Zone
Test ESP32
Test Buzzer
Test Radar
Test Ground
Test Event
Test Snapshot
Test Video
Test Supabase

============================================================
PROJECT STRUCTURE
============================================================

Use a clean modular architecture.

Example:

backend/
    app.py
    config.py
    api/
    camera/
    vision/
    tracking/
    sensors/
    decision/
    alerts/
    evidence/
    database/
    hardware/
    logging/

frontend/
    src/
      components/
      pages/
      hooks/
      services/
      types/
      utils/

esp32/
    firmware/

models/
    yolo/

tests/

docs/

============================================================
ENVIRONMENT
============================================================

Create:

.env.example

Include:

SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=

ESP32_IP=
ESP32_PORT=80

CAMERA_INDEX=0

YOLO_MODEL=models/yolo11n.pt
YOLO_CONFIDENCE=0.50
YOLO_HUMAN_HIGH_CONFIDENCE=0.85
YOLO_IMGSZ=640

RADAR_GPIO=27
GROUND_GPIO=26
RAIN_GPIO=34
BUZZER_GPIO=25

RUNTIME_MODE=laptop
SENSOR_SIMULATION=true

PRE_EVENT_SECONDS=5
POST_EVENT_SECONDS=8

EVENT_COOLDOWN_SECONDS=10

TEMPORAL_MIN_FRAMES=3
TEMPORAL_WINDOW_SECONDS=1

Never commit .env.

Create .gitignore.

============================================================
DOCUMENTATION
============================================================

Create:

README.md
ARCHITECTURE.md
HARDWARE_SETUP.md
ESP32_SETUP.md
SOFTWARE_SETUP.md
SUPABASE_SETUP.md
TESTING.md
TROUBLESHOOTING.md
RASPBERRY_PI_MIGRATION.md

============================================================
TESTING
============================================================

Actually run the application.

Do not simply create source files and say DONE.

Test:

1. camera
2. YOLO
3. frontend
4. backend
5. zone selection
6. tracking
7. temporal confirmation
8. event creation
9. snapshot
10. video
11. Supabase insertion
12. Supabase storage
13. ESP32 communication
14. buzzer
15. sensor simulation
16. ESP32 disconnect behavior

Fix errors found.

============================================================
FIRST DEMO
============================================================

The first complete demo must be:

1. Start backend
2. Start frontend
3. Camera opens
4. Dashboard opens
5. Configure restricted polygon
6. Person enters polygon
7. YOLO detects person
8. Track ID assigned
9. Confidence shown
10. Temporal confirmation
11. Critical event created
12. Snapshot captured
13. Video captured
14. Supabase event stored
15. Evidence uploaded
16. ESP32 receives alarm
17. Buzzer activates
18. Dashboard shows CRITICAL ALERT

============================================================
NON-HUMAN TEST
============================================================

Animal/bird/vehicle:

Detect
Classify
Display

Do not activate intrusion buzzer by default.

============================================================
SENSOR FUSION TEST
============================================================

Test:

YOLO = 0.55
Radar = ON
Ground = ON
Temporal = TRUE

Expected:

CONFIRMED EVENT

Test:

YOLO = 0.55
Radar = OFF
Ground = OFF

Expected:

POSSIBLE DETECTION

Test:

YOLO person = 0.92
inside restricted zone

Expected:

IMMEDIATE CRITICAL ALERT

============================================================
NO FAKE FEATURES
============================================================

Never pretend:

radar is connected
ground sensor is connected
PTZ exists
rain detection is perfect
fog detection is perfect
fighting recognition exists

Clearly label:

SIMULATED
EXPERIMENTAL
OFFLINE
FUTURE HARDWARE

============================================================
GITHUB MCP
============================================================

If GitHub MCP fails because Docker is unavailable:

DO NOT stop development.

Continue with local workspace.

Do not waste implementation time fixing GitHub MCP.

============================================================
FINAL ACCEPTANCE CRITERIA
============================================================

The system is successful only when:

✓ camera works
✓ YOLO works
✓ person detection works
✓ tracking works
✓ polygon zone works
✓ temporal confirmation works
✓ event state machine works
✓ duplicate suppression works
✓ snapshot works
✓ video works
✓ Supabase event works
✓ Supabase Storage works
✓ dashboard displays events
✓ ESP32 communication works
✓ buzzer works
✓ ESP32 disconnect does not crash system
✓ sensor simulation works
✓ architecture supports real sensors
✓ documentation exists
✓ no secrets committed

============================================================
VERY IMPORTANT
============================================================

Do not say DONE just because files were generated.

Before declaring completion:

RUN IT.

TEST IT.

FIX IT.

Then provide:

1. Project tree
2. Installation commands
3. Run commands
4. .env.example
5. ESP32 pin table
6. ESP32 firmware
7. Backend API
8. Frontend URL
9. Supabase tables
10. Storage buckets
11. Zone configuration procedure
12. Testing procedure
13. Troubleshooting
14. What works now
15. What is simulated
16. What requires future hardware
17. Known limitations
18. Next recommended development step

============================================================
START NOW
============================================================

FIRST:

1. Inspect the existing workspace.
2. Inspect the existing Supabase project/schema.
3. Inspect connected Figma/Stitch resources.
4. Inspect existing project files.
5. Do not delete existing useful work.
6. Create an implementation plan.
7. Identify missing dependencies.
8. Begin with the laptop prototype.
9. Implement incrementally.
10. Test after every major subsystem.

DO NOT WAIT FOR ME TO REPEAT THE PROJECT REQUIREMENTS.

============================================================
END MASTER PROMPT
============================================================


After every major development phase, update:

PROJECT_STATE.md

It must contain:

PROJECT STATUS

CURRENT PHASE

WHAT IS IMPLEMENTED

WHAT IS TESTED

WHAT FAILED

WHAT WAS FIXED

CURRENT ERRORS

CURRENT CONFIGURATION

SUPABASE STATUS

FRONTEND STATUS

BACKEND STATUS

ESP32 STATUS

YOLO STATUS

SENSOR SIMULATION STATUS

FILES CREATED

FILES MODIFIED

NEXT TASK

KNOWN LIMITATIONS

DO NOT repeat completed work.


                 PROJECT REQUIREMENTS
                         │
                         ▼
             MASTER SPECIFICATION
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
       STITCH / FIGMA             CLAUDE
       UI DESIGN                  REVIEW
             │                       │
             │                       │
             ▼                       ▼
       UI SOURCE OF             ARCHITECTURE
         TRUTH                    REVIEW
             │                       │
             └───────────┬───────────┘
                         ▼
                  ANTIGRAVITY
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       FRONTEND       BACKEND        ESP32
          │              │              │
          │              ▼              │
          │          YOLO/OpenCV        │
          │              │              │
          │              ▼              │
          │       DECISION ENGINE       │
          │              │              │
          │              ▼              │
          │         EVENT ENGINE        │
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                    SUPABASE
                  ┌──────┴──────┐
                  ▼             ▼
                 DB          STORAGE
                  │             │
                  └──────┬──────┘
                         ▼
                    DASHBOARD


PART 7 — DEVELOPMENT PHASES

Don't tell Antigravity to build everything simultaneously.

Tell it to work in these phases.

PHASE 0 — Inspect
Workspace
Supabase
Figma/Stitch
existing code
dependencies
PHASE 1 — UI shell
Dashboard
navigation
live monitor
events
zones
sensors
settings
PHASE 2 — Camera
Laptop camera
OpenCV
smooth frame pipeline
PHASE 3 — YOLO
YOLO
detections
confidence
tracking
PHASE 4 — Restricted zone
polygon
point-in-polygon
person inside zone
PHASE 5 — Decision engine
confidence
temporal confirmation
event state machine
PHASE 6 — Evidence
snapshot
pre-event buffer
post-event recording
video
PHASE 7 — Supabase
events
detections
zones
camera health
event_media
storage
PHASE 8 — ESP32
Wi-Fi
HTTP
heartbeat
alarm
buzzer
PHASE 9 — Sensor simulation
radar simulation
ground simulation
fusion
PHASE 10 — Testing
full system test
failure test
performance test
PHASE 11 — Real sensors

When your sensors arrive:

SIMULATION
     ↓
REAL RADAR
REAL GROUND SENSOR
PHASE 12 — Raspberry Pi

Finally:

Laptop
   ↓
Raspberry Pi 5
   ↓
USB/CSI Camera
   ↓
YOLO