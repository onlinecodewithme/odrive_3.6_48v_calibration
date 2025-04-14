# ODrive Motor Calibration Guide

This document explains how to calibrate your 48V 1000W motors with the ODrive controller for use with the ROS 2 driver.

## Before You Begin

Ensure that:
1. Your ODrive firmware is updated (v0.5.1 or higher)
2. The ODrive is powered with 48V
3. Motors are securely mounted
4. Motors can rotate freely during calibration
5. Hall sensor cables are properly connected

## Calibration Tools

We provide several calibration scripts for different scenarios:

### 1. Minimal Calibration (For Difficult Motors)

If you're having problems calibrating your motors, start with this script. It uses extremely conservative settings and is designed for motors that are challenging to calibrate.

```bash
./scripts/minimal_calibration.py
```

This script:
- Uses very low currents (2A) and voltages (2V) for calibration
- Focuses only on the basic motor calibration
- Takes a step-by-step approach with detailed feedback

### 2. Troubleshooting Calibration

For more detailed diagnostics and greater control, use the troubleshooting script:

```bash
./scripts/troubleshoot_calibration.py --mode=diagnose
```

This script provides multiple modes:
- `diagnose`: Show detailed motor and encoder information
- `motor`: Calibrate only the motor with custom parameters
- `encoder`: Calibrate only the encoder (if motor is already calibrated)
- `force`: Use ultra-conservative settings for difficult motors
- `test`: Test motor rotation
- `full`: Complete calibration process

Example with specific parameters:
```bash
./scripts/troubleshoot_calibration.py --mode=motor --axis=0 --current=3.0 --limit=15.0
```

### 3. Quick Calibration

For simple cases when you already know your motors work well:

```bash
./scripts/quick_calibrate.py
```

### 4. Advanced Calibration

For full control over the calibration parameters:

```bash
./scripts/calibrate_motors.py --axis=0 --current-limit=35.0 --pole-pairs=7 --speed=3.0
```

## What the Calibration Process Does

The calibration process performs several steps:

1. **Motor Calibration**
   - Identifies phase resistance and inductance
   - Creates a mapping between current and magnetic flux
   - Produces a brief "chirp" sound from the motor

2. **Hall Sensor Calibration**
   - Slowly rotates the motor to map hall sensor positions
   - Determines correct commutation sequence
   - Creates an offset table for accurate position tracking

3. **Rotation Test**
   - Tests forward and backward motion
   - Verifies that the motor can be controlled correctly

## Troubleshooting

### Motor Vibrates But Doesn't Rotate

This usually indicates an issue with the Hall sensors:
- Check hall sensor connections
- Verify that the sensor cables are plugged in correctly (A, B, C order matters)
- Try reducing calibration current with: `--calibration-current 5.0`

### Motor Makes Grinding Noise

This could mean:
- Motor phase connections are incorrect (try swapping any two phase wires)
- Current limits are too high (try reducing with: `--current-limit 20.0`)
- Motor is physically obstructed

### Calibration Fails with Error

Common errors and solutions:
- `ERROR_PHASE_RESISTANCE_OUT_OF_RANGE`: Check wiring and connections
- `ERROR_PHASE_INDUCTANCE_OUT_OF_RANGE`: Try increasing calibration current
- `ERROR_ENCODER_NOT_READY`: Check hall sensor connections

## After Calibration

Once calibration is successful:
1. The configuration is automatically saved to the ODrive
2. You can now use the ROS 2 driver:
   ```bash
   ros2 launch odrive_ros2 odrive.launch.py
   ```

## Advanced Motor Settings

For 48V 1000W motors, these settings typically work well:
- Current limit: 30-40A
- Velocity limit: 25 rad/s
- Calibration current: 10A
- Pole pairs: 7 (common for many BLDC motors)

You can adjust these in the configuration if needed for your specific motors.
