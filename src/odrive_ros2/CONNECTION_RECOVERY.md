# ODrive Connection Recovery Guide

The scripts confirm that the ODrive is not currently detected by the system after the firmware update. This is not uncommon after firmware updates, especially on embedded systems. Here are step-by-step instructions to recover your connection:

## Immediate Steps

1. **Complete Power Cycle**
   ```
   1. Disconnect the USB cable from your computer
   2. Disconnect 48V power from the ODrive
   3. Wait at least 30 seconds
   4. Reconnect 48V power to the ODrive
   5. Reconnect the USB cable to your computer
   ```

2. **Try a Different USB Port**
   - Sometimes USB ports can have issues. Try connecting to a different port on your computer.
   - If available, try a direct connection rather than through a USB hub.

3. **Check USB Cable**
   - Try a different USB cable if available.
   - Some USB cables are power-only and don't support data transfer.

## Recovery Methods

If the device still isn't detected after the steps above:

### Method 1: Force DFU Mode and Reflash Firmware

1. **Force DFU Mode Manually**
   - Locate the "Boot0" or "DFU" button on your ODrive
   - Power off the ODrive completely
   - Hold the Boot0/DFU button
   - While holding the button, connect USB cable
   - Keep holding the button for 2-3 seconds, then release

2. **Run Manual DFU Flash Script**
   ```bash
   ./scripts/manual_dfu_flash.py
   ```

### Method 2: Hardware Reset (if available)

Some ODrive boards have a reset button:
1. With the ODrive powered, press the reset button
2. This may restore the board to a responsive state

### Method 3: STLink/2 Method (Advanced)

If the above methods fail, you'll need an STLink/2 programmer to reflash the firmware:
1. Follow the instructions in the ODrive developer guide
2. This bypasses the bootloader and flashes directly to the microcontroller

## Check for Success

After each recovery attempt, run:
```bash
./scripts/recover_odrive.py
```

This script will check if the ODrive is now detected by the system.

## Using ROS 2 in Simulation Mode

If you can't recover the device connection immediately, you can still work with the ROS 2 driver in simulation mode:

1. Edit the config file: `config/odrive_config.yaml`
2. Set `simulation_mode: true`
3. Launch the node as usual: `ros2 launch odrive_ros2 odrive.launch.py`

This will allow you to test and develop your robot software while working on recovering the hardware connection.
