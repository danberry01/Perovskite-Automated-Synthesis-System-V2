# ArUco Marker Calibration System - Implementation Summary

## Overview
A complete new tab has been added to the GUI for ArUco marker position calibration. This system allows precise determination of absolute positions of ArUco markers in the robot's coordinate system.

---

## Architecture

### New Files Created

#### 1. **Core Calibration Frame**
- **Path**: `src/gui/frames/calibration/aruco_calibration_frame.py`
- **Class**: `ArucoCalibrationFrame`
- **Responsibility**: Main UI frame orchestrating the calibration workflow

#### 2. **Package Initialization**
- **Path**: `src/gui/frames/calibration/__init__.py`
- **Purpose**: Makes calibration module importable

### Modified Files

1. **`src/gui/components/constants.py`**
   - Added `"aruco_calibration"` to TABS list

2. **`src/gui/frames/__init__.py`**
   - Added import: `from .calibration import ArucoCalibrationFrame`

3. **`src/gui/frames/tab_view_frame.py`**
   - Added import of ArucoCalibrationFrame
   - Created `aruco_calibration_frame` instance
   - Added to `frames` dictionary mapping

4. **`src/gui/frames/tab_manager_frame.py`**
   - Added calibration icons (currently reusing settings icons)
   - Created calibration tab button
   - Added button to UI at row 5

---

## Calibration Workflow

### Phase 1: Scanning
1. User clicks "Start Calibration Scan"
2. System displays current gantry position (X, Y, Z, A, B)
3. Scans camera feed for ArUco markers for 2 seconds
4. Collects relative position of each detected marker

### Phase 2: Calculation
1. Gets gantry's current absolute position from control board
2. Calculates absolute marker position:
   ```
   absolute_pos = gantry_position + marker_relative_position
   ```
3. Stores in calibration_data dictionary

### Phase 3: Verification (3 Attempts)
For each detected marker:
1. Home the gantry (G28 command)
2. Move to calculated absolute position
3. Scan camera feed for marker at that location
4. Record if marker is detected
5. Repeat 3 times

### Phase 4: Validation
- If results are consistent (detected at least 2/3 times), calibration is stored
- If inconsistent, system retries verification
- Keeps trying until consistent results are achieved

---

## UI Components

### Left Panel
- **Camera Feed Display**: Live video feed (600x400)
- **Status Label**: Real-time operation status updates
- **Gantry Position Display**: Shows current X, Y, Z positions in mm

### Right Panel - Controls
- **Start Calibration Scan**: Green button - initiates calibration process
- **Cancel**: Red button - stops ongoing calibration (disabled when idle)
- **Home Gantry**: Blue button - sends G28 home command
- **Refresh Position**: Gray button - updates displayed gantry position

### Right Panel - Displays
- **Detected Markers Section**: Shows real-time marker detection
  - Marker ID
  - X, Y, Z coordinates

- **Calibrated Positions Section**: List of successfully calibrated markers
  - Marker ID
  - Absolute position (X, Y, Z in mm)
  - Verification count

### Right Panel - Management
- **Save Selected**: Green button - saves selected calibration to disk
- **Delete Selected**: Red button - removes selected calibration
- **Clear All**: Orange button - removes all calibrations

---

## Data Storage

### Calibration Data Format
```json
{
  "marker_id": {
    "relative_positions": [{"x": 0.123, "y": 0.456, "z": 0.789}],
    "absolute_position": {
      "x": 150.5,
      "y": 200.3,
      "z": 50.2
    },
    "verification_count": 3,
    "gantry_reference": {
      "X": 150.377,
      "Y": 199.844,
      "Z": 49.411,
      "A": 0,
      "B": 0
    }
  }
}
```

### Storage Location
- **File**: `calibration_data/aruco_calibrations.json`
- **Automatic**: Data is auto-loaded on startup
- **Auto-save**: Data is saved after each successful calibration

---

## API Methods

### Public Methods

#### `_start_calibration_scan()`
Initiates the calibration process in a background thread.

#### `_home_gantry()`
Sends G28 home command to controlboard and waits for completion.

#### `_refresh_position()`
Updates the displayed gantry position from control board.

#### `_cancel_calibration()`
Cancels ongoing calibration and resets UI state.

#### `_save_selected_position()`
Saves the selected calibration to disk.

#### `_delete_selected_position()`
Removes a selected calibration entry.

#### `_clear_all_calibrations()`
Removes all calibrations from the system.

#### `pause_updates()`
Pauses operations when tab is not active (reduces CPU usage).

#### `resume_updates()`
Resumes operations when tab becomes active.

---

## Integration Points

### Dependencies Used
- **ArucoDetector** (`src/drivers/aruco_detector_driver.py`)
  - `detect_markers(frame)` - Detects markers in frame
  - `log_detection_results(result)` - Logs detection info

- **ControlBoard** (`src/drivers/controlboard_driver.py`)
  - `positions` - Dict with current X, Y, Z, A, B positions
  - `move_axis(axis, distance_mm, feedrate)` - Moves specific axis
  - `send_message(command)` - Sends G-code commands
  - `finish_moves()` - Waits for move to complete

### Data Access
- Gets position from: `dispatcher.control_board`
- Passes through: `Tab Manager` → `App` → `TabViewFrame`

---

## Threading Model

### Background Worker Thread
- Calibration process runs in `_calibration_worker()` thread
- Prevents UI freezing during scanning and verification
- Updates UI via method calls from worker thread

### Thread Safety
- Uses status label updates for progress communication
- All hardware commands go through ControlBoard (thread-safe)
- Calibration data stored in dictionary (no concurrent access)

---

## Error Handling

### Graceful Failures
- If no markers detected → Status message, cancel operation
- If verification fails → Retry with consistent results check
- If file I/O fails → Logged, allows continued use with in-memory data

### Logger Integration
- All major events logged to "Main Logger"
- Debug level: Step-by-step operation details
- Info level: Successful calibrations
- Warning level: No markers detected, inconsistent results
- Error level: I/O failures, connection issues

---

## User Workflow Example

1. **Navigate to ArUco Calibration Tab** - Click calibration icon in sidebar
2. **Position Marker** - Place ArUco marker in robot workspace
3. **Position Gantry** - Manually move gantry to known reference position
4. **Click "Start Calibration Scan"** 
   - System scans for marker
   - Calculates absolute position
   - Verifies position accuracy 3 times
   - Displays result in list
5. **Save Calibration** - Position is already saved automatically
6. **Repeat for Other Markers** - Scan different markers as needed

---

## Future Enhancements

### Possible Improvements
1. **Calibration Profiles**: Save multiple calibration sets per mission
2. **Marker Position History**: Track position changes over time
3. **Export/Import**: Save/load calibrations in different formats
4. **Batch Calibration**: Calibrate multiple markers in one workflow
5. **Position Testing**: Move to calibrated position on demand
6. **Accuracy Metrics**: Display margin of error and confidence score
7. **Camera Calibration UI**: Integrate with camera calibration workflow
8. **Live Marker Tracking**: Stream marked positions in real-time

---

## Known Limitations

1. **Single Camera Capture Instance**: Creates new VideoCapture for each scan
   - May conflict with other camera operations
   - Future: Share camera resource via dispatcher

2. **Icon Placeholders**: Currently reusing settings icons for calibration
   - Future: Create dedicated calibration icons

3. **Fixed Marker Size**: Assumes 50mm (0.05m) markers
   - Could be made configurable

4. **No GUI Position Entry**: Can't manually set positions for testing
   - Future: Add manual position input field

---

## Testing Checklist

- [ ] Tab appears in sidebar with correct icon
- [ ] Tab button switches to calibration frame
- [ ] Camera feed displays live video
- [ ] Gantry position updates correctly
- [ ] "Start Calibration Scan" button initiates workflow
- [ ] Markers are detected and displayed
- [ ] Absolute positions calculated correctly
- [ ] Verification process completes 3 times
- [ ] Calibrations saved to JSON file
- [ ] Calibrations load on startup
- [ ] Delete removes calibrations from list
- [ ] Clear All empties list and file
- [ ] Tab pause/resume prevents CPU usage when not visible
- [ ] Cancel button stops ongoing calibration
- [ ] Status messages display workflow progress
- [ ] No errors in Pylance/linter

---

## Tab Integration Summary

| Component | Location | Status |
|-----------|----------|--------|
| Frame Class | `src/gui/frames/calibration/` | ✅ Created |
| Constants Updated | `components/constants.py` | ✅ Updated |
| Frames Init Updated | `frames/__init__.py` | ✅ Updated |
| Tab View Updated | `tab_view_frame.py` | ✅ Updated |
| Tab Manager Button | `tab_manager_frame.py` | ✅ Updated |
| Documentation | This file | ✅ Complete |

---

## Running the Application

After these changes, the calibration tab will be available in the main GUI:

```bash
cd Code
python src/main.py
```

The new ArUco Calibration tab will appear in the side navigation panel.

