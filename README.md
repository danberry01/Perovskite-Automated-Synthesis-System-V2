# Perovskite-Automated-Synthesis-System

## Short System Guide

This project combines the software, firmware, electronics, and mechanical files for the PASS V2 platform. The live application is in [Code/src](Code/src), while [Marlin-2.1.2.4](Marlin-2.1.2.4), [Electronics](Electronics), and [CAD](CAD) hold the supporting machine definitions.

## How The Software Is Structured

The main hardware startup path is [Code/src/main.py](Code/src/main.py). On a real machine it enables `PiGPIOFactory`, builds the shared runtime objects, and opens the CustomTkinter GUI.

The runtime is split into four main layers:

1. [Code/src/core/dispatcher.py](Code/src/core/dispatcher.py) creates and owns the hardware-facing objects. This includes the control board, toolhead, camera, spectrometer, hotplate, spin coater, pipette hardware, gripper hardware, and the shared ArUco detector.
2. [Code/src/services/move_registry.py](Code/src/services/move_registry.py) is the high-level command library. It maps procedure step names such as `home`, `move_toolhead`, `set_temperature`, `dispense`, and `measure_spectrum` to Python methods that actually perform the work.
3. [Code/src/services/procedure_handler.py](Code/src/services/procedure_handler.py) runs procedures in a background thread. It validates the loaded step list, executes steps one at a time, and handles pause, resume, stop, progress tracking, and emergency kill behavior.
4. [Code/src/gui/app.py](Code/src/gui/app.py) builds the desktop UI and connects it to the shared dispatcher, move registry, and procedure handler.

In practice, the GUI does not directly talk to every device itself. The usual path is:

`GUI action -> ProcedureHandler or direct callback -> MoveRegistry method -> Dispatcher-owned device/driver`

## What The GUI Does

The main tabs are assembled in [Code/src/gui/frames/tab_view_frame.py](Code/src/gui/frames/tab_view_frame.py) and selected from [Code/src/gui/frames/tab_manager_frame.py](Code/src/gui/frames/tab_manager_frame.py).

- `file_manager`: browse and manage saved files.
- `procedure_builder`: create or edit procedures, locations, and obstacle data.
- `procedure_viewer`: queue and run procedures while watching status updates.
- `settings`: device and run-time configuration.
- `aruco_calibration`: camera-based calibration and alignment tools.

On full startup, the splash and UI flows are responsible for most connection actions. `main.py` mainly builds the application objects and then hands control to the GUI.

## How A Typical Run Works

1. Start the GUI.
2. Connect or verify the required hardware from the UI.
3. Load or build procedure data and any saved locations or obstacles.
4. Run a procedure.
5. The procedure handler steps through each command and calls the matching move in the move registry.
6. The move registry uses the dispatcher-owned devices to move the gantry, operate the pipette and gripper, control the hotplate or spin coater, and collect camera or spectrometer data.
7. If something goes wrong, the procedure can be paused, stopped, or killed. Emergency stop notification is shared across the runtime so non-procedure workers can stop too.

## Saved Data And Configuration

Several parts of the system use YAML or other persisted files under [Code/src/persistant](Code/src/persistant).

- `locations.yml` stores named machine positions.
- `obstacles.yml` stores soft-limit and path-planning obstacles.
- procedure files store step lists that the procedure handler can validate and execute.
- calibration data is used by the ArUco alignment path.

## Real Hardware Vs Mock Mode

There are two useful ways to run the GUI:

- Real hardware mode: start [Code/src/main.py](Code/src/main.py). This path expects the real Linux or Raspberry Pi style hardware environment, including the GPIO-backed servo setup and connected device drivers.
- Mock GUI mode: use [launch_mock_gui.bat](launch_mock_gui.bat), [launch_mock_gui.sh](launch_mock_gui.sh), or [Code/src/gui_mock_launcher.py](Code/src/gui_mock_launcher.py). This path builds a mock dispatcher and mock procedure handler from [Code/src/mock_runtime.py](Code/src/mock_runtime.py), so the UI can be exercised without the full machine connected.

Mock mode is the safer option on Windows when you want to inspect the interface or test non-hardware UI flows.

## Repository Layout At A Glance

- [Code](Code): Python application, drivers, GUI, and persisted runtime data.
- [Marlin-2.1.2.4](Marlin-2.1.2.4): printer or gantry firmware sources and configuration.
- [Electronics](Electronics): board design files.
- [CAD](CAD): mechanical assemblies and part models.

If you are new to the project, the fastest way to understand behavior is to start with [Code/src/main.py](Code/src/main.py), then read [Code/src/core/dispatcher.py](Code/src/core/dispatcher.py), [Code/src/services/move_registry.py](Code/src/services/move_registry.py), and [Code/src/services/procedure_handler.py](Code/src/services/procedure_handler.py) in that order.
 
