# VMC Position Proxy

A VMC Protocol proxy that integrates Root movement and rotation into the Hips bone, enabling avatar locomotion in applications that do not support Root transform properly.

## Overview

When using tracking software via the VMC Protocol (VirtualMotionCapture), some target applications may ignore the `Root` position and rotation data, causing the avatar to walk in place without moving forward. 

This proxy tool intercepts the VMC Protocol data, merges the `Root` data into the `Hips` bone data, and forwards it to the target application. This allows your avatar to move and rotate correctly, even in applications that cannot handle Root information.

* **Fixes position, rotation, and head height synchronization.**
* **Filters unnecessary data** (only prints warning/error logs when forwarding fails).
* **Compact, lightweight Windows native GUI** built with Python and Tkinter.

## Requirements

To run from source or build the application, you need:
* Python 3.x
* python-osc

## How to Build (.exe)

You can compile the script into a standalone Windows executable (`.exe`) using PyInstaller so it can run on PCs without Python installed.

1. Open your terminal or Command Prompt in the project folder.
2. Install the required dependencies:
   ```bash
   pip install python-osc pyinstaller
   ```
3. Run the following command to build the executable:
   ```bash
   pyinstaller --onefile --noconsole --name VMC_Position_Proxy main.py
   ```
4. Once completed, your standalone application `VMC_Position_Proxy.exe` will be generated in the `dist/` directory.

## Usage

1. Launch your tracking software (e.g., VirtualMotionCapture) and set its VMC Protocol **output port to `39539`**.
2. Run `VMC_Position_Proxy.exe`.
3. Enter the **Target IP Address** (e.g., `192.168.0.xx`) and the **Target Port Number** (e.g., `39539`) of your destination application (e.g., Unity or target avatar app).
4. Click the **START** button to begin proxy forwarding.
5. If any packet forwarding errors occur, you can click **▶ Show Error Log** to inspect the error details.

## License

This project is open-source. Feel free to use and modify.
