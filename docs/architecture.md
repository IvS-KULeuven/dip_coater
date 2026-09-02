# Architecture

This page describes the runtime boundaries maintainers should preserve when
changing the application.

## Runtime flow

The command-line entry point selects a machine profile and motor-driver
specification. `initialize_runtime()` is the single production construction
boundary: it normalizes and validates the profile, creates the concrete driver
through the registry, attaches logging, and creates the `MotionController`.
`AppState` connects that runtime to the Textual UI and the Coder API.

```text
CLI and environment
        |
        v
machine profile + driver registry
        |
        v
initialize_runtime()
        |
        v
concrete motor driver <-> MotionController
        |                      |
        +---------- AppState --+
                         |
                Textual UI / Coder API
```

## Component boundaries

| Component | Owns | Must not own |
|---|---|---|
| Machine profile | Geometry, travel range, homing direction, safety-switch configuration | Hardware communication |
| Driver registry | Driver selection, construction, and setup compatibility | User-interface state |
| `initialize_runtime()` | Startup ordering, runtime wiring, session-start event, and rollback after partial startup | Motion policy or widget behavior |
| Motor driver | Chip communication, register units, and resource cleanup | Machine travel policy |
| `MotionController` | Input validation, travel checks, homing reference, timeouts, limit handling, and session events | Textual widgets |
| `AppState` | References shared by the runtime and UI | Motion or register calculations |
| Textual widgets | User interaction and visible state | Direct chip communication |

## Safety invariants

- Driver outputs start disabled and every application exit routes through
  cleanup.
- Motion commands require finite, positive values and remain inside configured
  travel after a homing reference exists.
- Absolute movement is rejected without a valid homing reference.
- Starting or failing a homing attempt invalidates the previous homing
  reference until the complete sequence succeeds.
- Motion timeouts, polling faults, and driver exceptions attempt both stop and
  disable operations before reporting a fault.
- Emergency stop and cleanup attempt every safety action while preserving the
  first failure for diagnosis.
- Hardware resources and log handlers have explicit ownership and are released
  on both partial startup and normal shutdown.

## Extension rules

Add a new driver through the driver registry and the `MotorDriver` interface.
Keep chip-unit conversions inside the driver or `trinamic_wrapper`; keep
millimeter motion, travel, and homing policy in `MotionController`.

Add a new machine by defining a validated machine profile. Do not encode
machine geometry or limit-switch polarity in UI callbacks.

Use dummy drivers for automated application tests. Real-hardware tests must be
marked as hardware tests, use conservative current limits, and keep physical
motion behind a separate explicit opt-in.
