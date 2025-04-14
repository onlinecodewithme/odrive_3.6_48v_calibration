# ODrive ROS 2 Driver

A ROS 2 driver for the ODrive motor controller, designed for differential drive robots.

## Overview

This package provides a ROS 2 driver for the ODrive motor controller. It supports:

- Differential drive control via cmd_vel
- Odometry publishing
- TF transforms
- Multiple control modes (velocity, position, torque)
- Emergency stop functionality

## Requirements

- ROS 2 (Foxy, Galactic, Humble, or later)
- ODrive 3.6 or compatible controller
- Python 3.6+
- Python packages: odrive, numpy

## Installation

### 1. Install ROS 2

Follow the official ROS 2 installation guide for your OS:
https://docs.ros.org/en/galactic/Installation.html

### 2. Install the ODrive Python package

```bash
pip install --upgrade odrive
```

### 3. Clone and build the package

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/yourusername/odrive_ros2.git
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## Configuration

Edit the configuration file in `config/odrive_config.yaml` to match your robot setup:

- `left_motor_axis` and `right_motor_axis`: Axis numbers for left and right motors (typically 0 and 1)
- `wheel_radius`: Radius of your wheels in meters
- `wheel_base`: Distance between wheels in meters
- `ticks_per_rev`: Encoder counts per revolution
- `control_mode`: "velocity", "position", or "torque"
- `gear_ratio`: Set if you're using geared motors

## Usage

### Basic Usage

```bash
ros2 launch odrive_ros2 odrive.launch.py
```

### Run in Simulation Mode

```bash
ros2 launch odrive_ros2 odrive.launch.py simulation_mode:=true
```

### Test with Teleop

Install the teleop package:

```bash
sudo apt install ros-$ROS_DISTRO-teleop-twist-keyboard
```

Run teleop:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

## Firmware Management

This package works with ODrive firmware version 0.5.1 and above. We've included several methods to manage firmware:

1. **Convert and Flash Tool** (recommended):
   ```bash
   ./scripts/convert_and_flash.py
   ```
   - Converts the large ELF firmware file to a binary format first
   - Then flashes the binary to the ODrive
   - Solves the "Last page is not writeable" error
   - Requires arm-none-eabi-gcc tools (will guide you to install)

2. **Custom Firmware Flash** (alternative):
   ```bash
   ./scripts/flash_custom_firmware.py
   ```
   - Attempts direct flashing of the ELF file
   - Tries multiple alternative methods
   - May not work with very large firmware files

2. **Official Firmware Tool**:
   ```bash
   ./scripts/official_firmware_flash.py
   ```
   - Fetches available firmware versions from the official ODrive documentation
   - Allows you to select which version to install
   - Guides you through the DFU mode process

3. Manual DFU Mode (specific version):
   ```bash
   ./scripts/manual_dfu_flash.py
   ```
   - Pre-configured to use v0.5.1 (known to work well)

4. Recovery Tool (for connection issues):
   ```bash
   ./scripts/recover_odrive.py
   ```
   - Helps diagnose and recover from connection problems

5. Using STLink/2 programmer (for advanced users):
   - Requires additional hardware

For detailed instructions and troubleshooting, see:
- [FIRMWARE_UPDATE.md](FIRMWARE_UPDATE.md) - Firmware update procedures
- [CONNECTION_RECOVERY.md](CONNECTION_RECOVERY.md) - Connection recovery steps

## Troubleshooting

### Cannot Connect to ODrive

Make sure you have permissions to access the USB device:

```bash
sudo chmod 666 /dev/ttyUSB*
```

Or add yourself to the dialout group:

```bash
sudo usermod -a -G dialout $USER
```

### Error Messages

- "ODrive not found": Make sure the ODrive is powered and connected via USB
- "Failed to read encoder values": Check encoder connections
- "Cannot set speeds": Verify the ODrive is in the correct control mode

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
