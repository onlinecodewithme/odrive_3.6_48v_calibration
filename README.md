# ODrive ROS 2 Integration

A complete toolkit for integrating ODrive motor controllers with ROS 2, specifically designed for differential drive robots with 48V 1000W motors.

## Overview

This package provides:

1. **Firmware Management** - Tools to update ODrive firmware with custom or official versions
2. **Motor Calibration** - Multiple calibration approaches for challenging high-power motors
3. **ROS 2 Driver** - A full-featured differential drive interface for ROS 2
4. **Configuration Tools** - Utilities to configure and test your ODrive with ROS 2

The tools in this package are designed to handle the specific challenges of 48V 1000W motors, including difficulties with calibration and firmware updates.

## Getting Started

### 1. Update Firmware (if needed)

If you need to update the firmware on your ODrive controller:

```bash
# For the provided custom firmware (ELF file):
./src/odrive_ros2/scripts/flash_custom_firmware.py

# If firmware file is too large for direct flashing:
./src/odrive_ros2/scripts/convert_and_flash.py
```

See [FIRMWARE_UPDATE.md](src/odrive_ros2/FIRMWARE_UPDATE.md) for detailed firmware update instructions.

### 2. Calibrate Motors

Motor calibration is the most critical step for proper operation. Use the calibration sequence to try multiple approaches:

```bash
./src/odrive_ros2/scripts/calibration_sequence.py
```

This script tries a sequence of calibration approaches with increasingly aggressive settings, logging results to help diagnose problems.

Individual calibration tools are also available:

```bash
# For difficult-to-calibrate motors:
./src/odrive_ros2/scripts/minimal_calibration.py

# For detailed troubleshooting:
./src/odrive_ros2/scripts/troubleshoot_calibration.py --mode=diagnose

# For standard quick calibration:
./src/odrive_ros2/scripts/quick_calibrate.py
```

See [MOTOR_CALIBRATION.md](src/odrive_ros2/MOTOR_CALIBRATION.md) for detailed motor calibration instructions.

### 3. Configure for ROS 2

After calibration, set up the ODrive for ROS 2:

```bash
./src/odrive_ros2/scripts/setup_ros2_odrive.py --wheel-radius 0.085 --wheel-base 0.3
```

Adjust the wheel radius and wheel base parameters to match your robot's dimensions.

### 4. Launch with ROS 2

Once everything is configured, launch the ROS 2 driver:

```bash
ros2 launch odrive_ros2 odrive.launch.py
```

Test basic movement:

```bash
# Move forward at 0.2 m/s:
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "linear: {x: 0.2}" -1

# Turn at 0.5 rad/s while moving:
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "linear: {x: 0.2}, angular: {z: 0.5}" -1

# Stop:
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "linear: {x: 0.0}" -1
```

## Key Components

### Firmware Tools

- `flash_custom_firmware.py` - For direct flashing of custom firmware
- `convert_and_flash.py` - For converting large ELF files to binary before flashing
- `official_firmware_flash.py` - To install official firmware versions

### Calibration Tools

- `calibration_sequence.py` - Step-by-step system to try multiple calibration methods
- `minimal_calibration.py` - Ultra-conservative settings for difficult motors
- `troubleshoot_calibration.py` - Detailed diagnostics and specialized calibration modes
- `quick_calibrate.py` - Standard calibration for normal setups

### Configuration Tools

- `setup_ros2_odrive.py` - Configures ODrive for ROS 2 and tests movement
- `check_odrive.py` - Simple tool to verify ODrive connectivity

### ROS 2 Components

- `odrive_node.py` - The main ROS 2 driver node
- `config/odrive_config.yaml` - Configuration parameters for the ROS 2 driver
- `launch/odrive.launch.py` - Launch file for the ROS 2 driver

## Calibration Workflow

For challenging 48V 1000W motors, we recommend this calibration workflow:

1. **Start with Diagnostics**:
   ```bash
   ./src/odrive_ros2/scripts/troubleshoot_calibration.py --mode=diagnose
   ```

2. **Try Minimal Calibration**:
   ```bash
   ./src/odrive_ros2/scripts/minimal_calibration.py
   ```

3. **Progress to Forced Calibration** (if needed):
   ```bash
   ./src/odrive_ros2/scripts/troubleshoot_calibration.py --mode=force --axis=0 --current=1.5
   ```

4. **Try Standard Calibration** (if previous steps fail):
   ```bash
   ./src/odrive_ros2/scripts/quick_calibrate.py
   ```

5. **Or run the Complete Sequence**:
   ```bash
   ./src/odrive_ros2/scripts/calibration_sequence.py
   ```

## Common Issues and Solutions

### Motor Calibration Failures

- Check motor wiring (phase wires and Hall sensor connections)
- Try lower calibration currents (1.5A to 3.0A)
- Check power supply (needs to be adequately rated for 48V motors)
- Try reconfiguring with minimal conservative settings

### Encoder Calibration Failures

- Ensure Hall sensors are properly connected
- Verify motor calibration is successful first
- Try manual encoder placement in safe position

### ROS 2 Communication Issues

- Check USB connections
- Ensure motors are calibrated before running the ROS 2 driver
- Verify ODrive is detected with `check_odrive.py`

## Advanced Configuration

Fine-tune your setup by editing:

- `config/odrive_config.yaml` - Main ROS 2 driver configuration
- ODrive controller settings using the scripts in the `scripts` directory

## Documentation

- [FIRMWARE_UPDATE.md](src/odrive_ros2/FIRMWARE_UPDATE.md) - Detailed firmware update instructions
- [MOTOR_CALIBRATION.md](src/odrive_ros2/MOTOR_CALIBRATION.md) - Comprehensive motor calibration guide
- [CONNECTION_RECOVERY.md](src/odrive_ros2/CONNECTION_RECOVERY.md) - Troubleshooting connection issues

## Requirements

- ODrive 3.6 controller
- ROS 2 (Foxy, Galactic, Humble, or later)
- Python 3.6+
- ODrive Python package (`pip install odrive`)
- 48V power supply (adequate for 1000W motors)
